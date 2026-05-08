import ast
import xml.etree.ElementTree as ET
from gi.repository import Gtk, Adw, GObject
from .views import ListView, KanbanView, GraphView, PivotView, FormView, ActivityView
from .widget_search.form import LegacySearchForm
from core.session import session

class OdooTabPage(Gtk.Box):
    __gsignals__ = {
        'open-report': (GObject.SignalFlags.RUN_FIRST, None, (str, int, str)),
    }
    
    @staticmethod
    def _safe_eval(value):
        """Safely parse a domain/context that may be a Python literal string."""
        if isinstance(value, str):
            try:
                return ast.literal_eval(value)
            except Exception:
                return [] if value.strip().startswith('[') else {}
        return value if value else ([] if isinstance(value, list) else {})

    def __init__(self, model_name, title, action_data=None, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        self.model_name = model_name
        self.title = title
        self.action_data = action_data or {}
        vid = self.action_data.get('view_id')
        if isinstance(vid, (list, tuple)) and vid:
            self.view_id = vid[0]
        else:
            self.view_id = vid if isinstance(vid, int) else None
        self.domain = self._safe_eval(self.action_data.get('domain', []))
        self.context = self._safe_eval(self.action_data.get('context', {}))
        
        # Resolve search_default_* from context into domain filters
        self._resolve_search_defaults()
        
        # ViewStack for this tab
        self.view_stack = Adw.ViewStack(vexpand=True)
        self.append(self.view_stack)
        
        # Search View (MUST be setup AFTER view_stack)
        self.search_view = None
        self._setup_search_view()
        
        self._setup_views()

    def _resolve_search_defaults(self):
        """Convert search_default_XXX context keys into actual domain filters.
        
        Odoo web client does this by loading the search view XML and finding
        <filter name="XXX" domain="[...]"/>. We replicate the same logic.
        """
        if not isinstance(self.context, dict):
            return
        
        # Find all search_default_* keys
        search_defaults = {}
        for key, value in self.context.items():
            if key.startswith('search_default_') and value:
                filter_name = key[len('search_default_'):]
                search_defaults[filter_name] = value
        
        if not search_defaults:
            return
        
        # Load the search view to find the filter domains
        try:
            search_view_id = self.action_data.get('search_view_id')
            if isinstance(search_view_id, (list, tuple)) and search_view_id:
                search_view_id = search_view_id[0]
            else:
                search_view_id = None
            
            res = session.client.get_view(
                self.model_name, view_id=search_view_id, view_type='search')
            arch = res.get('arch', '<search/>')
            root = ET.fromstring(arch)
            
            collected_domains = []
            
            for filter_node in root.iter('filter'):
                fname = filter_node.get('name', '')
                if fname in search_defaults:
                    domain_str = filter_node.get('domain', '')
                    if domain_str:
                        try:
                            filter_domain = ast.literal_eval(domain_str)
                            if isinstance(filter_domain, list):
                                collected_domains.append(filter_domain)
                                print(f"DEBUG: Collected search_default_{fname} -> domain: {filter_domain}")
                        except Exception as e:
                            print(f"Warning: Could not parse filter domain for '{fname}': {e!r}")
            
            # Also handle search_default for fields (not filters)
            for filter_name, filter_value in search_defaults.items():
                already_handled = False
                for fn in root.iter('filter'):
                    if fn.get('name', '') == filter_name:
                        already_handled = True
                        break
                if already_handled: continue
                
                for field_node in root.iter('field'):
                    if field_node.get('name', '') == filter_name:
                        if filter_value:
                            if isinstance(filter_value, str):
                                collected_domains.append([(filter_name, 'ilike', filter_value)])
                            else:
                                collected_domains.append([(filter_name, '=', filter_value)])
                        break
            
            if collected_domains:
                if not isinstance(self.domain, list):
                    self.domain = []
                
                # Merge domains: if multiple, OR them together (basic heuristic for search defaults)
                merged_search_domain = []
                for i in range(len(collected_domains) - 1):
                    merged_search_domain.append('|')
                for d in collected_domains:
                    merged_search_domain.extend(d)
                
                if self.domain:
                    # AND the action domain with the search domain
                    self.domain = ['&'] + self.domain + merged_search_domain
                else:
                    self.domain = merged_search_domain
                
                print(f"DEBUG: Final resolved domain: {self.domain}")
                        
        except Exception as e:
            print(f"Warning: Could not resolve search_default filters: {e}")
            import traceback
            traceback.print_exc()
        
    def _setup_search_view(self):
        try:
            search_view_id = self.action_data.get('search_view_id')
            if isinstance(search_view_id, (list, tuple)) and search_view_id:
                search_view_id = search_view_id[0]
            
            res = session.client.get_view(self.model_name, view_id=search_view_id, view_type='search')
            arch = res.get('arch', '<search/>')
            fields = res.get('fields', {})
            
            self.search_view = LegacySearchForm(arch, fields, model=self.model_name, callback=self._on_search_changed_legacy, context=self.context)
            self.search_view.set_margin_start(12)
            self.search_view.set_margin_end(12)
            self.search_view.set_margin_top(6)
            self.search_view.set_margin_bottom(6)
            self.prepend(self.search_view)
            
            # Watch view changes to hide search bar in Form view
            self.view_stack.connect("notify::visible-child", self._on_view_changed)
            # Initial check
            GObject.idle_add(self._on_view_changed, self.view_stack, None)
        except Exception as e:
            print(f"Error setting up search view: {e}")

    def _on_view_changed(self, stack, pspec):
        if not self.search_view: return
        view = stack.get_visible_child()
        if not view: return
        
        # Check if it's a Form view by checking the class name
        view_type = type(view).__name__
        print(f"DEBUG: View changed to {view_type}")
        
        if view_type == 'FormView':
            # Strictly remove from parent to be 100% sure it's gone
            if self.search_view.get_parent() == self:
                print("DEBUG: Hiding search bar (FormView)")
                self.remove(self.search_view)
        else:
            # Re-insert at the top (index 0) if it was removed
            if self.search_view.get_parent() is None:
                print(f"DEBUG: Showing search bar ({view_type})")
                self.prepend(self.search_view)
            self.search_view.set_visible(True)

    def _on_search_changed_legacy(self, domain, context):
        # Ensure we are working with correct types
        base_domain = self.domain if isinstance(self.domain, list) else []
        search_domain = domain if isinstance(domain, list) else []
        full_domain = base_domain + search_domain
        
        base_context = self.context if isinstance(self.context, dict) else {}
        search_context = context if isinstance(context, dict) else {}
        full_context = base_context.copy()
        full_context.update(search_context)
        
        # Refresh current view
        current_view = self.view_stack.get_visible_child()
        if hasattr(current_view, 'load_data'):
            current_view.domain = full_domain
            current_view.context = full_context
            current_view.load_data()

    def _setup_views(self):
        # Determine allowed views
        view_mode_str = self.action_data.get('view_mode', 'list,form')
        allowed_modes = [m.strip() for m in view_mode_str.split(',')]
        # Map Odoo 'tree' to our 'list'
        allowed_modes = ['list' if m == 'tree' else m for m in allowed_modes]
        
        # Action views mapping: list of [view_id, view_type]
        views = self.action_data.get('views', [])
        mode_to_id = {}
        for v in views:
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                vid, vmode = v[0], v[1]
                if vmode == 'tree': vmode = 'list'
                mode_to_id[vmode] = vid
        
        # If a single view_id was also provided, it usually matches the first mode
        if self.view_id and allowed_modes:
            if allowed_modes[0] not in mode_to_id:
                mode_to_id[allowed_modes[0]] = self.view_id

        first_mode = allowed_modes[0] if allowed_modes else 'list'
        
        # 1. List View
        self.list_view = ListView(self.model_name, view_id=mode_to_id.get('list'), 
                                  domain=self.domain, context=self.context)
        self.list_view.connect('record-activated', self._on_record_activated)
        self.list_view.connect('create-clicked', self._on_create_record)
        self.list_view.connect('edit-clicked', self._on_record_activated)
        if 'list' in allowed_modes:
            self.view_stack.add_titled_with_icon(self.list_view, "list", "Liste", "view-list-symbolic")
        
        # 2. Kanban View
        self.kanban_view = KanbanView(self.model_name, view_id=mode_to_id.get('kanban'),
                                      domain=self.domain, context=self.context)
        if hasattr(self.kanban_view, 'connect'):
            try:
                self.kanban_view.connect("record-activated", self._on_record_activated)
            except Exception:
                pass
        if 'kanban' in allowed_modes:
            self.view_stack.add_titled_with_icon(self.kanban_view, "kanban", "Kanban", "view-grid-symbolic")
        
        # 3. Graph View
        self.graph_view = GraphView(self.model_name, view_id=mode_to_id.get('graph'),
                                   domain=self.domain, context=self.context)
        if 'graph' in allowed_modes:
            self.view_stack.add_titled_with_icon(self.graph_view, "graph", "Graphe", "office-chart-area-stacked-symbolic")
        
        # 4. Form View
        self.form_view = FormView(self.model_name, view_id=mode_to_id.get('form'))
        self.form_view.connect('back-to-list', self._on_back_to_list)
        self.form_view.connect('open-report', lambda f, m, r, n: self.emit('open-report', m, r, n))
        if 'form' in allowed_modes:
            self.view_stack.add_titled_with_icon(self.form_view, "form", "Formulaire", "text-x-generic-symbolic")
        else:
            self.view_stack.add_named(self.form_view, "form")

        # 5. Activity View
        if 'activity' in allowed_modes:
            self.activity_view = ActivityView(self.model_name, view_id=mode_to_id.get('activity'),
                                             domain=self.domain, context=self.context)
            self.view_stack.add_titled_with_icon(self.activity_view, "activity", "Activités", "contact-new-symbolic")

        # 6. Pivot View
        if 'pivot' in allowed_modes:
            self.pivot_view = PivotView(self.model_name, view_id=mode_to_id.get('pivot'),
                                       domain=self.domain, context=self.context)
            self.view_stack.add_titled_with_icon(self.pivot_view, "pivot", "Pivot", "office-spreadsheet-symbolic")

        # Show the first mode by default
        target = first_mode if first_mode in allowed_modes else (allowed_modes[0] if allowed_modes else "list")
        self.view_stack.set_visible_child_name(target)

    def _on_record_activated(self, list_view, res_id):
        self.form_view.res_id = res_id
        self.form_view.load_record()
        self.view_stack.set_visible_child_name("form")

    def _on_create_record(self, list_view):
        """Open form view in creation mode (no res_id)."""
        self.form_view.res_id = None
        self.form_view.load_record()  # Will load defaults
        self.view_stack.set_visible_child_name("form")

    def _on_back_to_list(self, form_view):
        """Return to list view and refresh data."""
        self.list_view.load_data()
        self.view_stack.set_visible_child_name("list")
