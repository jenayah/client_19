# -*- coding: utf-8 -*-
# Odoo GTK 19 — Many2one Widget
# Search dialog + Open form + Autocomplete

from gi.repository import Gtk, Gio, GObject, Pango, GLib
from .base import WidgetBase
from core.session import session


class _SearchRecord(GObject.Object):
    """Wrapper for search results."""
    def __init__(self, rec_id, name):
        super().__init__()
        self.rec_id = rec_id
        self.name = name


class Many2oneWidget(WidgetBase):
    """many2one field → Entry + Search dialog + Open form

    Features:
      - Text entry with live autocomplete via name_search
      - 🔍 Search button opens search/select dialog
      - 📂 Open button opens the linked record's form view
    """

    def _build_widget(self):
        self.widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.widget.set_hexpand(True)

        # Text entry
        self.entry = Gtk.Entry()
        self.entry.set_hexpand(True)
        self.entry.set_placeholder_text(self.field_string)
        self.entry.connect('changed', self._on_entry_changed)
        self.entry.connect('activate', self._on_entry_activate)
        self.widget.append(self.entry)

        # Open button (📂)
        self.btn_open = Gtk.Button(icon_name='document-open-symbolic')
        self.btn_open.add_css_class('flat')
        self.btn_open.set_tooltip_text('Ouvrir le formulaire')
        self.btn_open.set_sensitive(False)
        self.btn_open.connect('clicked', self._on_open_record)
        self.widget.append(self.btn_open)

        # Search button (🔍)
        self.btn_search = Gtk.Button(icon_name='system-search-symbolic')
        self.btn_search.add_css_class('flat')
        self.btn_search.set_tooltip_text('Rechercher')
        self.btn_search.connect('clicked', self._on_search_clicked)
        self.widget.append(self.btn_search)

        self._current_id = False
        self._current_name = ''
        self._relation = self.field_info.get('relation', '')
        self._domain = self.field_info.get('domain', [])
        self._suppress_change = False  # Prevent change loop
        self._search_timeout_id = None

    # ══════════════════════════════════════════════════════════════
    #   VALUE GET / SET
    # ══════════════════════════════════════════════════════════════
    def set_value(self, value):
        self._suppress_change = True
        if not value or value is False:
            self._current_id = False
            self._current_name = ''
            self.entry.set_text('')
            self.btn_open.set_sensitive(False)
        elif isinstance(value, (list, tuple)) and len(value) >= 2:
            self._current_id = value[0]
            self._current_name = str(value[1])
            self.entry.set_text(self._current_name)
            self.btn_open.set_sensitive(True)
        elif isinstance(value, int):
            self._current_id = value
            try:
                if self._relation:
                    result = session.client.call_kw(
                        self._relation, 'read', [[value]],
                        {'fields': ['display_name']})
                    if result:
                        self._current_name = str(result[0].get('display_name', value))
                        self.entry.set_text(self._current_name)
                        self.btn_open.set_sensitive(True)
            except Exception:
                self.entry.set_text(str(value))
        else:
            self.entry.set_text(str(value))
        self._suppress_change = False

    def get_value(self):
        return self._current_id or False

    def set_readonly(self, readonly):
        self._readonly = readonly
        self.entry.set_editable(not readonly)
        self.btn_search.set_sensitive(not readonly)

    # ══════════════════════════════════════════════════════════════
    #   AUTOCOMPLETE (on typing)
    # ══════════════════════════════════════════════════════════════
    def _on_entry_changed(self, entry):
        """Live autocomplete: debounce then search."""
        if self._suppress_change:
            return
        if self._readonly:
            return

        text = entry.get_text().strip()

        # If text is cleared, reset selection
        if not text:
            self._current_id = False
            self._current_name = ''
            self.btn_open.set_sensitive(False)
            return

        # Debounce: wait 400ms before searching
        if self._search_timeout_id:
            GLib.source_remove(self._search_timeout_id)
        self._search_timeout_id = GLib.timeout_add(400, self._do_autocomplete, text)

    def _do_autocomplete(self, text):
        """Run name_search and show popup."""
        self._search_timeout_id = None
        if not self._relation or not text:
            return False

        try:
            domain = self._domain if isinstance(self._domain, list) else []
            results = session.client.call_kw(
                self._relation, 'name_search', [text, domain],
                {'limit': 10, 'context': session.client.context or {}})

            if results and len(results) == 1:
                # Exact match: select immediately
                self._select_value(results[0][0], results[0][1])
            elif results:
                # Multiple results: show dropdown popover
                self._show_autocomplete_popup(results)
        except Exception as e:
            print(f"Autocomplete error for {self._relation}: {e}")
        return False  # Don't repeat

    def _show_autocomplete_popup(self, results):
        """Show a popover with autocomplete results."""
        popover = Gtk.Popover()
        popover.set_parent(self.entry)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_size_request(300, -1)

        scroll = Gtk.ScrolledWindow()
        scroll.set_max_content_height(250)
        scroll.set_propagate_natural_height(True)

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        listbox.add_css_class('boxed-list')

        for rec_id, name in results:
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label=str(name), xalign=0)
            label.set_margin_start(8)
            label.set_margin_end(8)
            label.set_margin_top(6)
            label.set_margin_bottom(6)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            row.set_child(label)
            row._rec_id = rec_id
            row._rec_name = str(name)
            listbox.append(row)

        def on_row_activated(lb, row):
            self._select_value(row._rec_id, row._rec_name)
            popover.popdown()

        listbox.connect('row-activated', on_row_activated)
        scroll.set_child(listbox)
        box.append(scroll)
        popover.set_child(box)
        popover.popup()

    def _on_entry_activate(self, entry):
        """On Enter key: validate entry text via name_search."""
        if self._readonly:
            return
        text = entry.get_text().strip()
        if not text:
            self._current_id = False
            self._current_name = ''
            self.btn_open.set_sensitive(False)
            return
        if text == self._current_name:
            return  # Already selected

        # Try to find exact match
        try:
            domain = self._domain if isinstance(self._domain, list) else []
            results = session.client.call_kw(
                self._relation, 'name_search', [text, domain],
                {'limit': 5})
            if results:
                if len(results) == 1:
                    self._select_value(results[0][0], results[0][1])
                else:
                    # Open full search dialog with these results
                    self._open_search_dialog(text)
        except Exception:
            pass

    def _select_value(self, rec_id, name):
        """Set the selected value."""
        self._current_id = rec_id
        self._current_name = str(name)
        self._suppress_change = True
        self.entry.set_text(self._current_name)
        self._suppress_change = False
        self.btn_open.set_sensitive(True)

    # ══════════════════════════════════════════════════════════════
    #   SEARCH DIALOG (🔍 button)
    # ══════════════════════════════════════════════════════════════
    def _on_search_clicked(self, btn):
        """Open the full search dialog."""
        self._open_search_dialog('')

    def _open_search_dialog(self, initial_text=''):
        """Open a dialog to search and select a record."""
        if not self._relation:
            return

        window = self.widget.get_root()
        dialog = Gtk.Window(title=f'Rechercher : {self.field_string}')
        dialog.set_transient_for(window)
        dialog.set_modal(True)
        dialog.set_default_size(500, 450)
        dialog.set_destroy_with_parent(True)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        dialog.set_child(main_box)

        # ── Search bar ──
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        search_entry = Gtk.SearchEntry()
        search_entry.set_hexpand(True)
        search_entry.set_placeholder_text('Tapez pour rechercher...')
        if initial_text:
            search_entry.set_text(initial_text)
        search_box.append(search_entry)
        main_box.append(search_box)

        # ── Results list ──
        store = Gio.ListStore.new(_SearchRecord)
        selection = Gtk.SingleSelection.new(store)

        factory = Gtk.SignalListItemFactory()
        def on_setup(f, item):
            label = Gtk.Label(xalign=0)
            label.set_margin_start(8)
            label.set_margin_end(8)
            label.set_margin_top(6)
            label.set_margin_bottom(6)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            item.set_child(label)

        def on_bind(f, item):
            rec = item.get_item()
            item.get_child().set_text(rec.name)

        factory.connect('setup', on_setup)
        factory.connect('bind', on_bind)

        list_view = Gtk.ListView.new(selection, factory)
        list_view.add_css_class('boxed-list')

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_child(list_view)
        main_box.append(scroll)

        # ── Status label ──
        status_label = Gtk.Label(label='', xalign=0)
        status_label.add_css_class('dim-label')
        main_box.append(status_label)

        # ── Buttons ──
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.END)

        btn_new = Gtk.Button(label='Nouveau')
        btn_new.add_css_class('suggested-action')
        btn_box.append(btn_new)

        btn_select = Gtk.Button(label='Sélectionner')
        btn_select.add_css_class('suggested-action')
        btn_box.append(btn_select)

        btn_cancel = Gtk.Button(label='Annuler')
        btn_box.append(btn_cancel)

        main_box.append(btn_box)

        # ── Search logic ──
        def do_search(text=''):
            store.remove_all()
            try:
                domain = self._domain if isinstance(self._domain, list) else []
                results = session.client.call_kw(
                    self._relation, 'name_search', [text, domain],
                    {'limit': 80, 'context': session.client.context or {}})
                for rec_id, name in results:
                    store.append(_SearchRecord(rec_id, str(name)))
                status_label.set_text(f'{len(results)} résultat(s)')
            except Exception as e:
                status_label.set_text(f'Erreur: {e}')

        def on_search_changed(entry):
            text = entry.get_text().strip()
            do_search(text)

        search_entry.connect('search-changed', on_search_changed)

        def on_select(btn):
            sel_item = selection.get_selected_item()
            if sel_item:
                self._select_value(sel_item.rec_id, sel_item.name)
                dialog.close()

        def on_activate(lv, pos):
            item = store.get_item(pos)
            if item:
                self._select_value(item.rec_id, item.name)
                dialog.close()

        btn_select.connect('clicked', on_select)
        list_view.connect('activate', on_activate)
        btn_cancel.connect('clicked', lambda b: dialog.close())

        def on_new(btn):
            # Create a new record and select it
            try:
                new_id = session.client.call_kw(
                    self._relation, 'create', [{'name': search_entry.get_text().strip() or 'Nouveau'}],
                    {'context': session.client.context or {}})
                if isinstance(new_id, list):
                    new_id = new_id[0]
                # Fetch name
                recs = session.client.call_kw(
                    self._relation, 'read', [[new_id]],
                    {'fields': ['display_name']})
                if recs:
                    self._select_value(new_id, recs[0].get('display_name', f'#{new_id}'))
                else:
                    self._select_value(new_id, f'#{new_id}')
                dialog.close()
            except Exception as e:
                status_label.set_text(f'Erreur création: {e}')

        btn_new.connect('clicked', on_new)

        # Initial search
        do_search(initial_text)
        dialog.present()

    # ══════════════════════════════════════════════════════════════
    #   OPEN FORM (📂 button)
    # ══════════════════════════════════════════════════════════════
    def _on_open_record(self, btn):
        """Open the selected record in a form view dialog."""
        if not self._current_id or not self._relation:
            return

        window = self.widget.get_root()
        dialog = Gtk.Window(title=f'{self._current_name}')
        dialog.set_transient_for(window)
        dialog.set_modal(True)
        dialog.set_default_size(700, 550)
        dialog.set_destroy_with_parent(True)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        dialog.set_child(main_box)

        # Header bar with title
        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        dialog.set_titlebar(header)

        # Loading label
        loading = Gtk.Label(label='Chargement...')
        loading.set_margin_top(40)
        main_box.append(loading)

        dialog.present()

        # Load the form view in background
        GLib.idle_add(self._load_form_dialog, dialog, main_box, loading)

    def _load_form_dialog(self, dialog, main_box, loading):
        """Load form view into the dialog."""
        try:
            # Get form view arch
            res = session.client.get_view(self._relation, view_type='form')
            arch = res.get('arch', '<form/>')
            view_fields = res.get('fields', {})

            # Get full field info
            try:
                all_fields = session.client.call_kw(
                    self._relation, 'fields_get', [],
                    {'attributes': ['type', 'string', 'relation', 'selection', 'readonly']})
                for fname, finfo in all_fields.items():
                    if fname in view_fields:
                        merged = dict(finfo)
                        merged.update(view_fields[fname])
                        view_fields[fname] = merged
                    else:
                        view_fields[fname] = finfo
            except Exception:
                pass

            # Read record data
            fields_to_read = list(view_fields.keys())
            if 'display_name' not in fields_to_read:
                fields_to_read.append('display_name')

            record_data = {}
            try:
                recs = session.client.call_kw(
                    self._relation, 'read', [[self._current_id]],
                    {'fields': fields_to_read,
                     'context': session.client.context or {}})
                if recs:
                    record_data = recs[0]
            except Exception:
                # Retry without complex fields
                basic = [f for f in fields_to_read
                         if view_fields.get(f, {}).get('type', 'char')
                         not in ('one2many', 'properties')]
                try:
                    recs = session.client.call_kw(
                        self._relation, 'read', [[self._current_id]],
                        {'fields': basic})
                    if recs:
                        record_data = recs[0]
                except Exception:
                    pass

            # Parse and render the form
            from ui.views.parser import FormParser
            parser = FormParser(view_fields, record_data)
            form_widget = parser.parse(arch)

            # Remove loading label and add form
            main_box.remove(loading)

            if form_widget:
                # All fields readonly in open dialog
                for wid in parser.field_widgets.values():
                    wid.set_readonly(True)

                scroll = Gtk.ScrolledWindow()
                scroll.set_vexpand(True)
                scroll.set_child(form_widget)
                main_box.append(scroll)

            # Update dialog title
            name = record_data.get('display_name', record_data.get('name', ''))
            if name:
                dialog.set_title(str(name))

        except Exception as e:
            main_box.remove(loading)
            error_label = Gtk.Label(label=f'Erreur: {e}')
            error_label.set_margin_top(20)
            error_label.set_wrap(True)
            main_box.append(error_label)
            print(f"Error loading form for {self._relation}/{self._current_id}: {e}")

        return False  # Don't repeat idle
