import ast
import xml.etree.ElementTree as ET
from gi.repository import Gtk, GObject, Pango, Gio
from core.session import session

class SearchView(Gtk.Box):
    __gsignals__ = {
        'search-changed': (GObject.SignalFlags.RUN_FIRST, None, (object, object)), # (domain, context)
    }

    def __init__(self, model_name, search_arch, **kwargs):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, **kwargs)
        self.model_name = model_name
        self.arch = search_arch
        self.add_css_class("search-view")
        
        self.filters = [] # List of {'name', 'label', 'domain', 'active', 'btn'}
        self.group_bys = [] # List of {'name', 'label', 'context', 'active', 'btn'}
        
        # UI Components
        self.search_entry = Gtk.SearchEntry(placeholder_text="Rechercher...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("activate", self._on_search_triggered)
        self.append(self.search_entry)
        
        self.filters_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.append(self.filters_box)
        
        self._parse_arch()
        self._build_ui()

    def _parse_arch(self):
        try:
            root = ET.fromstring(self.arch)
            for node in root:
                if node.tag == 'filter':
                    name = node.get('name', '')
                    label = node.get('string', name)
                    domain = node.get('domain', '[]')
                    context = node.get('context', '{}')
                    
                    if 'group_by' in context:
                        self.group_bys.append({
                            'name': name, 'label': label, 'context': context, 'active': False
                        })
                    else:
                        self.filters.append({
                            'name': name, 'label': label, 'domain': domain, 'active': False
                        })
                elif node.tag == 'separator':
                    pass # TODO: handle separators
        except Exception as e:
            print(f"Error parsing search arch: {e}")

    def _build_ui(self):
        # Filters Button
        if self.filters:
            filter_btn = Gtk.MenuButton(label="Filtres", icon_name="view-filter-symbolic")
            filter_menu = Gio.Menu()
            for i, f in enumerate(self.filters):
                action_name = f"filter_{i}"
                # In GTK4 with Adwaita/GMenu it's better to use ToggleButtons for simple search
                # but let's use a simpler approach for now: a horizontal flow box or similar
                pass
        
        # Simplified: Just horizontal buttons for main filters
        for f in self.filters[:5]: # Show first 5 as buttons
            btn = Gtk.ToggleButton(label=f['label'])
            btn.add_css_class("flat")
            btn.connect("toggled", self._on_filter_toggled, f)
            self.filters_box.append(btn)
            f['btn'] = btn

    def _on_filter_toggled(self, btn, filter_data):
        filter_data['active'] = btn.get_active()
        self._emit_search()

    def _on_search_triggered(self, entry):
        self._emit_search()

    def _emit_search(self):
        domain = []
        # Add entry search (simplified: search on 'name' field)
        text = self.search_entry.get_text()
        if text:
            domain.append(('name', 'ilike', text))
            
        # Add active filters
        for f in self.filters:
            if f['active']:
                try:
                    f_domain = ast.literal_eval(f['domain'])
                    if isinstance(f_domain, list):
                        domain.extend(f_domain)
                except: pass
                
        context = {}
        # Add active group_bys
        group_by = []
        for g in self.group_bys:
            if g.get('active'):
                try:
                    g_ctx = ast.literal_eval(g['context'])
                    if 'group_by' in g_ctx:
                        group_by.append(g_ctx['group_by'])
                except: pass
        if group_by:
            context['group_by'] = group_by
            
        self.emit('search-changed', domain, context)
