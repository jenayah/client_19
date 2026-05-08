from gi.repository import Gtk, Adw, Gio, GdkPixbuf
from core import session
from .tab_page import OdooTabPage
from .views.report_view import ReportView

class OdooMainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Odoo GTK 19")
        self.set_default_size(1200, 800)

        # Main Layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.main_box)

        # HeaderBar
        self.header_bar = Adw.HeaderBar()
        self.main_box.append(self.header_bar)
        
        # Split View for Sidebar
        self.split_view = Adw.NavigationSplitView(vexpand=True)
        self.main_box.append(self.split_view)
        
        # Sidebar
        self.sidebar_page = Adw.NavigationPage(title="Navigation")
        self.sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.sidebar_page.set_child(self.sidebar_box)
        self.split_view.set_sidebar(self.sidebar_page)
        
        # Sidebar List
        self.sidebar_scroll = Gtk.ScrolledWindow(vexpand=True)
        self.sidebar_list = Gtk.ListBox()
        self.sidebar_list.add_css_class("navigation-sidebar")
        self.sidebar_scroll.set_child(self.sidebar_list)
        self.sidebar_box.append(self.sidebar_scroll)
        
        # Content Area with TabView
        self.tab_view = Adw.TabView()
        self.tab_bar = Adw.TabBar(view=self.tab_view)
        self.tab_bar.set_autohide(False) # Force visibility
        
        # Tab Overview
        self.tab_overview = Adw.TabOverview(view=self.tab_view)
        
        # Menu Toggle Button in Header (Gero Logo)
        self.menu_btn = Gtk.ToggleButton()
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale("gero_icon.svg", -1, 24, True)
        img_menu = Gtk.Image.new_from_pixbuf(pixbuf)
        self.menu_btn.set_child(img_menu)
        self.menu_btn.set_tooltip_text("Afficher / Masquer le menu")
        self.menu_btn.set_active(True)
        self.menu_btn.connect("toggled", self._on_menu_toggle)
        self.header_bar.pack_start(self.menu_btn)

        # Tab overview button removed
        pass
        
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True)
        self.content_box.append(self.tab_bar)
        self.content_box.append(self.tab_view)
        
        self.content_page = Adw.NavigationPage(title="Odoo")
        self.content_page.set_child(self.content_box)
        self.split_view.set_content(self.content_page)
        
        # ViewSwitcher in Header
        self.view_switcher_title = Adw.ViewSwitcherTitle()
        self.header_bar.set_title_widget(self.view_switcher_title)
        
        # Connect tab change to update header
        self.tab_view.connect("notify::selected-page", self._on_tab_changed)
        
        self._load_menus()

    def _on_menu_toggle(self, btn):
        """Toggle sidebar visibility."""
        show = btn.get_active()
        if show:
            self.split_view.set_collapsed(False)
            self.sidebar_page.set_child(self.sidebar_box)
        else:
            self.split_view.set_collapsed(True)
            self.split_view.set_show_content(True)
    def _on_tab_changed(self, tab_view, params):
        page = tab_view.get_selected_page()
        if page:
            tab_content = page.get_child()
            if hasattr(tab_content, 'view_stack'):
                self.view_switcher_title.set_stack(tab_content.view_stack)
                self.view_switcher_title.set_title(page.get_title())
            else:
                self.view_switcher_title.set_stack(None)
                self.view_switcher_title.set_title(page.get_title())

    def _load_menus(self):
        try:
            menus = session.client.load_menus()
            
            if isinstance(menus, dict):
                top_menus = menus.get('children', [])
            elif isinstance(menus, list):
                top_menus = menus
            else:
                top_menus = []
            
            # Clear current list
            while child := self.sidebar_list.get_first_child():
                self.sidebar_list.remove(child)
                
            for menu in top_menus:
                self._add_menu_row(self.sidebar_list, menu)
            
        except Exception as e:
            print(f"Erreur chargement menus: {e}")

    def _add_menu_row(self, container, menu, depth=0):
        from gi.repository import GLib
        children = menu.get('children', [])
        name = menu.get('name', 'Menu sans nom')
        # Ensure name is escaped even if it came from a fallback
        safe_name = GLib.markup_escape_text(name) if isinstance(name, str) else str(name)
        
        if children:
            # It's a category/parent menu
            expander = Adw.ExpanderRow(title=safe_name)
            if isinstance(container, Adw.ExpanderRow):
                container.add_row(expander)
            else:
                container.append(expander)
                
            for child in children:
                self._add_menu_row(expander, child, depth + 1)
        else:
            # It's a leaf menu (clickable action)
            row = Adw.ActionRow(title=safe_name)
            row.set_activatable(True)
            row.menu_data = menu
            row.connect("activated", self._on_menu_row_activated)
            
            if isinstance(container, Adw.ExpanderRow):
                container.add_row(row)
            else:
                container.append(row)

    def _on_menu_row_activated(self, row):
        # Forward to the existing handler
        self._on_menu_activated(None, row)

    def _on_menu_activated(self, listbox, row):
        menu = row.menu_data
        action_ref = menu.get('action')
        if not action_ref:
            return
            
        print(f"Chargement de l'action: {action_ref}")
        try:
            action = None
            if isinstance(action_ref, str) and ',' in action_ref:
                # Format "ir.actions.act_window,123"
                act_model, act_id = action_ref.split(',')
                res = session.client.call_kw(act_model, 'read', [[int(act_id)]], {})
                if res and isinstance(res, list):
                    action = res[0]
            elif isinstance(action_ref, (list, tuple)):
                # Format [id, name]
                act_id = action_ref[0]
                res = session.client.call_kw('ir.actions.actions', 'read', [[int(act_id)]], {})
                if res and isinstance(res, list):
                    action = res[0]
                
                if action and action.get('type') == 'ir.actions.act_window':
                    res = session.client.call_kw('ir.actions.act_window', 'read', [[int(act_id)]], {})
                    if res and isinstance(res, list):
                        action = res[0]
            
            if action and action.get('res_model'):
                self._show_model_list(action.get('res_model'), action.get('name'), action)
                
        except Exception as e:
            print(f"Erreur chargement action: {e}")

    def _show_model_list(self, model_name, title, action_data=None):
        # Create a new tab page
        tab_content = OdooTabPage(model_name, title, action_data=action_data)
        tab_content.connect('open-report', self._on_open_report)
        
        # Add to TabView
        page = self.tab_view.append(tab_content)
        page.set_title(title)
        page.set_live_thumbnail(True)
        
        # Select the new page
        self.tab_view.set_selected_page(page)

    def _on_open_report(self, tab, model, res_id, report_name):
        """Open a new tab with the native report view."""
        title = f"Rapport: {report_name}"
        report_content = ReportView(model, res_id, report_name)
        
        page = self.tab_view.append(report_content)
        page.set_title(title)
        page.set_live_thumbnail(True)
        self.tab_view.set_selected_page(page)
