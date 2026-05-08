# -*- coding: utf-8 -*-
# Odoo GTK 19 — Integer Widget
# Inspired by E:\odoo-client-19\widget\view\form_gtk\spinint.py

from gi.repository import Gtk
from .base import WidgetBase


class IntegerWidget(WidgetBase):
    """integer field → Gtk.SpinButton (increment 1)"""

    def _build_widget(self):
        # GTK4 Adjustment: value, lower, upper, step_increment, page_increment, page_size
        adj = Gtk.Adjustment.new(0, -2147483648, 2147483647, 1, 10, 0)
        self.widget = Gtk.SpinButton(adjustment=adj, digits=0)
        self.widget.set_hexpand(True)
        self.widget.set_numeric(True)

    def set_value(self, value):
        if value is False or value is None:
            self.widget.set_value(0)
        else:
            self.widget.set_value(int(value))

    def get_value(self):
        return int(self.widget.get_value())
