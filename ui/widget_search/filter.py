# -*- coding: utf-8 -*-
from gi.repository import Gtk, GObject
from . import wid_int

class filter(wid_int.wid_int):
    def __init__(self, name, parent, attrs={}, call=None):
        wid_int.wid_int.__init__(self, name, parent, attrs, call)
        self.butt = Gtk.ToggleButton(label=name)
        self.butt.add_css_class("flat")
        self.butt.connect('toggled', self._on_toggled)
        self.filter_group = None

    def _on_toggled(self, btn):
        if self.call:
            obj, fct = self.call
            fct(obj)

    def _value_get(self):
        if self.butt.get_active():
            # Use a safer evaluation that handles common Odoo variables
            domain = []
            context = {}
            eval_dict = {'uid': 1, 'True': True, 'False': False, 'None': None}
            try:
                domain_str = self.attrs.get('domain', '[]')
                # Try simple eval
                domain = eval(domain_str, {}, eval_dict)
            except Exception as e:
                print(f"Warning: Could not parse filter domain for '{self.name}': {e}")
            try:
                context_str = self.attrs.get('context', '{}')
                context = eval(context_str, {}, eval_dict)
            except Exception as e:
                print(f"Warning: Could not parse filter context for '{self.name}': {e}")
            return {'domain': domain, 'context': context}
        return {'domain': [], 'context': {}}

    def _value_set(self, value):
        self.butt.set_active(bool(value))

    value = property(_value_get, _value_set)

    def sig_activate(self, fct):
        self.butt.connect('toggled', fct)

    def clear(self):
        self.butt.set_active(False)
