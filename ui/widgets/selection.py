# -*- coding: utf-8 -*-
# Odoo GTK 19 — Selection Widget
# Inspired by E:\odoo-client-19\widget\view\form_gtk\selection.py

from gi.repository import Gtk, GObject
from .base import WidgetBase


class SelectionWidget(WidgetBase):
    """selection field → Gtk.DropDown"""

    def _build_widget(self):
        self._selection = self.field_info.get('selection', [])
        self._values = [s[0] for s in self._selection]
        labels = [str(s[1]) for s in self._selection]
        
        self.string_list = Gtk.StringList.new(labels)
        self.widget = Gtk.DropDown.new(self.string_list)
        self.widget.set_hexpand(True)

    def set_value(self, value):
        if value in self._values:
            idx = self._values.index(value)
            self.widget.set_selected(idx)
        else:
            self.widget.set_selected(Gtk.INVALID_LIST_POSITION)

    def get_value(self):
        idx = self.widget.get_selected()
        if idx != Gtk.INVALID_LIST_POSITION and idx < len(self._values):
            return self._values[idx]
        return False

    def set_readonly(self, readonly):
        self._readonly = readonly
        self.widget.set_sensitive(not readonly)


class RadioWidget(WidgetBase):
    """widget="radio" → Gtk.CheckButton group"""

    def _build_widget(self):
        self._selection = self.field_info.get('selection', [])
        self.widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.widget.add_css_class('radio-group')
        
        self._buttons = []
        group = None
        for val, label in self._selection:
            btn = Gtk.CheckButton(label=str(label))
            if group:
                btn.set_group(group)
            else:
                group = btn
            btn._odoo_value = val
            self._buttons.append(btn)
            self.widget.append(btn)

    def set_value(self, value):
        for btn in self._buttons:
            if btn._odoo_value == value:
                btn.set_active(True)
                break

    def get_value(self):
        for btn in self._buttons:
            if btn.get_active():
                return btn._odoo_value
        return False
