# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET
from gi.repository import Gtk, GObject, Gio
from . import wid_int, char, filter

widgets_type = {
    'char': (char.char, 2),
    'text': (char.char, 2),
    'many2one': (char.char, 2),
    'filter': (filter.filter, 1),
}

class LegacySearchForm(Gtk.Box):
    def __init__(self, xml_arch, fields, model=None, callback=None, context=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.xml_arch = xml_arch
        self.fields = fields
        self.model = model
        self.callback = callback
        self.context = context or {}
        self.widgets = {}
        
        # 1. Main fields FlowBox
        self.fields_flow = Gtk.FlowBox()
        self.fields_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.fields_flow.set_column_spacing(12)
        self.fields_flow.set_row_spacing(6)
        self.fields_flow.set_hexpand(True)
        self.append(self.fields_flow)
        
        # 2. Filters Menu Button
        self.filter_button = Gtk.MenuButton(label="Filtres", icon_name="view-filter-symbolic")
        self.filter_button.set_valign(Gtk.Align.END)
        self.append(self.filter_button)
        
        self.filter_popover = Gtk.Popover()
        self.filter_button.set_popover(self.filter_popover)
        self.filter_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._set_margins(self.filter_box)
        self.filter_popover.set_child(self.filter_box)

        # 3. Group By Menu Button
        self.group_button = Gtk.MenuButton(label="Regrouper par", icon_name="view-group-symbolic")
        self.group_button.set_valign(Gtk.Align.END)
        self.append(self.group_button)
        
        self.group_popover = Gtk.Popover()
        self.group_button.set_popover(self.group_popover)
        self.group_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._set_margins(self.group_box)
        self.group_popover.set_child(self.group_box)
        
        self._build_ui()

    def _set_margins(self, widget):
        widget.set_margin_start(10)
        widget.set_margin_end(10)
        widget.set_margin_top(10)
        widget.set_margin_bottom(10)

    def _build_ui(self):
        try:
            root = ET.fromstring(self.xml_arch)
            self._parse_node(root)
        except Exception as e:
            print(f"Error building legacy search: {e}")

    def _parse_node(self, node):
        for child in node:
            attrs = child.attrib
            if child.tag == 'field':
                name = attrs.get('name')
                field_info = self.fields.get(name, {}).copy()
                field_info.update(attrs)
                
                ftype = field_info.get('type', 'char')
                if ftype in widgets_type:
                    widget_cls = widgets_type[ftype][0]
                    label_text = attrs.get('string', field_info.get('string', name))
                    
                    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                    label = Gtk.Label(label=label_text)
                    label.set_halign(Gtk.Align.START)
                    label.add_css_class("caption")
                    vbox.append(label)
                    
                    w_inst = widget_cls(name, self, field_info, screen=None)
                    w_inst.sig_activate(self._on_activated)
                    vbox.append(w_inst.widget if hasattr(w_inst, 'widget') else w_inst.butt)
                    
                    self.fields_flow.append(vbox)
                    self.widgets[name] = w_inst
                    
            elif child.tag == 'filter':
                name = attrs.get('string') or attrs.get('name', 'Filter')
                w_inst = filter.filter(name, self, attrs, call=(self, self._on_activated))
                
                # Check if it's a Group By filter
                if 'group_by' in attrs.get('context', ''):
                    self.group_box.append(w_inst.butt)
                else:
                    self.filter_box.append(w_inst.butt)
                    
                self.widgets[name] = w_inst
            
            elif child.tag in ('group', 'search'):
                self._parse_node(child)

    def _on_activated(self, *args):
        if self.callback:
            domain, context = self.get_value()
            self.callback(domain, context)

    def get_value(self):
        domain = []
        context = {}
        for w in self.widgets.values():
            val = w.value
            if val.get('domain'):
                domain.extend(val['domain'])
            if val.get('context'):
                # Handle group_by merge correctly
                new_ctx = val['context']
                if 'group_by' in new_ctx:
                    if 'group_by' not in context:
                        context['group_by'] = []
                    gb = new_ctx['group_by']
                    if isinstance(gb, str): gb = [gb]
                    context['group_by'].extend(gb)
                else:
                    context.update(new_ctx)
        return domain, context

    def clear(self):
        for w in self.widgets.values():
            w.clear()
