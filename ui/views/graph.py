# -*- coding: utf-8 -*-
# Odoo GTK 19 — Graph View (Cairo Powered)

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GObject, Pango, Gio, PangoCairo
import math
from core import Model, session
import xml.etree.ElementTree as ET

class GraphView(Gtk.Box):
    def __init__(self, model_name, view_id=None, domain=None, context=None, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        self.model_name = model_name
        self.view_id = view_id
        self.domain = domain or []
        self.context = context or {}
        
        self.view_arch = None
        self.view_fields = {}
        self.graph_type = 'bar' # bar, pie, line
        self.groupby = []
        self.measure = '__count'
        self.data = [] # List of (label, value)
        
        self._setup_ui()
        self._load_view_arch()
        self.load_data()

    def _setup_ui(self):
        # Toolbar
        self.toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.toolbar.set_margin_start(6)
        self.toolbar.set_margin_end(6)
        self.toolbar.set_margin_top(6)
        self.toolbar.set_margin_bottom(6)
        self.append(self.toolbar)

        # Chart Type Buttons
        self.bar_btn = Gtk.Button(icon_name="office-chart-bar-stacked-symbolic")
        self.bar_btn.connect("clicked", self._set_type, 'bar')
        self.toolbar.append(self.bar_btn)

        self.line_btn = Gtk.Button(icon_name="office-chart-line-symbolic")
        self.line_btn.connect("clicked", self._set_type, 'line')
        self.toolbar.append(self.line_btn)

        self.pie_btn = Gtk.Button(icon_name="office-chart-pie-symbolic")
        self.pie_btn.connect("clicked", self._set_type, 'pie')
        self.toolbar.append(self.pie_btn)

        self.toolbar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        # Refresh
        self.refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        self.refresh_btn.connect("clicked", lambda x: self.load_data())
        self.toolbar.append(self.refresh_btn)

        # Drawing Area
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_vexpand(True)
        self.drawing_area.set_draw_func(self._draw_func)
        self.append(self.drawing_area)

    def _load_view_arch(self):
        try:
            res = session.client.get_view(self.model_name, view_id=self.view_id, view_type='graph')
            self.view_arch = res.get('arch', '<graph/>')
            self.view_fields = res.get('fields', {})
            
            root = ET.fromstring(self.view_arch)
            self.graph_type = root.get('type', 'bar')
            
            for field_node in root.findall('.//field'):
                fname = field_node.get('name')
                ftype = field_node.get('type')
                if ftype == 'measure':
                    self.measure = fname
                else:
                    self.groupby.append(fname)
            
            if not self.groupby:
                self.groupby = ['create_date'] if 'create_date' in self.view_fields else ['id']
                
            print(f"DEBUG: Graph Arch loaded. Type: {self.graph_type}, Groupby: {self.groupby}, Measure: {self.measure}")
        except Exception as e:
            print(f"Erreur arch Graph {self.model_name}: {e}")

    def _set_type(self, btn, gtype):
        self.graph_type = gtype
        self.drawing_area.queue_draw()

    def load_data(self):
        try:
            # Aggregate data
            fields_to_read = [] if self.measure == '__count' else [self.measure]
            res = session.client.call_kw(self.model_name, 'read_group', [], {
                'domain': self.domain,
                'fields': fields_to_read,
                'groupby': self.groupby,
                'lazy': False
            })
            
            self.data = []
            for r in res:
                label = "Inconnu"
                for g in self.groupby:
                    val = r.get(g)
                    if val:
                        label = val[1] if isinstance(val, (list, tuple)) else str(val)
                        break
                
                m_key = self.measure if self.measure != '__count' else f"{self.groupby[0]}_count"
                value = r.get(m_key, 0)
                self.data.append((label, value))
            
            self.drawing_area.queue_draw()
        except Exception as e:
            print(f"Erreur données Graph {self.model_name}: {e}")

    def _draw_func(self, area, cr, width, height, user_data=None):
        if not self.data:
            return

        # Odoo colors
        colors = [
            (0.44, 0.29, 0.40), # Odoo Purple
            (0.00, 0.64, 0.64), # Teal
            (0.95, 0.47, 0.13), # Orange
            (0.18, 0.53, 0.81), # Blue
            (0.80, 0.20, 0.20), # Red
            (0.40, 0.60, 0.20), # Green
        ]

        if self.graph_type == 'pie':
            self._draw_pie(cr, width, height, colors)
        elif self.graph_type == 'line':
            self._draw_line(cr, width, height, colors[0])
        else:
            self._draw_bar(cr, width, height, colors)

    def _draw_bar(self, cr, width, height, colors):
        margin = 60
        chart_w = width - 2 * margin
        chart_h = height - 2 * margin
        
        max_val = max([d[1] for d in self.data]) if self.data else 1
        if max_val == 0: max_val = 1
        
        bar_count = len(self.data)
        bar_w = (chart_w / bar_count) * 0.7
        spacing = (chart_w / bar_count) * 0.3
        
        # Draw Axis
        cr.set_source_rgb(0.5, 0.5, 0.5)
        cr.set_line_width(1)
        cr.move_to(margin, margin)
        cr.line_to(margin, height - margin)
        cr.line_to(width - margin, height - margin)
        cr.stroke()
        
        # Draw Bars
        for i, (label, val) in enumerate(self.data):
            h = (val / max_val) * chart_h
            x = margin + spacing/2 + i * (bar_w + spacing)
            y = height - margin - h
            
            color = colors[i % len(colors)]
            cr.set_source_rgba(*color, 0.8)
            cr.rectangle(x, y, bar_w, h)
            cr.fill()
            
            # Label (Pango)
            layout = self.drawing_area.create_pango_layout(label)
            font_desc = Pango.FontDescription("Sans 8")
            layout.set_font_description(font_desc)
            
            l_width, l_height = layout.get_pixel_size()
            cr.move_to(x + bar_w/2 - l_width/2, height - margin + 5)
            cr.set_source_rgb(0.3, 0.3, 0.3)
            PangoCairo.show_layout(cr, layout)

    def _draw_pie(self, cr, width, height, colors):
        radius = min(width, height) * 0.3
        center_x, center_y = width / 2, height / 2
        
        total = sum([d[1] for d in self.data])
        if total == 0: return
        
        current_angle = -math.pi / 2
        for i, (label, val) in enumerate(self.data):
            angle = (val / total) * 2 * math.pi
            
            cr.set_source_rgb(*colors[i % len(colors)])
            cr.move_to(center_x, center_y)
            cr.arc(center_x, center_y, radius, current_angle, current_angle + angle)
            cr.close_path()
            cr.fill()
            
            current_angle += angle

    def _draw_line(self, cr, width, height, color):
        margin = 60
        chart_w = width - 2 * margin
        chart_h = height - 2 * margin
        max_val = max([d[1] for d in self.data]) if self.data else 1
        
        cr.set_source_rgb(*color)
        cr.set_line_width(2)
        
        for i, (label, val) in enumerate(self.data):
            x = margin + i * (chart_w / (len(self.data) - 1))
            y = height - margin - (val / max_val) * chart_h
            if i == 0: cr.move_to(x, y)
            else: cr.line_to(x, y)
        cr.stroke()
