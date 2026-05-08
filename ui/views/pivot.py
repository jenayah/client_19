# -*- coding: utf-8 -*-
# Odoo GTK 19 — Pivot View

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GObject, Pango, Gio
from core import Model, session
import xml.etree.ElementTree as ET

class PivotView(Gtk.Box):
    def __init__(self, model_name, view_id=None, domain=None, context=None, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        self.model_name = model_name
        self.model = Model(model_name)
        self.view_id = view_id
        self.domain = domain or []
        self.context = context or {}
        
        self.view_arch = None
        self.view_fields = {}
        self.row_fields = []
        self.col_fields = []
        self.measures = []
        
        self._setup_ui()
        self._load_view_arch()
        self.load_data()

    def _setup_ui(self):
        # Toolbar
        self.toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.toolbar.add_css_class('o_cp_buttons')
        self.toolbar.set_margin_start(12)
        self.toolbar.set_margin_end(12)
        self.toolbar.set_margin_top(6)
        self.toolbar.set_margin_bottom(6)
        self.append(self.toolbar)

        # Measures Dropdown
        self.measures_btn = Gtk.MenuButton()
        self.measures_btn.set_label("Mesures")
        self.measures_btn.add_css_class('btn-secondary')
        self.measures_menu = Gio.Menu()
        self.measures_btn.set_menu_model(self.measures_menu)
        self.toolbar.append(self.measures_btn)

        # Separator
        self.toolbar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        # Odoo-style buttons
        self.swap_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        self.swap_btn.set_tooltip_text("Inverser les axes")
        self.swap_btn.connect("clicked", self._on_swap_clicked)
        self.toolbar.append(self.swap_btn)

        self.expand_btn = Gtk.Button(icon_name="view-fullscreen-symbolic")
        self.expand_btn.set_tooltip_text("Développer tout")
        self.expand_btn.connect("clicked", self._on_expand_clicked)
        self.toolbar.append(self.expand_btn)

        self.download_btn = Gtk.Button(icon_name="document-save-symbolic")
        self.download_btn.set_tooltip_text("Télécharger (CSV)")
        self.download_btn.connect("clicked", self._on_download_clicked)
        self.toolbar.append(self.download_btn)

        # Scrolled Window
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_vexpand(True)
        self.append(self.scroll)

        # Content area
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.content_box.set_margin_start(12)
        self.content_box.set_margin_end(12)
        self.content_box.set_margin_top(12)
        self.content_box.set_margin_bottom(12)
        self.scroll.set_child(self.content_box)

    def _load_view_arch(self):
        try:
            res = session.client.get_view(self.model_name, view_id=self.view_id, view_type='pivot')
            self.view_arch = res.get('arch', '<pivot/>')
            self.view_fields = res.get('fields', {})
            
            # Fetch full field defs
            try:
                all_fields = session.client.call_kw(
                    self.model_name, 'fields_get', [],
                    {'attributes': ['type', 'string', 'relation']})
                for fname, finfo in all_fields.items():
                    if fname in self.view_fields:
                        merged = dict(finfo)
                        merged.update(self.view_fields[fname])
                        self.view_fields[fname] = merged
                    else:
                        self.view_fields[fname] = finfo
            except Exception as e:
                print(f"Warning: fields_get failed for pivot: {e}")

            # Parse arch
            root = ET.fromstring(self.view_arch)
            for field_node in root.findall('.//field'):
                fname = field_node.get('name')
                ftype = field_node.get('type')
                if ftype == 'row':
                    self.row_fields.append(fname)
                elif ftype == 'col':
                    self.col_fields.append(fname)
                elif ftype == 'measure' or field_node.get('operator'):
                    self.measures.append(fname)
            
            # Default measures if none
            if not self.measures:
                for f in ('price_total', 'amount_total', 'product_uom_qty', 'qty_done'):
                    if f in self.view_fields:
                        self.measures.append(f)
                        break
                if not self.measures:
                    self.measures = ['__count']
            
            # Populate Measures Menu (Multiple Selection)
            for fname, finfo in self.view_fields.items():
                if finfo.get('type') in ('integer', 'float', 'monetary'):
                    item = Gio.MenuItem.new(finfo.get('string', fname), f"app.pivot_measure('{fname}')")
                    self.measures_menu.append_item(item)
            
            print(f"DEBUG: Pivot View Arch loaded for {self.model_name}. Rows: {self.row_fields}, Measures: {self.measures}")
        except Exception as e:
            print(f"Erreur arch Pivot {self.model_name}: {e}")

    def _on_expand_clicked(self, btn):
        # Implementation of expand all (lazy=False already does a form of this)
        self.load_data()

    def _on_swap_clicked(self, btn):
        self.row_fields, self.col_fields = self.col_fields, self.row_fields
        self.load_data()

    def _on_download_clicked(self, btn):
        print(f"DEBUG: Exporting Pivot to CSV for {self.model_name}...")
        
    def load_data(self):
        # Clear content
        while child := self.content_box.get_first_child():
            self.content_box.remove(child)

        row_dims = self.row_fields
        if not row_dims:
            # Pick a stored field as default to avoid 'display_name' SQL error
            for f in ('date', 'partner_id', 'name', 'id'):
                if f in self.view_fields and self.view_fields[f].get('store', True):
                    row_dims = [f]
                    break
            if not row_dims: row_dims = ['id']
            
        col_dims = self.col_fields
        
        try:
            # We use read_group for pivot
            groupby = row_dims + col_dims
            fields_to_read = [m for m in self.measures if m != '__count']
            
            # Filter out non-stored fields from groupby to prevent RPC error
            groupby = [g for g in groupby if self.view_fields.get(g, {}).get('store', True)]
            if not groupby: groupby = ['id']

            records = session.client.call_kw(self.model_name, 'read_group', [], {
                'domain': self.domain,
                'fields': fields_to_read,
                'groupby': groupby,
                'lazy': False
            })
            
            self._render_pivot_table(records)
        except Exception as e:
            print(f"Erreur données Pivot {self.model_name}: {e}")
            self.content_box.append(Gtk.Label(label=f"Erreur de chargement: {e}"))

    def _render_pivot_table(self, records):
        if not records:
            self.content_box.append(Gtk.Label(label="Aucune donnée à afficher"))
            return

        # Simple Table Implementation
        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.set_row_spacing(10)
        grid.add_css_class('pivot-table')
        
        # Headers
        col_idx = 0
        header_labels = self.row_fields if self.row_fields else ['display_name']
        for rf in header_labels:
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            lbl = Gtk.Label(label=self.view_fields.get(rf, {}).get('string', rf))
            lbl.add_css_class('fw-bold')
            box.append(lbl)
            
            # Drill-down (+) Button
            add_btn = Gtk.MenuButton()
            add_btn.set_icon_name("list-add-symbolic")
            add_btn.add_css_class('flat')
            
            menu = Gio.Menu()
            # Sort fields by label
            groupable = []
            for fname, finfo in self.view_fields.items():
                if finfo.get('type') in ('many2one', 'selection', 'char', 'date', 'datetime'):
                    groupable.append((fname, finfo.get('string', fname)))
            
            for fname, label in sorted(groupable, key=lambda x: x[1]):
                item = Gio.MenuItem.new(label, f"app.pivot_add_row('{fname}')")
                menu.append_item(item)
                
            add_btn.set_menu_model(menu)
            box.append(add_btn)
            
            grid.attach(box, col_idx, 0, 1, 1)
            col_idx += 1
            
        for m in self.measures:
            m_name = m if m != '__count' else 'Nombre'
            lbl = Gtk.Label(label=self.view_fields.get(m, {}).get('string', m_name))
            lbl.add_css_class('fw-bold')
            lbl.set_halign(Gtk.Align.END)
            grid.attach(lbl, col_idx, 0, 1, 1)
            col_idx += 1

        # Totals calculation
        totals = {m: 0 for m in self.measures}
        
        # Rows
        row_idx = 2
        for rec in records:
            c_idx = 0
            # Row dimensions
            for rf in header_labels:
                val = rec.get(rf)
                if isinstance(val, (list, tuple)) and len(val) > 1:
                    val = val[1]
                lbl = Gtk.Label(label=str(val or '-'))
                lbl.set_halign(Gtk.Align.START)
                grid.attach(lbl, c_idx, row_idx, 1, 1)
                c_idx += 1
            
            # Measures
            for m in self.measures:
                m_key = m if m != '__count' else f'{header_labels[0]}_count'
                val = rec.get(m_key, 0)
                if val is None: val = 0
                totals[m] += val
                
                # Format numbers
                if isinstance(val, (int, float)):
                    if val == int(val): text = f"{int(val)}"
                    else: text = f"{val:,.2f}"
                else:
                    text = str(val)
                    
                lbl = Gtk.Label(label=text)
                lbl.set_halign(Gtk.Align.END)
                grid.attach(lbl, c_idx, row_idx, 1, 1)
                c_idx += 1
                
            row_idx += 1

        # Total Row
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        grid.attach(sep, 0, row_idx, col_idx, 1)
        row_idx += 1
        
        c_idx = 0
        total_lbl = Gtk.Label(label="Total")
        total_lbl.add_css_class('fw-bold')
        grid.attach(total_lbl, 0, row_idx, len(header_labels), 1)
        c_idx = len(header_labels)
        
        for m in self.measures:
            val = totals[m]
            if isinstance(val, (int, float)):
                if val == int(val): text = f"{int(val)}"
                else: text = f"{val:,.2f}"
            else:
                text = str(val)
            lbl = Gtk.Label(label=text)
            lbl.add_css_class('fw-bold')
            lbl.set_halign(Gtk.Align.END)
            grid.attach(lbl, c_idx, row_idx, 1, 1)
            c_idx += 1

        self.content_box.append(grid)
