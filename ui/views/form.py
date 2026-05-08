# -*- coding: utf-8 -*-
# Odoo GTK 19 — Form View (Full CRUD + Navigation + Action Buttons)

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject, Gio, GLib
from core import Model, session
from ui.views.parser import FormParser


class FormView(Gtk.Box):
    __gsignals__ = {
        'record-activated': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'back-to-list': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'open-report': (GObject.SignalFlags.RUN_FIRST, None, (str, int, str)),
    }

    def __init__(self, model_name, view_id=None, res_id=None, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        self.model_name = model_name
        self.model = Model(model_name)
        self.view_id = view_id
        self.res_id = res_id
        self.view_arch = None
        self.view_fields = {}
        self.parser = None
        self.current_record_data = {}
        self.editing = False

        # Navigation state — set by TabPage when opening from a list
        self.record_ids = []   # All visible record IDs from the list
        self.current_index = -1

        # Actions & reports cache (loaded once per model)
        self._server_actions = None
        self._report_actions = None

        self._load_view_arch(view_id)
        self._build_toolbar()
        self._build_form_area()
        self._setup_form()

    # ══════════════════════════════════════════════════════════════
    #   VIEW ARCH LOADING
    # ══════════════════════════════════════════════════════════════
    def _load_view_arch(self, view_id):
        try:
            res = session.client.get_view(self.model_name, view_id=view_id, view_type='form')
            self.view_arch = res.get('arch', '<form/>')
            self.view_fields = res.get('fields', {})
            print(f"DEBUG: get_view for {self.model_name} (form)")

            # Fetch full field definitions for better widget creation
            try:
                all_fields = session.client.call_kw(
                    self.model_name, 'fields_get', [],
                    {'attributes': ['type', 'string', 'relation', 'selection', 'digits',
                                    'help', 'readonly', 'required', 'translate', 'size']})
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

        except Exception as e:
            print(f"Erreur arch Form {self.model_name}: {e}")
            self.view_arch = '<form><field name="display_name"/></form>'

    # ══════════════════════════════════════════════════════════════
    #   TOOLBAR (CRUD + Navigation + Actions/Print)
    # ══════════════════════════════════════════════════════════════
    def _build_toolbar(self):
        self.toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.toolbar.set_margin_start(6)
        self.toolbar.set_margin_end(6)
        self.toolbar.set_margin_top(4)
        self.toolbar.set_margin_bottom(4)
        self.toolbar.add_css_class('toolbar')
        self.append(self.toolbar)

        # ── Back button ──
        self.btn_back = Gtk.Button(icon_name='go-previous-symbolic')
        self.btn_back.set_tooltip_text('Retour à la liste')
        self.btn_back.add_css_class('flat')
        self.btn_back.connect('clicked', self._on_back)
        self.toolbar.append(self.btn_back)

        sep1 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.toolbar.append(sep1)

        # ── New ──
        self.btn_new = Gtk.Button(label='Nouveau')
        self.btn_new.set_icon_name('document-new-symbolic')
        self.btn_new.add_css_class('flat')
        self.btn_new.connect('clicked', self._on_new)
        self.toolbar.append(self.btn_new)

        # ── Edit / Save / Discard ──
        self.btn_edit = Gtk.Button(label='Modifier')
        self.btn_edit.set_icon_name('document-edit-symbolic')
        self.btn_edit.add_css_class('flat')
        self.btn_edit.connect('clicked', self._on_edit)
        self.toolbar.append(self.btn_edit)

        self.btn_save = Gtk.Button(label='Enregistrer')
        self.btn_save.set_icon_name('document-save-symbolic')
        self.btn_save.add_css_class('suggested-action')
        self.btn_save.connect('clicked', self._on_save)
        self.btn_save.set_visible(False)
        self.toolbar.append(self.btn_save)

        self.btn_discard = Gtk.Button(label='Annuler')
        self.btn_discard.set_icon_name('edit-undo-symbolic')
        self.btn_discard.add_css_class('flat')
        self.btn_discard.connect('clicked', self._on_discard)
        self.btn_discard.set_visible(False)
        self.toolbar.append(self.btn_discard)

        # ── Delete ──
        self.btn_delete = Gtk.Button(icon_name='user-trash-symbolic')
        self.btn_delete.set_tooltip_text('Supprimer')
        self.btn_delete.add_css_class('flat')
        self.btn_delete.add_css_class('destructive-action')
        self.btn_delete.connect('clicked', self._on_delete)
        self.toolbar.append(self.btn_delete)

        sep2 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.toolbar.append(sep2)

        # ── Actions menu button ──
        self.btn_action = Gtk.MenuButton(label='Action')
        self.btn_action.set_icon_name('system-run-symbolic')
        self.btn_action.add_css_class('flat')
        self.toolbar.append(self.btn_action)

        # ── Print menu button ──
        self.btn_print = Gtk.MenuButton(label='Imprimer')
        self.btn_print.set_icon_name('printer-symbolic')
        self.btn_print.add_css_class('flat')
        self.toolbar.append(self.btn_print)

        # ── Spacer ──
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        self.toolbar.append(spacer)

        # ── Navigation ──
        self.btn_prev = Gtk.Button(icon_name='go-previous-symbolic')
        self.btn_prev.set_tooltip_text('Précédent')
        self.btn_prev.add_css_class('flat')
        self.btn_prev.connect('clicked', self._on_prev)
        self.toolbar.append(self.btn_prev)

        self.nav_label = Gtk.Label(label='')
        self.nav_label.add_css_class('dim-label')
        self.toolbar.append(self.nav_label)

        self.btn_next = Gtk.Button(icon_name='go-next-symbolic')
        self.btn_next.set_tooltip_text('Suivant')
        self.btn_next.add_css_class('flat')
        self.btn_next.connect('clicked', self._on_next)
        self.toolbar.append(self.btn_next)

    def _build_form_area(self):
        """Build the scrolled area that will host the parsed form."""
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_vexpand(True)
        self.append(self.scroll)

    # ══════════════════════════════════════════════════════════════
    #   FORM RENDERING
    # ══════════════════════════════════════════════════════════════
    def _setup_form(self):
        # Create parser with current record data and a button callback
        self.parser = FormParser(self.view_fields, self.current_record_data,
                                 button_callback=self._on_form_button_clicked)

        # Parse the arch and get the widget tree
        try:
            form_widget = self.parser.parse(self.view_arch)
            if form_widget:
                self.scroll.set_child(form_widget)
        except Exception as e:
            print(f"Erreur parsing Form {self.model_name}: {e}")
            import traceback
            traceback.print_exc()
            error_label = Gtk.Label(label=f"Erreur de rendu: {e}")
            self.scroll.set_child(error_label)

        self._update_toolbar_state()

    def _update_toolbar_state(self):
        """Sync toolbar button visibility with current mode (edit/read)."""
        has_record = self.res_id is not None
        self.btn_edit.set_visible(has_record and not self.editing)
        self.btn_save.set_visible(self.editing)
        self.btn_discard.set_visible(self.editing)
        self.btn_delete.set_sensitive(has_record and not self.editing)
        self.btn_new.set_sensitive(not self.editing)

        # Navigation
        has_list = len(self.record_ids) > 1
        self.btn_prev.set_sensitive(has_list and self.current_index > 0)
        self.btn_next.set_sensitive(has_list and self.current_index < len(self.record_ids) - 1)
        if has_list and self.current_index >= 0:
            self.nav_label.set_text(f"{self.current_index + 1} / {len(self.record_ids)}")
        else:
            self.nav_label.set_text('')

        # Load actions/print menus lazily
        self._ensure_action_menus()

    def _set_all_readonly(self, readonly):
        """Lock/unlock all field widgets in the form."""
        if self.parser:
            for fname, wid in self.parser.field_widgets.items():
                # Don't unlock fields that are always readonly from XML
                if readonly:
                    wid.set_readonly(True)
                else:
                    # Only unlock if not marked readonly in the XML arch
                    xml_readonly = wid.attrs.get('readonly', '')
                    if xml_readonly in ('1', 'True', 'true'):
                        wid.set_readonly(True)
                    else:
                        wid.set_readonly(False)

    def load_record(self):
        """Alias for load_data to match tab_page usage."""
        self.load_data()

    def load_data(self):
        """Load record data or defaults for new records."""
        ctx = session.client.context or {}
        
        if self.res_id:
            # Mode Edition/Lecture
            self.editing = False
            # Only request fields that exist in view_fields
            fields = [fname for fname in self.view_fields.keys()
                    if not fname.startswith('_')]
            if 'display_name' not in fields:
                fields.append('display_name')

            try:
                records = session.client.call_kw(
                    self.model_name, 'read', [[self.res_id]],
                    {'fields': fields, 'context': ctx})
                if records:
                    self.current_record_data = records[0]
                    self._setup_form()
            except Exception as e:
                print(f"Error loading record {self.res_id}: {e}")
                # Fallback retry logic
                try:
                    records = session.client.call_kw(self.model_name, 'read', [[self.res_id]], {'fields': ['display_name']})
                    if records: 
                        self.current_record_data = records[0]
                        self._setup_form()
                except: pass
        else:
            # Mode Création
            self.editing = True
            self.current_record_data = {}
            try:
                # Call default_get to fetch default values from Odoo
                fields = list(self.view_fields.keys())
                defaults = session.client.call_kw(
                    self.model_name, 'default_get', [fields],
                    {'context': ctx})
                self.current_record_data = defaults
                self._setup_form()
            except Exception as e:
                print(f"Error fetching defaults: {e}")
                self._setup_form()
        
        self._update_toolbar_state()
        self._set_all_readonly(not self.editing)

    def _update_toolbar_state(self):
        """Sync toolbar button visibility with current mode (edit/read)."""
        has_record = self.res_id is not None
        self.btn_edit.set_visible(has_record and not self.editing)
        self.btn_save.set_visible(self.editing)
        self.btn_discard.set_visible(self.editing)
        self.btn_delete.set_sensitive(has_record and not self.editing)
        self.btn_new.set_sensitive(not self.editing)

        # Navigation
        has_list = len(self.record_ids) > 1
        self.btn_prev.set_sensitive(has_list and self.current_index > 0)
        self.btn_next.set_sensitive(has_list and self.current_index < len(self.record_ids) - 1)
        if has_list and self.current_index >= 0:
            self.nav_label.set_text(f"{self.current_index + 1} / {len(self.record_ids)}")
        else:
            self.nav_label.set_text('')

        # Load actions/print menus lazily
        self._ensure_action_menus()

    def set_record_ids(self, ids, current_id=None):
        """Set the full list of record IDs (from list view) for navigation."""
        self.record_ids = list(ids) if ids else []
        if current_id and current_id in self.record_ids:
            self.current_index = self.record_ids.index(current_id)
        elif self.record_ids:
            self.current_index = 0
        else:
            self.current_index = -1

    # ══════════════════════════════════════════════════════════════
    #   TOOLBAR HANDLERS
    # ══════════════════════════════════════════════════════════════
    def _on_back(self, btn):
        self.emit('back-to-list')

    def _on_new(self, btn):
        """Create a new blank record in edit mode."""
        self.res_id = None
        self.current_record_data = {}
        self.editing = True
        self._setup_form()
        self._set_all_readonly(False)

    def _on_edit(self, btn):
        """Switch to edit mode (unlock widgets)."""
        self.editing = True
        self._set_all_readonly(False)
        self._update_toolbar_state()

    def _is_field_writable(self, fname):
        """Check if a field can be written to (not computed/readonly from model)."""
        finfo = self.view_fields.get(fname, {})
        ftype = finfo.get('type', 'char')
        
        # Skip known non-writable fields
        skip_fields = {'id', 'create_uid', 'create_date', 'write_uid', 'write_date',
                       'display_name', '__last_update', 'activity_state',
                       'message_follower_ids', 'message_ids', 'message_main_attachment_id'}
        if fname in skip_fields:
            return False

        # Skip non-stored computed fields
        if finfo.get('store', True) is False:
            return False
        
        # Only filter by readonly if it's a boolean True from the model definition,
        # NOT an XML expression string like "state != 'draft'"
        readonly_val = finfo.get('readonly')
        if readonly_val is True:
            # It's readonly at the model level — check if it's a computed-only field
            computed_suffixes = ('_count', '_string', '_display', '_url', '_warning',
                                '_ids_count', '_amount', '_total', '_signed')
            if any(fname.endswith(s) for s in computed_suffixes):
                return False
        
        return True

    def _values_equal(self, old_val, new_val, ftype):
        """Smart comparison of old and new values accounting for Odoo data quirks."""
        # Normalize False/None/empty
        if old_val in (False, None, '', 0) and new_val in (False, None, '', 0):
            if ftype in ('char', 'text', 'html'):
                return str(old_val or '') == str(new_val or '')
            return True
        
        # Many2one: compare just the ID
        if ftype == 'many2one':
            old_id = old_val[0] if isinstance(old_val, (list, tuple)) and old_val else old_val
            new_id = new_val[0] if isinstance(new_val, (list, tuple)) and new_val else new_val
            return old_id == new_id
        
        return old_val == new_val

    def _on_save(self, btn):
        """Collect values from all widgets and write/create via RPC."""
        if not self.parser:
            return

        vals = {}
        for fname, wid in self.parser.field_widgets.items():
            # Skip non-writable fields
            if not self._is_field_writable(fname):
                continue
            
            try:
                new_val = wid.get_value()
                old_val = self.current_record_data.get(fname)
                ftype = self.view_fields.get(fname, {}).get('type', 'char')
                
                # One2many / Many2many: get_value() returns command tuples
                if ftype in ('one2many', 'many2many'):
                    if new_val:  # Non-empty command list
                        vals[fname] = new_val
                    continue

                # Only send changed values
                if not self._values_equal(old_val, new_val, ftype):
                    # Normalize many2one: (id, name) → id
                    if ftype == 'many2one':
                        if isinstance(new_val, (list, tuple)) and len(new_val) >= 1:
                            new_val = new_val[0]
                    vals[fname] = new_val
            except Exception as e:
                print(f"Error collecting value for {fname}: {e}")

        if not vals and self.res_id:
            # Nothing changed, just go back to read mode
            self.editing = False
            self._set_all_readonly(True)
            self._update_toolbar_state()
            return

        try:
            # Build context with lang for translatable fields
            ctx = dict(session.client.context or {})

            if self.res_id:
                # UPDATE existing record
                session.client.call_kw(self.model_name, 'write',
                                       [[self.res_id], vals],
                                       {'context': ctx})
                print(f"DEBUG: write({self.model_name}, {self.res_id}) = {list(vals.keys())}")
            else:
                # CREATE new record
                new_id = session.client.call_kw(self.model_name, 'create',
                                                [vals],
                                                {'context': ctx})
                if isinstance(new_id, list):
                    new_id = new_id[0]
                self.res_id = new_id
                if self.res_id not in self.record_ids:
                    self.record_ids.insert(0, self.res_id)
                    self.current_index = 0
                print(f"DEBUG: create({self.model_name}) = {self.res_id}")

            # Reload to get computed fields + switch to readonly
            self.load_data()
        except Exception as e:
            print(f"Erreur sauvegarde {self.model_name}: {e}")
            # Show error in a dialog
            dialog = Adw.MessageDialog.new(
                self.get_root(),
                f"Erreur de sauvegarde",
                str(e)
            )
            dialog.add_response('ok', 'OK')
            dialog.present()

    def _on_discard(self, btn):
        """Cancel editing and reload original data."""
        if self.res_id:
            self.load_data()
        else:
            # Was creating a new record — go back
            self.emit('back-to-list')

    def _on_delete(self, btn):
        """Delete the current record after confirmation."""
        if not self.res_id:
            return

        dialog = Adw.MessageDialog.new(
            self.get_root(),
            "Supprimer l'enregistrement ?",
            f"Voulez-vous vraiment supprimer cet enregistrement de {self.model_name} ?"
        )
        dialog.add_response('cancel', 'Annuler')
        dialog.add_response('delete', 'Supprimer')
        dialog.set_response_appearance('delete', Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect('response', self._on_delete_confirmed)
        dialog.present()

    def _on_delete_confirmed(self, dialog, response):
        if response != 'delete':
            return
        try:
            session.client.call_kw(self.model_name, 'unlink', [[self.res_id]])
            print(f"DEBUG: unlink({self.model_name}, {self.res_id})")
            # Remove from navigation list
            if self.res_id in self.record_ids:
                self.record_ids.remove(self.res_id)
            self.res_id = None
            self.emit('back-to-list')
        except Exception as e:
            print(f"Erreur suppression: {e}")

    # ══════════════════════════════════════════════════════════════
    #   NAVIGATION
    # ══════════════════════════════════════════════════════════════
    def _on_prev(self, btn):
        if self.current_index > 0:
            self.current_index -= 1
            self.res_id = self.record_ids[self.current_index]
            self.load_data()

    def _on_next(self, btn):
        if self.current_index < len(self.record_ids) - 1:
            self.current_index += 1
            self.res_id = self.record_ids[self.current_index]
            self.load_data()

    # ══════════════════════════════════════════════════════════════
    #   ACTIONS / PRINT MENUS
    # ══════════════════════════════════════════════════════════════
    def _ensure_action_menus(self):
        """Lazily load server actions and reports for this model."""
        if self._server_actions is None:
            self._load_action_menus()

    def _load_action_menus(self):
        """Fetch ir.actions.server and ir.actions.report for this model."""
        try:
            # Server actions
            self._server_actions = session.client.call_kw(
                'ir.actions.server', 'search_read',
                [[('model_id.model', '=', self.model_name),
                  ('binding_type', '=', 'action')]],
                {'fields': ['id', 'name'], 'limit': 30})
        except Exception:
            self._server_actions = []

        try:
            # Reports
            self._report_actions = session.client.call_kw(
                'ir.actions.report', 'search_read',
                [[('model', '=', self.model_name),
                  ('binding_type', '=', 'report')]],
                {'fields': ['id', 'name', 'report_type', 'report_name'], 'limit': 30})
        except Exception:
            self._report_actions = []

        # Build simple popovers for both menus
        self._build_action_popover()
        self._build_print_popover()

    def _build_action_popover(self):
        """Build a popover with clickable action buttons."""
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
        """Build a popover with clickable report buttons."""
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
            rep_id = rep['id']
            report_name = rep.get('report_name', '')
            btn.connect('clicked', lambda b, rn=report_name, rid=rep_id:
                        self._run_report(rn, rid))
            box.append(btn)

        popover = Gtk.Popover()
        popover.set_child(box)
        self.btn_print.set_popover(popover)

    def _on_form_button_clicked(self, name, btn_type, btn_ctx=None):
        """Handle clicks on buttons defined in the XML arch."""
        if not self.res_id and btn_type == 'object':
            return

        # If editing, save first
        if self.editing:
            if not self.save_data():
                return

        print(f"DEBUG: Executing button {name} of type {btn_type}")
        
        try:
            from core.session import session
            ctx = session.client.context.copy()
            if btn_ctx:
                ctx.update(btn_ctx)
            
            # Common context for actions
            ctx.update({
                'active_id': self.res_id,
                'active_ids': [self.res_id] if self.res_id else [],
                'active_model': self.model_name,
            })

            if btn_type == 'object':
                # Call method on current record
                res = session.client.call_kw(
                    self.model_name, name, [[self.res_id]] if self.res_id else [],
                    {'context': ctx}
                )
                if isinstance(res, dict) and res.get('type'):
                    self._handle_action(res, ctx)
                
                self.load_data()

            elif btn_type == 'action':
                # Resolve XML ID to integer ID via ir.model.data search
                action_id = name
                if isinstance(action_id, str) and ('.' in action_id or not action_id.isdigit()):
                    try:
                        if '.' in action_id:
                            mod, xml_name = action_id.split('.', 1)
                            res_data = session.client.call_kw(
                                'ir.model.data', 'search_read',
                                [[('module', '=', mod), ('name', '=', xml_name)]],
                                {'fields': ['res_id'], 'limit': 1}
                            )
                            if res_data:
                                action_id = res_data[0]['res_id']
                    except Exception as e:
                        print(f"DEBUG: XMLID resolution failed for {name}: {e}")
                
                if isinstance(action_id, str) and action_id.isdigit():
                    action_id = int(action_id)

                if isinstance(action_id, int):
                    # 1. Load basic action info to find the type
                    action_data = session.client.call_kw(
                        'ir.actions.actions', 'read', [[action_id]], {'context': ctx}
                    )
                    if action_data:
                        act = action_data[0]
                        act_type = act.get('type')
                        
                        # 2. If it's a specialized action, read again from the correct model
                        if act_type == 'ir.actions.report':
                            report_data = session.client.call_kw(
                                'ir.actions.report', 'read', [[action_id]], {'context': ctx}
                            )
                            if report_data:
                                act = report_data[0]
                        elif act_type == 'ir.actions.act_window':
                            window_data = session.client.call_kw(
                                'ir.actions.act_window', 'read', [[action_id]], {'context': ctx}
                            )
                            if window_data:
                                act = window_data[0]
                        
                        self._handle_action(act, ctx)
                else:
                    print(f"Error: Could not resolve action {name} to an integer ID")
                
        except Exception as e:
            print(f"Error executing button {name}: {e}")

    def _handle_action(self, action, context):
        """Execute an Odoo action (report, window, server, etc)."""
        act_type = action.get('type')
        if not act_type:
            return

        print(f"DEBUG: Handling action type {act_type}. Keys available: {list(action.keys())}")
        
        from core.session import session
        if act_type == 'ir.actions.report':
            # Support both report_name and report_file as fallback
            report_name = action.get('report_name') or action.get('report_file')
            if report_name:
                self._run_report(report_name, action.get('id'))
            else:
                print(f"Error: Report action missing report_name/file: {action}")
        
        elif act_type == 'ir.actions.server':
            # Execute server action
            res = session.client.call_kw(
                'ir.actions.server', 'run', [[action['id']]],
                {'context': context}
            )
            # If server action returns another action, handle it recursively
            if isinstance(res, dict) and res.get('type'):
                self._handle_action(res, context)
            self.load_data()

        elif act_type == 'ir.actions.act_window':
            res_model = action.get('res_model')
            res_id = action.get('res_id')
            target = action.get('target')
            
            print(f"DEBUG: Opening window action: {action.get('name')} (Model: {res_model}, Target: {target})")
            
            if target == 'new':
                # Open in a modal dialog (Wizard)
                self._open_action_dialog(action, context)
            else:
                # TODO: Open in a new tab
                pass

    def _open_action_dialog(self, action, context):
        """Open a form view in a modal dialog (for Wizards)."""
        dialog = ActionDialog(self.get_root(), action, context)
        dialog.present()

    def _run_server_action(self, action_id):
        """Execute a server action on the current record."""
        if not self.res_id:
            return
        try:
            from core.session import session
            ctx = dict(session.client.context or {})
            ctx['active_id'] = self.res_id
            ctx['active_ids'] = [self.res_id]
            ctx['active_model'] = self.model_name
            result = session.client.call_kw(
                'ir.actions.server', 'run', [[action_id]],
                {'context': ctx})
            print(f"DEBUG: Server action {action_id} → {result}")
            self.load_data()
        except Exception as e:
            print(f"Erreur action serveur {action_id}: {e}")

    def _run_report(self, report_name, report_id):
        """Simple download and open with system default viewer."""
        if not self.res_id:
            return
        
        try:
            import tempfile
            import os
            from core.session import session
            
            url = f"{session.client.url}/report/pdf/{report_name}/{self.res_id}"
            print(f"DEBUG: Downloading report: {url}")
            
            response = session.client.session.get(url, timeout=30)
            if response.status_code == 200:
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                    f.write(response.content)
                    pdf_path = f.name
                
                print(f"DEBUG: Opening report with default viewer: {pdf_path}")
                os.startfile(pdf_path)
            else:
                print(f"Erreur téléchargement: {response.status_code}")
                
        except Exception as e:
            print(f"Erreur impression: {e}")

class ActionDialog(Gtk.Window):
    """A modal dialog to display a form (Odoo Wizard)."""
    def __init__(self, parent, action, context):
        super().__init__(title=action.get('name', 'Odoo'), transient_for=parent, modal=True)
        self.set_default_size(800, 600)
        
        # Add a header bar
        hb = Gtk.HeaderBar()
        self.set_titlebar(hb)
        
        btn_close = Gtk.Button(label="Annuler")
        btn_close.connect("clicked", lambda b: self.destroy())
        hb.pack_start(btn_close)

        # Create the form view for the wizard
        from .form import FormView
        v_id = action.get('view_id', [False])[0] if isinstance(action.get('view_id'), list) else action.get('view_id')
        self.form_view = FormView(
            model_name=action.get('res_model'),
            view_id=v_id,
            res_id=action.get('res_id')
        )
        # Pass the context (crucial for defaults)
        self.form_view.current_record_data = {'context': context}
        
        self.set_child(self.form_view)

