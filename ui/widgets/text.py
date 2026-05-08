# -*- coding: utf-8 -*-
# Odoo GTK 19 — Text / HTML Widget
# Inspired by E:\odoo-client-19\widget\view\form_gtk\textbox.py

from gi.repository import Gtk
from .base import WidgetBase


class TextWidget(WidgetBase):
    """text field → Gtk.TextView in ScrolledWindow"""

    def _build_widget(self):
        self.widget = Gtk.ScrolledWindow()
        self.widget.set_min_content_height(80)
        self.widget.set_hexpand(True)
        self.widget.set_vexpand(True)

        self.textview = Gtk.TextView()
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.textview.set_top_margin(8)
        self.textview.set_bottom_margin(8)
        self.textview.set_left_margin(8)
        self.textview.set_right_margin(8)
        self.widget.set_child(self.textview)

    def set_value(self, value):
        buf = self.textview.get_buffer()
        if value is False or value is None:
            buf.set_text('')
        else:
            buf.set_text(str(value))

    def get_value(self):
        buf = self.textview.get_buffer()
        start = buf.get_start_iter()
        end = buf.get_end_iter()
        return buf.get_text(start, end, False) or False

    def set_readonly(self, readonly):
        self._readonly = readonly
        self.textview.set_editable(not readonly)


class HtmlWidget(TextWidget):
    """html field → plain text for now (no web engine in GTK4)"""
    pass
