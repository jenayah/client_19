# -*- coding: utf-8 -*-
# Odoo GTK 19 — List View (Checkbox + Totals + Actions/Print)

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GObject, Pango
from core import Model, session
from ui.widgets import create_field_widget
from ui.widgets.base import WidgetBase
import xml.etree.ElementTree as ET


class _RowData(GObject.Object):
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.selected = False


class ListView(Gtk.Box):
    __gsignals__ = {
        'record-activated': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'create-clicked': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'edit-clicked': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    def __init__(self, model_name, view_id=None, domain=None, context=None, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        self.model_name = model_name
        self.model = Model(model_name)
        self.view_id = view_id
        self.domain = domain or []
        if isinstance(context, str):
            try:
                import ast
                self.context = ast.literal_eval(context)
            except Exception:
                self.context = {}
        else:
            self.context = context or {}
        self.view_arch = None
        self.view_fields = {}
        self.columns_info = []
        self.all_record_ids = []
        self.total_count = 0  # Total records on server

        # Rights
        self.can_create = False
        self.can_write = False

        # Checkbox tracking
        self._row_checkboxes = []
        self._header_check = None
        self._checked_ids = set()
        self._select_all_server = False  # Whether "select all on server" is active

        # Actions/reports cache
        self._server_actions = None
        self._report_actions = None

        self._check_access_rights()
        self._load_view_arch()
        self._setup_list()
        self.load_data()

    def _check_access_rights(self):
        """Check if user has create/write access to this model."""
        try:
            # check_access_rights returns True if OK, False if not
            self.can_create = session.client.call_kw(self.model_name, 'check_access_rights', ['create'], {'raise_exception': False})
            self.can_write = session.client.call_kw(self.model_name, 'check_access_rights', ['write'], {'raise_exception': False})
            print(f"DEBUG: Access rights for {self.model_name} -> create:{self.can_create}, write:{self.can_write}")
        except Exception as e:
            print(f"Error checking access rights: {e}")
            self.can_create = False
            self.can_write = False

    # ══════════════════════════════════════════════════════════════
    #   VIEW ARCH
    # ══════════════════════════════════════════════════════════════
    def _load_view_arch(self):
        try:
            res = session.client.get_view(self.model_name, view_id=self.view_id, view_type='list')
            self.view_arch = res.get('arch', '<list/>')
            self.view_fields = res.get('fields', {})
            
            # Odoo may also send a 'create' and 'edit' attribute in the arch node
            root = ET.fromstring(self.view_arch)
            if root.get('create') == '0':
                self.can_create = False
            if root.get('edit') == '0':
                self.can_write = False

            print(f"DEBUG: get_view for {self.model_name} (list)")

            try:
                all_fields = session.client.call_kw(
                    self.model_name, 'fields_get', [],
                    {'attributes': ['type', 'string', 'relation', 'selection', 'digits']})
                print(f"DEBUG: fetching field definitions for {self.model_name}...")
                for fname, finfo in all_fields.items():
                    if fname in self.view_fields:
                        merged = dict(finfo)
                        merged.update(self.view_fields[fname])
                        self.view_fields[fname] = merged
                    else:
                        self.view_fields[fname] = finfo
            except Exception as e:
                print(f"Warning: fields_get failed: {e}")

            self._parse_columns()
        except Exception as e:
            print(f"Erreur arch List {self.model_name}: {e}")

    def _parse_columns(self):
        self.columns_info = []
        try:
            root = ET.fromstring(self.view_arch)
            for field_node in root.findall('.//field'):
                fname = field_node.get('name', '')
                if not fname:
                    continue
                attrs = dict(field_node.attrib)
                invisible = attrs.get('column_invisible', attrs.get('invisible', ''))
                if invisible in ('1', 'True', 'true'):
                    continue
                optional = attrs.get('optional', 'show')
                if optional == 'hide':
                    continue
                f_info = self.view_fields.get(fname, {})
                label = attrs.get('string', f_info.get('string', fname))
                self.columns_info.append((fname, label, attrs))
        except Exception as e:
            print(f"Parse columns error: {e}")

    # ══════════════════════════════════════════════════════════════
    #   UI SETUP
    # ══════════════════════════════════════════════════════════════
    def _setup_list(self):
        # ── Main Control Bar ──
        self.control_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.control_bar.set_margin_start(8)
        self.control_bar.set_margin_end(8)
        self.control_bar.set_margin_top(4)
        self.control_bar.set_margin_bottom(4)
        self.append(self.control_bar)

        if self.can_create:
            self.btn_new = Gtk.Button(label="Créer")
            self.btn_new.add_css_class('suggested-action')
            self.btn_new.set_icon_name('list-add-symbolic')
            self.btn_new.connect('clicked', lambda b: self.emit('create-clicked'))
            self.control_bar.append(self.btn_new)

        # ── Selection action bar (hidden by default) ──
        self.action_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.action_bar.set_margin_start(8)
        self.action_bar.set_margin_end(8)
        self.action_bar.set_margin_top(4)
        self.action_bar.set_margin_bottom(4)
        self.action_bar.set_visible(False)
        self.action_bar.add_css_class('toolbar')
        self.append(self.action_bar)

        self.selection_label = Gtk.Label(label='')
        self.selection_label.add_css_class('dim-label')
        self.action_bar.append(self.selection_label)

        # "Select all X records" button
        self.btn_select_all = Gtk.Button()
        self.btn_select_all.add_css_class('flat')
        self.btn_select_all.add_css_class('link')
        self.btn_select_all.set_visible(False)
        self.btn_select_all.connect('clicked', self._on_select_all_server)
        self.action_bar.append(self.btn_select_all)

        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.action_bar.append(sep)

        # Modifier button (visible if 1 selected and can_write)
        self.btn_edit_sel = Gtk.Button(label='Modifier')
        self.btn_edit_sel.set_icon_name('document-edit-symbolic')
        self.btn_edit_sel.add_css_class('flat')
        self.btn_edit_sel.connect('clicked', self._on_edit_selected)
        self.action_bar.append(self.btn_edit_sel)

        # Action MenuButton
        self.btn_action = Gtk.MenuButton(label='Action')
        self.btn_action.set_icon_name('system-run-symbolic')
        self.btn_action.add_css_class('flat')
        self.action_bar.append(self.btn_action)

        # Print MenuButton
        self.btn_print = Gtk.MenuButton(label='Imprimer')
        self.btn_print.set_icon_name('printer-symbolic')
        self.btn_print.add_css_class('flat')
        self.action_bar.append(self.btn_print)

        # Delete selected
        self.btn_delete_sel = Gtk.Button(label='Supprimer')
        self.btn_delete_sel.set_icon_name('user-trash-symbolic')
        self.btn_delete_sel.add_css_class('flat')
        self.btn_delete_sel.add_css_class('destructive-action')
        self.btn_delete_sel.connect('clicked', self._on_delete_selected)
        self.action_bar.append(self.btn_delete_sel)

        # ── Header row with "Select All" checkbox ──
        self.header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.header_row.set_margin_start(8)
        self.header_row.set_margin_end(8)
        self.header_row.set_margin_top(2)
        self.header_row.set_margin_bottom(2)
        self.append(self.header_row)

        self._header_check = Gtk.CheckButton()
        self._header_check.set_tooltip_text('Tout sélectionner / Tout désélectionner')
        self._header_check.connect('toggled', self._on_header_check_toggled)
        self.header_row.append(self._header_check)

        self.record_count_label = Gtk.Label(label='')
        self.record_count_label.add_css_class('dim-label')
        self.header_row.append(self.record_count_label)

        # ── ColumnView ──
        self.store = Gio.ListStore.new(_RowData)
        self.selection = Gtk.NoSelection.new(self.store)
        
        self.column_view = Gtk.ColumnView.new(self.selection)
        self.column_view.add_css_class('data-table')
        self.column_view.set_show_column_separators(True)
        self.column_view.set_show_row_separators(True)

        # ── 1. Checkbox column ──
        check_factory = Gtk.SignalListItemFactory()
        check_factory.connect('setup', self._on_check_setup)
        check_factory.connect('bind', self._on_check_bind)

        check_col = Gtk.ColumnViewColumn.new('', check_factory)
        check_col.set_fixed_width(40)
        check_col.set_resizable(False)
        self.column_view.append_column(check_col)

        # ── 2. Data columns ──
        for fname, label, attrs in self.columns_info:
            factory = Gtk.SignalListItemFactory()
            col_name = fname
            f_info = self.view_fields.get(fname, {})
            f_type = f_info.get('type', 'char')
            widget_attr = attrs.get('widget', '')
            
            is_image = (f_type in ('binary', 'image') 
                        or widget_attr == 'image'
                        or any(p in fname for p in ('avatar', 'image_')))

            if is_image:
                def on_setup_img(f, item):
                    box = Gtk.Box()
                    box.set_size_request(36, 36)
                    item.set_child(box)

                def on_bind_img(f, item, _n=col_name):
                    rec = item.get_item()
                    val = rec.data.get(_n)
                    box = item.get_child()
                    while c := box.get_first_child():
                        box.remove(c)
                    if val and isinstance(val, str) and len(val) > 100:
                        from ui.widgets.binary import ImageWidget
                        pic = ImageWidget.create_from_base64(val, size=32)
                        box.append(pic)
                    else:
                        icon = Gtk.Image.new_from_icon_name('avatar-default-symbolic')
                        icon.set_pixel_size(24)
                        box.append(icon)

                factory.connect('setup', on_setup_img)
                factory.connect('bind', on_bind_img)
            else:
                def on_setup(f, item, _n=col_name, _t=f_type):
                    label_w = Gtk.Label(xalign=0)
                    label_w.set_margin_start(6)
                    label_w.set_margin_end(6)
                    label_w.set_margin_top(4)
                    label_w.set_margin_bottom(4)
                    label_w.set_ellipsize(Pango.EllipsizeMode.END)
                    label_w.set_max_width_chars(40)
                    item.set_child(label_w)

                def on_bind(f, item, _n=col_name, _t=f_type, _fi=f_info, _wa=widget_attr):
                    rec = item.get_item()
                    val = rec.data.get(_n)
                    label_w = item.get_child()
                    
                    if _t == 'boolean':
                        label_w.set_text('✓' if val else '✗')
                    elif _t in ('many2one',) and isinstance(val, (list, tuple)):
                        label_w.set_text(str(val[1]) if len(val) > 1 else '')
                    elif _t == 'selection':
                        sel = _fi.get('selection', [])
                        text = str(val) if val else ''
                        for sv, sl in sel:
                            if sv == val:
                                text = str(sl)
                                break
                        label_w.set_text(text)
                    elif _t in ('float', 'monetary'):
                        try:
                            label_w.set_text(f'{float(val):,.2f}' if val else '0.00')
                        except (ValueError, TypeError):
                            label_w.set_text(str(val) if val else '')
                        label_w.set_xalign(1)
                    elif _t == 'integer':
                        label_w.set_text(str(int(val)) if val else '0')
                        label_w.set_xalign(1)
                    elif _t in ('many2many', 'one2many'):
                        if isinstance(val, list):
                            label_w.set_text(f'{len(val)} enr.')
                        else:
                            label_w.set_text('')
                    elif _wa == 'activity_exception':
                        label_w.set_text('')
                    elif val is not False and val is not None:
                        text = str(val)
                        if len(text) > 100:
                            if text.startswith(('/9j/', 'iVBOR', '{', '[')):
                                label_w.set_text('…')
                            else:
                                label_w.set_text(text[:80] + '…')
                        else:
                            label_w.set_text(text)
                    else:
                        label_w.set_text('')

                factory.connect('setup', on_setup)
                factory.connect('bind', on_bind)

            col = Gtk.ColumnViewColumn.new(label, factory)
            col.set_resizable(True)
            if is_image:
                col.set_fixed_width(50)
            else:
                col.set_expand(f_type in ('char', 'text', 'html'))
            self.column_view.append_column(col)

        # Activate on double-click or Enter key
        self.column_view.connect('activate', self._on_row_activated)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_child(self.column_view)
        self.append(scroll)

        # ── 3. Totals footer ──
        self.totals_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.totals_bar.add_css_class('toolbar')
        self.totals_bar.set_margin_start(4)
        self.totals_bar.set_margin_end(4)
        self.totals_bar.set_margin_top(2)
        self.totals_bar.set_margin_bottom(2)
        self.totals_bar.set_visible(False)
        self.append(self.totals_bar)

    # ══════════════════════════════════════════════════════════════
    #   CHECKBOX COLUMN
    # ══════════════════════════════════════════════════════════════
    def _on_check_setup(self, factory, item):
        check = Gtk.CheckButton()
        check.set_halign(Gtk.Align.CENTER)
        item.set_child(check)

    def _on_check_bind(self, factory, item):
        check = item.get_child()
        rec = item.get_item()
        rec_id = rec.data.get('id')
        
        # Set initial state
        check.set_active(rec_id in self._checked_ids)
        
        # Connect toggle with the record id
        # Disconnect old handler if any
        if hasattr(check, '_handler_id') and check._handler_id:
            check.disconnect(check._handler_id)
        check._handler_id = check.connect('toggled', self._on_row_check_toggled, rec_id)



    def _on_row_check_toggled(self, check, rec_id):
        """Individual row checkbox toggled."""
        if check.get_active():
            self._checked_ids.add(rec_id)
        else:
            self._checked_ids.discard(rec_id)
            self._select_all_server = False

        self._update_selection_ui()
        self._update_totals_for_selection()

    def _on_header_check_toggled(self, check):
        """Header checkbox: select/deselect all visible rows."""
        active = check.get_active()
        
        if active:
            # Select all visible
            self._checked_ids = set(self.all_record_ids)
        else:
            # Deselect all
            self._checked_ids.clear()
            self._select_all_server = False

        # Update all row checkboxes by refreshing the view
        self._refresh_checkboxes()
        self._update_selection_ui()
        self._update_totals_for_selection()

    def _on_select_all_server(self, btn):
        """Select ALL records on the server, not just visible ones."""
        self._select_all_server = True
        self._checked_ids = set(self.all_record_ids)
        self._update_selection_ui()

    def _refresh_checkboxes(self):
        """Force refresh of checkbox states by removing and re-adding items."""
        n = self.store.get_n_items()
        if n == 0:
            return
        # Save all items, clear, re-add — forces factory rebind
        items = [self.store.get_item(i) for i in range(n)]
        self.store.remove_all()
        for item in items:
            self.store.append(item)

    def _update_selection_ui(self):
        """Update the action bar based on current selection."""
        count = len(self._checked_ids)
        
        if count > 0:
            self.action_bar.set_visible(True)
            
            if self._select_all_server:
                self.selection_label.set_text(
                    f"Tous les {self.total_count} enregistrements sélectionnés")
                self.btn_select_all.set_visible(False)
            else:
                self.selection_label.set_text(f"{count} sélectionné(s)")
                
                # Show "Select all X records" if all visible are selected and there are more
                all_visible_selected = (count == len(self.all_record_ids) and 
                                        self.total_count > len(self.all_record_ids))
                if all_visible_selected:
                    self.btn_select_all.set_label(
                        f"Sélectionner les {self.total_count} enregistrements")
                    self.btn_select_all.set_visible(True)
                else:
                    self.btn_select_all.set_visible(False)
            
            self._ensure_action_menus()
            
            # Show "Edit" button only if 1 record selected and user has write access
            self.btn_edit_sel.set_visible(count == 1 and self.can_write)
        else:
            self.action_bar.set_visible(False)
            self.btn_select_all.set_visible(False)

    def _on_edit_selected(self, btn):
        """Emit edit-clicked signal for the single selected record."""
        selected_ids = list(self._checked_ids)
        if len(selected_ids) == 1:
            self.emit('edit-clicked', selected_ids[0])

    def _get_selected_ids(self):
        """Return list of selected record IDs."""
        if self._select_all_server:
            # Fetch ALL ids from server
            try:
                all_ids = session.client.call_kw(
                    self.model_name, 'search', [self.domain],
                    {'context': self.context})
                return all_ids
            except Exception:
                return list(self._checked_ids)
        return list(self._checked_ids)

    # ══════════════════════════════════════════════════════════════
    #   ACTIVATION
    # ══════════════════════════════════════════════════════════════
    def _on_row_activated(self, column_view, position):
        """On double-click or Enter, open the record in form view."""
        item = self.store.get_item(position)
        if item and item.data.get('id'):
            self.emit('record-activated', item.data['id'])

    def get_all_record_ids(self):
        return self.all_record_ids

    # ══════════════════════════════════════════════════════════════
    #   DATA LOADING
    # ══════════════════════════════════════════════════════════════
    def load_data(self):
        self._loaded_records = []  # Store for totals recalculation
        fields = [fname for fname, _, _ in self.columns_info]
        if 'id' not in fields:
            fields.append('id')

        valid_fields = [f for f in fields if f in self.view_fields or f == 'id']
        
        try:
            records = self.model.search_read(
                domain=self.domain, fields=valid_fields, limit=80, context=self.context)
            self.store.remove_all()
            self.all_record_ids = []
            self._checked_ids.clear()
            self._select_all_server = False
            self._loaded_records = records
            for rec in records:
                self.store.append(_RowData(rec))
                self.all_record_ids.append(rec.get('id'))
            
            # Get total count for "select all" feature
            try:
                self.total_count = session.client.call_kw(
                    self.model_name, 'search_count', [self.domain],
                    {'context': self.context})
            except Exception:
                self.total_count = len(records)

            # Update totals footer & record count label
            self._update_totals(records)
            self._update_selection_ui()
            self.record_count_label.set_text(f"{self.total_count} enregistrements")

        except Exception as e:
            print(f"Erreur données List {self.model_name}: {e}")
            try:
                records = self.model.search_read(
                    domain=self.domain, fields=['id', 'display_name'], limit=80, context=self.context)
                self.store.remove_all()
                self.all_record_ids = []
                for rec in records:
                    self.store.append(_RowData(rec))
                    self.all_record_ids.append(rec.get('id'))
            except Exception as e2:
                print(f"Retry also failed: {e2}")

    # ══════════════════════════════════════════════════════════════
    #   TOTALS FOOTER
    # ══════════════════════════════════════════════════════════════
    def _update_totals(self, records):
        """Compute and display totals for numeric columns."""
        self._render_totals_bar(records)

    def _update_totals_for_selection(self):
        """Recalculate totals based on current checkbox selection."""
        if not hasattr(self, '_loaded_records'):
            return
        if self._checked_ids:
            # Show totals for selected records only
            selected_records = [r for r in self._loaded_records
                                if r.get('id') in self._checked_ids]
            self._render_totals_bar(selected_records)
        else:
            # Show totals for all records
            self._render_totals_bar(self._loaded_records)

    def _render_totals_bar(self, records):
        """Render the totals bar with sums of numeric columns."""
        while child := self.totals_bar.get_first_child():
            self.totals_bar.remove(child)

        if not records:
            self.totals_bar.set_visible(False)
            return

        has_numeric = False
        numeric_types = ('float', 'monetary', 'integer')

        # Checkbox column spacer (40px)
        spacer = Gtk.Label(label='')
        spacer.set_size_request(40, -1)
        self.totals_bar.append(spacer)

        for fname, col_label, attrs in self.columns_info:
            f_info = self.view_fields.get(fname, {})
            f_type = f_info.get('type', 'char')

            total_label = Gtk.Label()
            total_label.set_margin_start(6)
            total_label.set_margin_end(6)
            total_label.set_margin_top(6)
            total_label.set_margin_bottom(6)
            total_label.set_hexpand(f_type in ('char', 'text', 'html'))

            if f_type in numeric_types:
                total = 0
                for rec in records:
                    val = rec.get(fname)
                    if val and isinstance(val, (int, float)):
                        total += val

                if f_type in ('float', 'monetary'):
                    total_label.set_text(f'{total:,.2f}')
                else:
                    total_label.set_text(f'{int(total):,}')
                total_label.set_xalign(1)
                total_label.add_css_class('fw-bold')
                has_numeric = True
            else:
                total_label.set_text('')

            self.totals_bar.append(total_label)

        self.totals_bar.set_visible(has_numeric)

    # ══════════════════════════════════════════════════════════════
    #   ACTION / PRINT MENUS
    # ══════════════════════════════════════════════════════════════
    def _ensure_action_menus(self):
        if self._server_actions is not None:
            return
        self._load_action_menus()

    def _load_action_menus(self):
        try:
            self._server_actions = session.client.call_kw(
                'ir.actions.server', 'search_read',
                [[('model_id.model', '=', self.model_name),
                  ('binding_type', '=', 'action')]],
                {'fields': ['id', 'name'], 'limit': 30})
        except Exception:
            self._server_actions = []

        try:
            self._report_actions = session.client.call_kw(
                'ir.actions.report', 'search_read',
                [[('model', '=', self.model_name),
                  ('binding_type', '=', 'report')]],
                {'fields': ['id', 'name', 'report_type', 'report_name'], 'limit': 30})
        except Exception:
            self._report_actions = []

        self._build_action_popover()
        self._build_print_popover()

    def _build_action_popover(self):
        if not self._server_actions:
            self.btn_action.set_sensitive(False)
            return
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_start(6)
        box.set_margin_end(6)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        for act in self._server_actions:
            btn = Gtk.Button(label=act['name'])
            btn.add_css_class('flat')
            btn.set_halign(Gtk.Align.START)
            act_id = act['id']
            btn.connect('clicked', lambda b, aid=act_id: self._run_server_action(aid))
            box.append(btn)
        popover = Gtk.Popover()
        popover.set_child(box)
        self.btn_action.set_popover(popover)

    def _build_print_popover(self):
        if not self._report_actions:
            self.btn_print.set_sensitive(False)
            return
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_start(6)
        box.set_margin_end(6)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        for rep in self._report_actions:
            btn = Gtk.Button(label=rep['name'])
            btn.add_css_class('flat')
            btn.set_halign(Gtk.Align.START)
            report_name = rep.get('report_name', '')
            btn.connect('clicked', lambda b, rn=report_name: self._run_report(rn))
            box.append(btn)
        popover = Gtk.Popover()
        popover.set_child(box)
        self.btn_print.set_popover(popover)

    def _run_server_action(self, action_id):
        selected_ids = self._get_selected_ids()
        if not selected_ids:
            return
        try:
            ctx = dict(session.client.context or {})
            ctx['active_ids'] = selected_ids
            ctx['active_id'] = selected_ids[0]
            ctx['active_model'] = self.model_name
            result = session.client.call_kw(
                'ir.actions.server', 'run', [[action_id]],
                {'context': ctx})
            print(f"DEBUG: List action {action_id} on {len(selected_ids)} records → {result}")
            self.load_data()
        except Exception as e:
            print(f"Erreur action serveur liste: {e}")

    def _run_report(self, report_name):
        selected_ids = self._get_selected_ids()
        if not selected_ids:
            return
        try:
            ids_str = ','.join(str(i) for i in selected_ids)
            url = f"{session.client.url}/report/pdf/{report_name}/{ids_str}"
            response = session.client.session.get(url, timeout=30)
            if response.status_code == 200:
                import tempfile, os, subprocess
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                    f.write(response.content)
                    pdf_path = f.name
                print(f"DEBUG: Report saved to {pdf_path}")
                if os.name == 'nt':
                    os.startfile(pdf_path)
                else:
                    subprocess.Popen(['xdg-open', pdf_path])
            else:
                print(f"Erreur rapport: HTTP {response.status_code}")
        except Exception as e:
            print(f"Erreur rapport {report_name}: {e}")

    def _on_delete_selected(self, btn):
        selected_ids = self._get_selected_ids()
        if not selected_ids:
            return
        dialog = Adw.MessageDialog.new(
            self.get_root(),
            f"Supprimer {len(selected_ids)} enregistrement(s) ?",
            "Cette action est irréversible."
        )
        dialog.add_response('cancel', 'Annuler')
        dialog.add_response('delete', 'Supprimer')
        dialog.set_response_appearance('delete', Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect('response', self._on_delete_confirmed, selected_ids)
        dialog.present()

    def _on_delete_confirmed(self, dialog, response, ids):
        if response != 'delete':
            return
        try:
            session.client.call_kw(self.model_name, 'unlink', [ids])
            print(f"DEBUG: unlink({self.model_name}, {ids})")
            self.load_data()
        except Exception as e:
            print(f"Erreur suppression liste: {e}")
