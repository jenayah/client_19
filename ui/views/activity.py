# -*- coding: utf-8 -*-
# Odoo GTK 19 — Activity View

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GObject, Gio
from core import Model, session
import xml.etree.ElementTree as ET

class ActivityView(Gtk.Box):
    def __init__(self, model_name, view_id=None, domain=None, context=None, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        self.model_name = model_name
        self.view_id = view_id
        self.domain = domain or []
        self.context = context or {}
        
        self.activity_types = []
        self.records_data = []
        
        self._setup_ui()
        self._load_view_arch()
        self.load_data()

    def _setup_ui(self):
        # Toolbar
        self.toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.toolbar.set_margin_start(12)
        self.toolbar.set_margin_end(12)
        self.toolbar.set_margin_top(6)
        self.toolbar.set_margin_bottom(6)
        self.append(self.toolbar)

        # Legend
        legend = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        for label, color_class in [("Prévu", "bg-success"), ("Aujourd'hui", "bg-warning"), ("En retard", "bg-danger")]:
            dot = Gtk.Box()
            dot.set_size_request(10, 10)
            dot.add_css_class(color_class)
            dot.add_css_class('circular')
            dot.set_valign(Gtk.Align.CENTER)
            
            item = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            item.append(dot)
            item.append(Gtk.Label(label=label))
            legend.append(item)
        
        legend.set_hexpand(True)
        legend.set_halign(Gtk.Align.END)
        self.toolbar.append(legend)

        # Scrolled Window
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_vexpand(True)
        self.append(self.scroll)

        # Grid Container
        self.grid = Gtk.Grid()
        self.grid.set_column_spacing(1)
        self.grid.set_row_spacing(1)
        self.grid.add_css_class('activity-grid')
        self.scroll.set_child(self.grid)

    def _load_view_arch(self):
        try:
            # Fetch activity types for the model
            # In Odoo 19, activity types are usually global or per model
            self.activity_types = session.client.call_kw('mail.activity.type', 'search_read', [
                [('res_model', 'in', [self.model_name, False])]], 
                {'fields': ['name', 'icon']})
            if not self.activity_types:
                # Fallback to common ones
                self.activity_types = [
                    {'id': 1, 'name': 'Email', 'icon': 'fa-envelope'},
                    {'id': 2, 'name': 'Appel', 'icon': 'fa-phone'},
                    {'id': 3, 'name': 'Réunion', 'icon': 'fa-users'},
                ]
        except Exception as e:
            print(f"Erreur arch Activity {self.model_name}: {e}")

    def load_data(self):
        try:
            # Fetch records and their activities
            # Odoo 17+ uses activity_ids and activity_state
            records = session.client.call_kw(self.model_name, 'search_read', [self.domain], {
                'fields': ['display_name', 'activity_ids', 'activity_state', 'activity_type_id'],
                'limit': 40
            })
            
            # Fetch activity details
            all_act_ids = []
            for r in records:
                all_act_ids.extend(r.get('activity_ids', []))
            
            activities = {}
            if all_act_ids:
                act_data = session.client.call_kw('mail.activity', 'read', [all_act_ids], {
                    'fields': ['res_id', 'activity_type_id', 'date_deadline', 'state']
                })
                for a in act_data:
                    res_id = a.get('res_id')
                    type_id = a.get('activity_type_id')[0] if a.get('activity_type_id') else 0
                    if res_id not in activities: activities[res_id] = {}
                    activities[res_id][type_id] = a
            
            self._render_grid(records, activities)
        except Exception as e:
            print(f"Erreur données Activity {self.model_name}: {e}")

    def _render_grid(self, records, activities):
        # Clear grid
        while child := self.grid.get_first_child():
            self.grid.remove(child)

        # Header Row
        # Top-left empty cell
        corner = Gtk.Label(label="")
        corner.set_size_request(200, 40)
        corner.add_css_class('bg-light')
        self.grid.attach(corner, 0, 0, 1, 1)

        for i, atype in enumerate(self.activity_types):
            lbl = Gtk.Label(label=atype['name'])
            lbl.set_size_request(120, 40)
            lbl.add_css_class('fw-bold')
            lbl.add_css_class('bg-light')
            self.grid.attach(lbl, i + 1, 0, 1, 1)

        # Data Rows
        for row_idx, rec in enumerate(records):
            # Record Name
            name_lbl = Gtk.Label(label=rec['display_name'], xalign=0)
            name_lbl.set_size_request(200, 50)
            name_lbl.set_margin_start(12)
            name_lbl.add_css_class('border-bottom')
            self.grid.attach(name_lbl, 0, row_idx + 1, 1, 1)

            # Activity Cells
            res_id = rec['id']
            rec_activities = activities.get(res_id, {})
            
            for col_idx, atype in enumerate(self.activity_types):
                type_id = atype['id']
                cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                cell.set_size_request(120, 50)
                cell.set_valign(Gtk.Align.CENTER)
                cell.set_halign(Gtk.Align.CENTER)
                cell.add_css_class('border-bottom')
                cell.add_css_class('border-start')

                if type_id in rec_activities:
                    act = rec_activities[type_id]
                    state = act.get('state')
                    
                    dot = Gtk.Box()
                    dot.set_size_request(14, 14)
                    dot.add_css_class('circular')
                    
                    if state == 'planned': dot.add_css_class('bg-success')
                    elif state == 'today': dot.add_css_class('bg-warning')
                    elif state == 'overdue': dot.add_css_class('bg-danger')
                    else: dot.add_css_class('bg-secondary')
                    
                    cell.append(dot)
                
                self.grid.attach(cell, col_idx + 1, row_idx + 1, 1, 1)
