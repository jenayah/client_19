from gi.repository import Gtk, Adw, Gio

class SearchView(Gtk.Box):
    def __init__(self, on_search):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.on_search = on_search
        self.set_margin_top(6)
        self.set_margin_bottom(6)
        self.set_margin_start(6)
        self.set_margin_end(6)
        
        # Search Entry
        self.entry = Gtk.SearchEntry()
        self.entry.set_hexpand(True)
        self.entry.connect("activate", self._on_activate)
        self.entry.connect("search-changed", self._on_search_changed)
        self.append(self.entry)
        
        # Filter Button (Placeholder)
        filter_btn = Gtk.Button()
        filter_btn.set_icon_name("view-filter-symbolic")
        filter_btn.set_tooltip_text("Filtres")
        self.append(filter_btn)

    def _on_activate(self, entry):
        self.on_search(entry.get_text())

    def _on_search_changed(self, entry):
        # We could implement real-time search here
        pass
