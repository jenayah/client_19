from gi.repository import Gtk, Adw, Gio
from .base import BaseWidget
from ..core import Model

class Many2oneWidget(BaseWidget):
    def create_widget(self):
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Rechercher...")
        
        # In a real implementation, we would add a search button/popover
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.append(self.entry)
        
        search_btn = Gtk.Button(icon_name="system-search-symbolic")
        search_btn.connect("clicked", self._on_search_clicked)
        box.append(search_btn)
        
        return box

    def _on_search_clicked(self, btn):
        print(f"Recherche pour Many2one: {self.attrs.get('relation')}")
        # TODO: Show search dialog

    def set_value(self, value):
        # value is usually [id, name]
        if isinstance(value, (list, tuple)) and len(value) > 1:
            self.entry.set_text(str(value[1]))
        else:
            self.entry.set_text(str(value))

class One2manyWidget(BaseWidget):
    def create_widget(self):
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_min_content_height(200)
        self.scroll.add_css_class("card")
        
        # We'll use a simplified list for now
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.scroll.set_child(self.list_box)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.append(self.scroll)
        
        add_btn = Gtk.Button(label="Ajouter une ligne", icon_name="list-add-symbolic")
        add_btn.add_css_class("flat")
        box.append(add_btn)
        
        return box

    def set_value(self, values):
        # values is a list of IDs or dicts
        while child := self.list_box.get_first_child():
            self.list_box.remove(child)
            
        if not values:
            return
            
        for val in values:
            row = Adw.ActionRow(title=str(val))
            self.list_box.append(row)
