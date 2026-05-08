# -*- coding: utf-8 -*-
# Odoo GTK 19 — URL / Email / Phone Widgets
# Inspired by E:\odoo-client-19\widget\view\form_gtk\url.py

from gi.repository import Gtk
from .base import WidgetBase


class UrlWidget(WidgetBase):
    """url field → Gtk.LinkButton"""

    def _build_widget(self):
        self.widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.widget.set_hexpand(True)
        self.entry = Gtk.Entry()
        self.entry.set_hexpand(True)
        self.entry.set_placeholder_text('https://')
        self.widget.append(self.entry)
        
        self.btn_open = Gtk.Button(icon_name='web-browser-symbolic')
        self.btn_open.add_css_class('flat')
        self.widget.append(self.btn_open)

    def set_value(self, value):
        self.entry.set_text(str(value) if value else '')

    def get_value(self):
        return self.entry.get_text().strip() or False


class EmailWidget(WidgetBase):
    """email field → Gtk.Entry with mail icon"""

    def _build_widget(self):
        self.widget = Gtk.Entry()
        self.widget.set_hexpand(True)
        self.widget.set_placeholder_text('email@example.com')
        self.widget.set_input_purpose(Gtk.InputPurpose.EMAIL)

    def set_value(self, value):
        self.widget.set_text(str(value) if value else '')

    def get_value(self):
        return self.widget.get_text().strip() or False


class PhoneWidget(WidgetBase):
    """phone field → Gtk.Entry with phone icon"""

    def _build_widget(self):
        self.widget = Gtk.Entry()
        self.widget.set_hexpand(True)
        self.widget.set_placeholder_text('+33...')
        self.widget.set_input_purpose(Gtk.InputPurpose.PHONE)

    def set_value(self, value):
        self.widget.set_text(str(value) if value else '')

    def get_value(self):
        return self.widget.get_text().strip() or False
