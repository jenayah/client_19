# -*- coding: utf-8 -*-
# Odoo GTK 19 — One2many Widget (Inline Editable)
# Full inline editing with add/delete line support

from gi.repository import Gtk, Gio, GObject, Pango
from .base import WidgetBase
import xml.etree.ElementTree as ET


class _O2mRecord(GObject.Object):
    """Wrapper for a single record in the one2many list."""
    def __init__(self, data, is_new=False):
        super().__init__()
        self.data = dict(data) if data else {}
        self.is_new = is_new          # True if created locally (not yet on server)
        self.dirty_fields = set()     # Fields modified by user
        self.deleted = False          # Marked for deletion


class One2manyWidget(WidgetBase):
    """one2many field → Editable inline list with add/delete/edit."""

    def _build_widget(self):
        self.widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.widget.set_hexpand(True)
        self.widget.set_vexpand(True)

        self._columns_meta = {}       # fname → {string, type, widget, selection, relation, ...}
        self._column_fnames = []      # Ordered list of visible field names
        self._control_ops = []        # List of {type, string, context, name, ...}
        self._records = []            # List of _O2mRecord
        self._deleted_ids = []        # IDs marked for server deletion
        self._relation = self.field_info.get('relation', '')
        self._editable = False        # From tree attribute 'editable'

        # Will be built after nested views are set
        self.store = Gio.ListStore.new(_O2mRecord)
        self.column_view = None
        self._built = False

    def set_nested_views(self, views):
        """Parse columns from the tree/list view architecture."""
        arch = views.get('tree') or views.get('list')
        if not arch:
            # Fallback: try to load from server
            if self._relation:
                try:
                    from core.session import session
                    res = session.client.get_view(self._relation, view_type='list')
                    arch = res.get('arch', '')
                except Exception as e:
                    print(f"Warning: Could not load tree view for {self._relation}: {e}")
            if not arch:
                return

        try:
            root = ET.fromstring(arch)
            self._editable = root.attrib.get('editable') in ('top', 'bottom')
            self._parse_tree_arch(root)
            self._build_ui()
        except Exception as e:
            print(f"Error parsing nested tree view for {self._relation}: {e}")
            import traceback
            traceback.print_exc()

    def _parse_tree_arch(self, root):
        """Extract column definitions from tree/list XML."""
        self._columns_meta = {}
        self._column_fnames = []
        self._control_ops = []

        # Get field defs from server for the relation model
        relation_fields = {}
        if self._relation:
            try:
                from core.session import session
                relation_fields = session.client.call_kw(
                    self._relation, 'fields_get', [],
                    {'attributes': ['type', 'string', 'relation', 'selection',
                                    'digits', 'readonly', 'required']})
            except Exception as e:
                print(f"Warning: fields_get failed for {self._relation}: {e}")

        for child in root:
            if child.tag == 'field':
                attrs = dict(child.attrib)
                fname = attrs.get('name', '')
                if not fname:
                    continue

                # Skip invisible columns
                invis = attrs.get('column_invisible', attrs.get('invisible', ''))
                if invis in ('1', 'True', 'true'):
                    continue
                if attrs.get('optional') == 'hide':
                    continue

                # Merge with server field info
                f_info = dict(relation_fields.get(fname, {}))
                f_info['string'] = attrs.get('string', f_info.get('string', fname))
                f_info['widget'] = attrs.get('widget', '')
                f_info['readonly'] = attrs.get('readonly', f_info.get('readonly', False))
                f_info['required'] = attrs.get('required', f_info.get('required', False))

                self._columns_meta[fname] = f_info
                self._column_fnames.append(fname)
            
            elif child.tag == 'control':
                # Parse custom buttons (Add a line, Add a section, etc.)
                for op in child:
                    if op.tag in ('create', 'button'):
                        self._control_ops.append({
                            'tag': op.tag,
                            'string': op.attrib.get('string', ''),
                            'context': op.attrib.get('context', ''),
                            'name': op.attrib.get('name', ''),
                            'type': op.attrib.get('type', '')
                        })

        # Default control if none provided
        if not self._control_ops:
            self._control_ops.append({
                'tag': 'create',
                'string': 'Ajouter une ligne',
                'context': '{}'
            })

    def _build_ui(self):
        """Build the ColumnView and footer buttons."""
        if self._built:
            # Clear previous UI
            while child := self.widget.get_first_child():
                self.widget.remove(child)

        self._built = True
        selection = Gtk.NoSelection.new(self.store)
        self.column_view = Gtk.ColumnView.new(selection)
        self.column_view.add_css_class('data-table')
        self.column_view.set_show_column_separators(True)
        self.column_view.set_show_row_separators(True)

        # Build columns
        for fname in self._column_fnames:
            f_info = self._columns_meta[fname]
            f_type = f_info.get('type', 'char')
            f_label = f_info.get('string', fname)
            col_readonly = f_info.get('readonly')
            # Consider True or '1' as readonly
            is_readonly = col_readonly is True or col_readonly in ('1', 'True', 'true')

            factory = Gtk.SignalListItemFactory()

            if f_type in ('float', 'monetary', 'integer') and not is_readonly:
                # Editable numeric cell
                def on_setup_num(f, item, _fn=fname, _ft=f_type):
                    entry = Gtk.Entry()
                    entry.set_alignment(1)
                    entry.set_max_width_chars(12)
                    entry.set_hexpand(True)
                    entry.add_css_class('flat')
                    item.set_child(entry)

                def on_bind_num(f, item, _fn=fname, _ft=f_type):
                    entry = item.get_child()
                    rec = item.get_item()
                    val = rec.data.get(_fn)
                    if _ft in ('float', 'monetary'):
                        entry.set_text(f'{float(val):,.2f}' if val else '0.00')
                    else:
                        entry.set_text(str(int(val)) if val else '0')
                    # Disconnect old handler
                    if hasattr(entry, '_sig_id') and entry._sig_id:
                        entry.disconnect(entry._sig_id)
                    entry._sig_id = entry.connect('changed', self._on_cell_changed, rec, _fn, _ft)
                    entry.set_editable(not self._readonly)

                factory.connect('setup', on_setup_num)
                factory.connect('bind', on_bind_num)

            elif f_type in ('char', 'text') and not is_readonly:
                # Editable text cell
                def on_setup_char(f, item, _fn=fname):
                    entry = Gtk.Entry()
                    entry.set_hexpand(True)
                    entry.add_css_class('flat')
                    entry.set_max_width_chars(30)
                    item.set_child(entry)

                def on_bind_char(f, item, _fn=fname):
                    entry = item.get_child()
                    rec = item.get_item()
                    val = rec.data.get(_fn, '')
                    entry.set_text(str(val) if val and val is not False else '')
                    if hasattr(entry, '_sig_id') and entry._sig_id:
                        entry.disconnect(entry._sig_id)
                    entry._sig_id = entry.connect('changed', self._on_cell_changed, rec, _fn, 'char')
                    entry.set_editable(not self._readonly)

                factory.connect('setup', on_setup_char)
                factory.connect('bind', on_bind_char)

            elif f_type == 'many2one':
                # Many2one: Editable search button + text entry
                def on_setup_m2o(f, item, _fn=fname, _rel=f_info.get('relation')):
                    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
                    box.set_hexpand(True)
                    
                    entry = Gtk.Entry()
                    entry.set_hexpand(True)
                    entry.add_css_class('flat')
                    box.append(entry)

                    btn = Gtk.Button(icon_name='system-search-symbolic')
                    btn.add_css_class('flat')
                    btn.set_visible(not self._readonly)
                    box.append(btn)
                    
                    item.set_child(box)

                def on_bind_m2o(f, item, _fn=fname, _rel=f_info.get('relation')):
                    box = item.get_child()
                    entry = box.get_first_child()
                    btn = entry.get_next_sibling()
                    rec = item.get_item()
                    val = rec.data.get(_fn)
                    
                    if isinstance(val, (list, tuple)) and len(val) > 1:
                        entry.set_text(str(val[1]))
                    elif val and val is not False:
                        entry.set_text(str(val))
                    else:
                        entry.set_text('')
                    
                    entry.set_editable(not self._readonly)
                    btn.set_visible(not self._readonly)
                    
                    if hasattr(btn, '_sig_id') and btn._sig_id:
                        btn.disconnect(btn._sig_id)
                    btn._sig_id = btn.connect('clicked', self._on_m2o_search_clicked, rec, _fn, _rel, item)
                    
                    if hasattr(entry, '_sig_id') and entry._sig_id:
                        entry.disconnect(entry._sig_id)
                    entry._sig_id = entry.connect('changed', self._on_cell_changed, rec, _fn, 'char')

                factory.connect('setup', on_setup_m2o)
                factory.connect('bind', on_bind_m2o)

            elif f_type == 'many2many':
                # Many2many tags (e.g. taxes)
                w_attr = f_info.get('widget', '')
                def on_setup_m2m(f, item, _fn=fname):
                    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
                    box.set_margin_start(4)
                    box.set_margin_end(4)
                    item.set_child(box)

                def on_bind_m2m(f, item, _fn=fname):
                    box = item.get_child()
                    while c := box.get_first_child():
                        box.remove(c)
                    rec = item.get_item()
                    val = rec.data.get(_fn, [])
                    if isinstance(val, list):
                        for v in val[:5]:  # Show max 5 tags
                            if isinstance(v, (list, tuple)) and len(v) > 1:
                                tag_label = str(v[1])
                            elif isinstance(v, dict):
                                tag_label = v.get('display_name', str(v.get('id', '')))
                            else:
                                tag_label = str(v) if v else ''
                            if tag_label:
                                badge = Gtk.Label(label=tag_label)
                                badge.add_css_class('badge')
                                badge.add_css_class('bg-info')
                                box.append(badge)

                factory.connect('setup', on_setup_m2m)
                factory.connect('bind', on_bind_m2m)

            elif f_type == 'selection':
                sel_list = f_info.get('selection', [])
                if not is_readonly and sel_list:
                    # Editable dropdown
                    def on_setup_sel(f, item, _fn=fname, _sl=sel_list):
                        dd = Gtk.DropDown.new_from_strings([str(s[1]) for s in _sl])
                        dd.add_css_class('flat')
                        item.set_child(dd)

                    def on_bind_sel(f, item, _fn=fname, _sl=sel_list):
                        dd = item.get_child()
                        rec = item.get_item()
                        val = rec.data.get(_fn)
                        # Find index
                        idx = 0
                        for i, (sv, sl) in enumerate(_sl):
                            if sv == val:
                                idx = i
                                break
                        dd.set_selected(idx)

                    factory.connect('setup', on_setup_sel)
                    factory.connect('bind', on_bind_sel)
                else:
                    # Readonly selection label
                    def on_setup_sel_ro(f, item, _fn=fname, _sl=sel_list):
                        label = Gtk.Label(xalign=0)
                        label.set_margin_start(6)
                        item.set_child(label)

                    def on_bind_sel_ro(f, item, _fn=fname, _sl=sel_list):
                        label = item.get_child()
                        rec = item.get_item()
                        val = rec.data.get(_fn)
                        text = str(val) if val else ''
                        for sv, sl in _sl:
                            if sv == val:
                                text = str(sl)
                                break
                        label.set_text(text)

                    factory.connect('setup', on_setup_sel_ro)
                    factory.connect('bind', on_bind_sel_ro)
            else:
                # Default: readonly label
                def on_setup_def(f, item, _fn=fname, _ft=f_type):
                    label = Gtk.Label(xalign=0 if _ft not in ('float', 'monetary', 'integer') else 1)
                    label.set_margin_start(6)
                    label.set_margin_end(6)
                    label.set_margin_top(4)
                    label.set_margin_bottom(4)
                    label.set_ellipsize(Pango.EllipsizeMode.END)
                    item.set_child(label)

                def on_bind_def(f, item, _fn=fname, _ft=f_type):
                    label = item.get_child()
                    rec = item.get_item()
                    val = rec.data.get(_fn)
                    if _ft in ('float', 'monetary'):
                        label.set_text(f'{float(val):,.2f}' if val else '0.00')
                    elif _ft == 'integer':
                        label.set_text(str(int(val)) if val else '0')
                    elif _ft == 'boolean':
                        label.set_text('✓' if val else '✗')
                    else:
                        label.set_text(WidgetBase.format_value(val))

                factory.connect('setup', on_setup_def)
                factory.connect('bind', on_bind_def)

            col = Gtk.ColumnViewColumn.new(f_label, factory)
            col.set_resizable(True)
            # Article/Product column should always expand
            if f_type in ('char', 'text', 'html', 'many2one') or fname in ('name', 'display_name', 'product_id'):
                col.set_expand(True)
                col.set_fixed_width(200) # Minimum width for articles
            self.column_view.append_column(col)

        # ── Delete button column ──
        del_factory = Gtk.SignalListItemFactory()
        def on_setup_del(f, item):
            btn = Gtk.Button(icon_name='edit-delete-symbolic')
            btn.add_css_class('flat')
            btn.add_css_class('destructive-action')
            btn.set_tooltip_text('Supprimer la ligne')
            item.set_child(btn)

        def on_bind_del(f, item):
            btn = item.get_child()
            rec = item.get_item()
            if hasattr(btn, '_sig_id') and btn._sig_id:
                btn.disconnect(btn._sig_id)
            btn._sig_id = btn.connect('clicked', self._on_delete_line, rec)
            btn.set_visible(not self._readonly)

        del_factory.connect('setup', on_setup_del)
        del_factory.connect('bind', on_bind_del)
        del_col = Gtk.ColumnViewColumn.new('', del_factory)
        del_col.set_fixed_width(40)
        del_col.set_resizable(False)
        self.column_view.append_column(del_col)

        # ── Scroll container ──
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(150)
        scroll.set_max_content_height(400)
        scroll.set_propagate_natural_height(True)
        scroll.set_vexpand(True)
        scroll.set_child(self.column_view)
        self.widget.append(scroll)

        # ── Footer: Dynamic buttons from <control> ──
        if self._control_ops:
            footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
            footer.set_margin_start(8)
            footer.set_margin_top(4)
            footer.set_margin_bottom(4)

            for op in self._control_ops:
                btn = Gtk.Button(label=op['string'])
                btn.add_css_class('flat')
                btn.add_css_class('link')
                
                if op['tag'] == 'create':
                    btn.connect('clicked', self._on_control_create, op['context'])
                else:
                    # Generic button (e.g. Catalog)
                    btn.connect('clicked', self._on_control_button, op)
                
                footer.append(btn)
                # Store reference to disable in readonly
                if not hasattr(self, '_footer_btns'): self._footer_btns = []
                self._footer_btns.append(btn)

            self.widget.append(footer)

    # ══════════════════════════════════════════════════════════════
    #   CELL EDITING
    # ══════════════════════════════════════════════════════════════
    def _on_cell_changed(self, entry, rec, fname, ftype):
        """Called when a cell value is changed by the user."""
        if self._readonly: return
        text = entry.get_text().strip()
        try:
            if ftype in ('float', 'monetary'):
                val = float(text.replace(',', '').replace(' ', '')) if text else 0.0
            elif ftype == 'integer':
                val = int(text.replace(',', '').replace(' ', '')) if text else 0
            elif ftype == 'many2one':
                # PROTECT ID: if we have [id, name], don't overwrite with 'name' string
                current = rec.data.get(fname)
                if isinstance(current, (list, tuple)) and len(current) > 1:
                    if text == str(current[1]):
                        val = current # Keep the list [id, name]
                    else:
                        # User typed something else, need to search ID by name
                        try:
                            rel_model = self._columns_meta[fname].get('relation')
                            search_res = session.client.call_kw(rel_model, 'name_search', [], {'name': text, 'operator': 'ilike', 'limit': 1})
                            if search_res:
                                val = search_res[0] # [id, name]
                            else:
                                val = text
                        except: val = text
                else:
                    val = text
            else:
                val = text
            
            if rec.data.get(fname) != val:
                rec.data[fname] = val
                rec.dirty_fields.add(fname)
                # Trigger onchange for quantity or price changes
                if fname in ('product_id', 'product_uom_qty', 'price_unit', 'quantity'):
                    self._trigger_onchange(rec, fname)
                    self._refresh_display()
        except ValueError:
            pass

    # ══════════════════════════════════════════════════════════════
    #   LINE OPERATIONS
    # ══════════════════════════════════════════════════════════════
    def _on_control_create(self, btn, context_str):
        """Add a new record based on the <create> tag context."""
        from core.expression import safe_eval
        # Parse context to find default values (e.g. default_display_type)
        ctx = {}
        if context_str:
            try:
                ctx = safe_eval(context_str, self.record)
            except:
                pass
        
        # Strictly only include fields that belong to the line model
        new_data = {}
        for fn in self._column_fnames:
            new_data[fn] = False
        
        # Apply defaults from context (ONLY if they are valid fields)
        for k, v in ctx.items():
            if k.startswith('default_'):
                field = k[8:]
                if field in self._column_fnames or field in self._columns_meta:
                    new_data[field] = v
        
        new_data['id'] = False
        rec = _O2mRecord(new_data, is_new=True)
        self._records.append(rec)
        self.store.append(rec)

    def _on_m2o_search_clicked(self, btn, rec, fname, relation, item):
        """Open a selection dialog for the Many2one field."""
        if not relation:
            return
            
        from ui.dialogs.selection import SelectionDialog
        dialog = SelectionDialog(self.widget.get_root(), relation, title=f"Sélectionner {fname}")
        
        def on_selected(dlg, res_id, display_name):
            # If we selected a template, we might need to find the product.product ID
            actual_fname = fname
            actual_res_id = res_id
            
            if relation == 'product.template' and fname == 'product_template_id':
                # Try to find the first variant (product.product) for this template
                try:
                    products = session.client.call_kw('product.product', 'search_read', [[['product_tmpl_id', '=', res_id]]], {'fields': ['id', 'display_name'], 'limit': 1})
                    if products:
                        actual_fname = 'product_id'
                        actual_res_id = products[0]['id']
                        display_name = products[0]['display_name']
                        # Update both if present
                        if 'product_id' in self._columns_meta:
                            rec.data['product_id'] = [actual_res_id, display_name]
                except: pass

            rec.data[actual_fname] = [actual_res_id, display_name]
            rec.dirty_fields.add(actual_fname)
            
            # Update the Entry text
            if item:
                box = item.get_child()
                if box:
                    entry = box.get_first_child()
                    if isinstance(entry, Gtk.Entry):
                        entry.set_text(str(display_name))
            
            self._trigger_onchange(rec, actual_fname)
            self._refresh_display()
            dlg.destroy()
            
        dialog.connect('record-selected', on_selected)
        dialog.present()

    def _trigger_onchange(self, rec, fname):
        """Call Odoo's onchange for the line, including parent context."""
        if not self._relation:
            return
            
        try:
            from core.session import session
            rec_id = rec.data.get('id')
            ids = [rec_id] if rec_id and not rec.is_new else []
            
            # 1. Prepare line values (PURE IDs for Many2one)
            values = {}
            for k, v in rec.data.items():
                if v is False or v is None: continue
                if k in self._columns_meta:
                    if isinstance(v, (list, tuple)) and len(v) > 0:
                        values[k] = v[0] # ID (int)
                    elif isinstance(v, str) and self._columns_meta[k].get('type') == 'many2one':
                        # Try to get ID from string if it looks like an ID
                        try: values[k] = int(v)
                        except: continue # Skip invalid M2O
                    else:
                        values[k] = v

            # 2. Trigger field validation
            if fname not in values:
                # Odoo crashes if trigger field is not in values
                values[fname] = v[0] if isinstance(v, (list, tuple)) else v
            
            trigger_fields = [fname]
            
            # Filter trigger_fields to only include real fields in self._columns_meta
            trigger_fields = [f for f in trigger_fields if f in self._columns_meta]
            if not trigger_fields: return
            
            onchange_spec = {fn: {} for fn in self._column_fnames}
            
            print(f"DEBUG: Triggering ONCHANGE on {self._relation} for field {fname}")
            print(f"DEBUG: Values sent: {values}")
            
            result = session.client.call_kw(
                self._relation, 'onchange', [ids, values, trigger_fields, onchange_spec],
                {'context': session.client.context})
            
            if result and 'value' in result:
                new_vals = result['value']
                print(f"DEBUG: Server returned values: {new_vals}")
                for k, v in new_vals.items():
                    if k in self._columns_meta:
                        if self._columns_meta[k].get('type') == 'many2one' and isinstance(v, int):
                            try:
                                rel_model = self._columns_meta[k].get('relation')
                                name_get = session.client.call_kw(rel_model, 'name_get', [[v]], {})
                                if name_get: v = name_get[0]
                            except: pass
                        rec.data[k] = v
                self._refresh_display()
            else:
                print(f"DEBUG: Server returned NO values for onchange")
        except Exception as e:
            print(f"Error triggering onchange on {self._relation}: {e}")
            import traceback
            traceback.print_exc()
            print(f"Error triggering onchange on {self._relation}: {e}")
            import traceback
            traceback.print_exc()

    def _refresh_display(self):
        """Force refresh of the ColumnView by re-triggering binding."""
        n = self.store.get_n_items()
        if n > 0:
            self.store.items_changed(0, n, n)

    def _on_control_button(self, btn, op):
        """Handle custom buttons in the control bar."""
        print(f"DEBUG: Control button clicked: {op['name']} ({op['type']})")
        # For now, just a placeholder for catalog etc.
        pass

    def _on_delete_line(self, btn, rec):
        """Remove a line from the list."""
        rec_id = rec.data.get('id')
        if rec_id and not rec.is_new:
            self._deleted_ids.append(rec_id)

        # Remove from store
        n = self.store.get_n_items()
        for i in range(n):
            if self.store.get_item(i) is rec:
                self.store.remove(i)
                break
        if rec in self._records:
            self._records.remove(rec)

    # ══════════════════════════════════════════════════════════════
    #   VALUE GET / SET
    # ══════════════════════════════════════════════════════════════
    def set_value(self, value):
        """Load records into the inline list."""
        self.store.remove_all()
        self._records = []
        self._deleted_ids = []

        if not value:
            return

        # If it's just a list of IDs, fetch full data
        if isinstance(value, list) and value and all(isinstance(v, int) for v in value):
            value = self._fetch_full_data(value)

        if not isinstance(value, list):
            return

        for item in value:
            if isinstance(item, dict):
                rec = _O2mRecord(item)
                self._records.append(rec)
                self.store.append(rec)
            elif isinstance(item, (list, tuple)) and len(item) >= 3:
                cmd = item[0]
                if cmd == 0:  # Create
                    rec = _O2mRecord(item[2], is_new=True)
                    self._records.append(rec)
                    self.store.append(rec)
                elif cmd == 1:  # Update
                    for r in self._records:
                        if r.data.get('id') == item[1]:
                            r.data.update(item[2])
                            break
                elif cmd == 4:  # Link
                    pass  # Would need to fetch

    def get_value(self):
        """Return Odoo write commands for the one2many field.
        
        Format: [(0, 0, vals), (1, id, vals), (2, id, 0)]
        """
        commands = []

        # Deletions
        for del_id in self._deleted_ids:
            commands.append((2, del_id, 0))

        # Creates and updates
        for rec in self._records:
            rec_id = rec.data.get('id')
            if rec.is_new:
                # Format values for Odoo: convert [id, name] -> id
                vals = {}
                for k, v in rec.data.items():
                    if k == 'id' or v is False or v is None: continue
                    vals[k] = v[0] if isinstance(v, (list, tuple)) and len(v) > 0 else v
                
                if vals:
                    commands.append((0, 0, vals))
            elif rec.dirty_fields:
                # Format changed values for Odoo
                vals = {}
                for fname in rec.dirty_fields:
                    v = rec.data.get(fname)
                    vals[fname] = v[0] if isinstance(v, (list, tuple)) and len(v) > 0 else v
                
                if vals and rec_id:
                    commands.append((1, rec_id, vals))
            # Unmodified existing records: no command needed (implicit keep)

        return commands if commands else False

    def _fetch_full_data(self, ids):
        """Fetch full record data for display."""
        if not self._relation or not ids:
            return []

        fields = list(self._columns_meta.keys()) if self._columns_meta else ['display_name']
        if 'id' not in fields:
            fields.append('id')

        try:
            from core.session import session
            return session.client.call_kw(self._relation, 'read', [ids],
                                          {'fields': fields,
                                           'context': session.client.context})
        except Exception as e:
            print(f"Error fetching O2M data for {self._relation}: {e}")
            return [{'id': i, 'display_name': f'#{i}'} for i in ids]

    def set_readonly(self, readonly):
        """Toggle readonly state for the entire widget."""
        self._readonly = readonly
        if hasattr(self, '_footer_btns'):
            for btn in self._footer_btns:
                btn.set_sensitive(not readonly)
        # Refresh display to update cell editability
        if self.store.get_n_items() > 0:
            items = [self.store.get_item(i) for i in range(self.store.get_n_items())]
            self.store.remove_all()
            for item in items:
                self.store.append(item)
