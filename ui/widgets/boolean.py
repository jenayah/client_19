# -*- coding: utf-8 -*-
# Odoo GTK 19 — Boolean Widget
# Inspired by E:\odoo-client-19\widget\view\form_gtk\checkbox.py

from gi.repository import Gtk
from .base import WidgetBase


class BooleanWidget(WidgetBase):
    """boolean field → Gtk.CheckButton"""

    def _build_widget(self):
        self.widget = Gtk.CheckButton()

    def set_value(self, value):
        self.widget.set_active(bool(value))

    def get_value(self):
        return self.widget.get_active()

    def set_readonly(self, readonly):
        self._readonly = readonly
        self.widget.set_sensitive(not readonly)


class ToggleWidget(WidgetBase):
    """widget="boolean_toggle" or widget="toggle" → Gtk.Switch"""

    def _build_widget(self):
        self.widget = Gtk.Switch()
        self.widget.set_valign(Gtk.Align.CENTER)

    def set_value(self, value):
        self.widget.set_active(bool(value))

    def get_value(self):
        return self.widget.get_active()

    def set_readonly(self, readonly):
        self._readonly = readonly
        self.widget.set_sensitive(not readonly)


class FavoriteWidget(WidgetBase):
    """widget="boolean_favorite" → Star toggle button"""

    def _build_widget(self):
        self.widget = Gtk.ToggleButton()
        self.widget.set_icon_name('starred-symbolic')
        self.widget.add_css_class('flat')
        self.widget.add_css_class('circular')
        self._active = False
        self.widget.connect('toggled', self._on_toggled)

    def _on_toggled(self, btn):
        self._active = btn.get_active()
        if self._active:
            btn.set_icon_name('starred-symbolic')
            btn.add_css_class('accent')
        else:
            btn.set_icon_name('non-starred-symbolic')
            btn.remove_css_class('accent')

    def set_value(self, value):
        self._active = bool(value)
        self.widget.set_active(self._active)

    def get_value(self):
        return self._active
