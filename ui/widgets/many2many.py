# -*- coding: utf-8 -*-
# Odoo GTK 19 — Many2many Widget
# Inspired by E:\odoo-client-19\widget\view\form_gtk\many2many.py

from gi.repository import Gtk, Gio, GObject
from .base import WidgetBase


class _M2mRecord(GObject.Object):
    def __init__(self, rid, name):
        super().__init__()
        self.rid = rid
        self.name = name


class Many2manyWidget(WidgetBase):
    """many2many field → List with Add/Remove buttons"""

    def _build_widget(self):
        self.widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.widget.set_hexpand(True)
        self.widget.set_vexpand(True)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.btn_add = Gtk.Button(icon_name='list-add-symbolic')
        self.btn_add.add_css_class('flat')
        self.btn_remove = Gtk.Button(icon_name='list-remove-symbolic')
        self.btn_remove.add_css_class('flat')
        toolbar.append(self.btn_add)
        toolbar.append(self.btn_remove)
        self.widget.append(toolbar)

        # List
        self.store = Gio.ListStore.new(_M2mRecord)
        self.selection_model = Gtk.SingleSelection.new(self.store)

        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self._on_setup)
        factory.connect('bind', self._on_bind)

        self.listview = Gtk.ListView.new(self.selection_model, factory)
        self.listview.set_vexpand(True)

        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(120)
        scroll.set_child(self.listview)
        self.widget.append(scroll)

        self._ids = []

    def _on_setup(self, factory, item):
        label = Gtk.Label(xalign=0)
        label.set_margin_start(8)
        label.set_margin_top(4)
        label.set_margin_bottom(4)
        item.set_child(label)

    def _on_bind(self, factory, item):
        rec = item.get_item()
        label = item.get_child()
        label.set_text(rec.name)

    def set_value(self, value):
        self.store.remove_all()
        self._ids = []
        if not value:
            return
        
        if isinstance(value, list):
            # Collect IDs that need name resolution
            ids_to_resolve = []
            resolved = []
            
            for v in value:
                if isinstance(v, (list, tuple)) and len(v) >= 2:
                    resolved.append((v[0], str(v[1])))
                elif isinstance(v, int):
                    ids_to_resolve.append(v)
            
            # Resolve names via name_get if we have plain IDs
            if ids_to_resolve:
                names = self._resolve_names(ids_to_resolve)
                resolved.extend(names)
            
            for rid, name in resolved:
                self._ids.append(rid)
                self.store.append(_M2mRecord(rid, name))

    def _resolve_names(self, ids):
        """Resolve record IDs to (id, name) pairs via read(['display_name'])."""
        relation = self.field_info.get('relation', '')
        if not relation or not ids:
            return [(i, f'#{i}') for i in ids]
        try:
            from core.session import session
            # Odoo 17+ uses display_name instead of name_get
            result = session.client.call_kw(
                relation, 'read', [ids], {'fields': ['display_name']})
            if isinstance(result, list):
                return [(r['id'], str(r.get('display_name', r.get('name', f"#{r['id']}")))) 
                        for r in result if isinstance(r, dict) and 'id' in r]
        except Exception as e:
            print(f"Warning: display_name resolution failed for {relation}: {e}")
        return [(i, f'#{i}') for i in ids]

    def get_value(self):
        return [(6, 0, self._ids)] if self._ids else [(5, 0, 0)]


class Many2manyTagsWidget(WidgetBase):
    """widget="many2many_tags" → Horizontal flow of badge labels"""

    def _build_widget(self):
        self.widget = Gtk.FlowBox()
        self.widget.set_hexpand(True)
        self.widget.set_selection_mode(Gtk.SelectionMode.NONE)
        self.widget.set_max_children_per_line(20)
        self.widget.set_min_children_per_line(1)
        self._ids = []

    def set_value(self, value):
        # Clear existing
        while child := self.widget.get_first_child():
            self.widget.remove(child)
        
        self._ids = []
        if not value:
            return
        
        if isinstance(value, list):
            # Collect IDs that need name resolution
            ids_to_resolve = []
            resolved = []
            
            for v in value:
                if isinstance(v, (list, tuple)) and len(v) >= 2:
                    resolved.append((v[0], str(v[1])))
                elif isinstance(v, int):
                    ids_to_resolve.append(v)
            
            # Resolve names via name_get if we have plain IDs
            if ids_to_resolve:
                names = self._resolve_names(ids_to_resolve)
                resolved.extend(names)
            
            for rid, name in resolved:
                self._ids.append(rid)
                # Build tag: badge with name + close button
                tag_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
                tag_box.add_css_class('badge')
                tag_box.set_margin_start(2)
                tag_box.set_margin_end(2)
                tag_box.set_margin_top(2)
                tag_box.set_margin_bottom(2)
                
                lbl = Gtk.Label(label=name)
                tag_box.append(lbl)
                
                close_btn = Gtk.Button(icon_name='window-close-symbolic')
                close_btn.add_css_class('flat')
                close_btn.add_css_class('circular')
                close_btn.set_valign(Gtk.Align.CENTER)
                tag_box.append(close_btn)
                
                self.widget.append(tag_box)

    def _resolve_names(self, ids):
        """Resolve record IDs to (id, name) pairs via read(['display_name'])."""
        relation = self.field_info.get('relation', '')
        if not relation or not ids:
            return [(i, f'#{i}') for i in ids]
        try:
            from core.session import session
            # Odoo 17+ uses display_name instead of name_get
            result = session.client.call_kw(
                relation, 'read', [ids], {'fields': ['display_name']})
            if isinstance(result, list):
                return [(r['id'], str(r.get('display_name', r.get('name', f"#{r['id']}")))) 
                        for r in result if isinstance(r, dict) and 'id' in r]
        except Exception as e:
            print(f"Warning: display_name resolution failed for {relation}: {e}")
        return [(i, f'#{i}') for i in ids]

    def get_value(self):
        return [(6, 0, self._ids)] if self._ids else [(5, 0, 0)]
