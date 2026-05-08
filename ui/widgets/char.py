# -*- coding: utf-8 -*-
# Odoo GTK 19 — Char Widget
# Inspired by E:\odoo-client-19\widget\view\form_gtk\char.py

import json
from gi.repository import Gtk
from .base import WidgetBase


class CharWidget(WidgetBase):
    """char field → Gtk.Entry
    
    Handles:
      - Standard char fields
      - Multilingual char (JSON dict → display current lang)
      - password attribute
      - size attribute
      - placeholder attribute
    """

    def _build_widget(self):
        self.widget = Gtk.Entry()
        self.widget.set_hexpand(True)
        
        # Size limit
        size = self.attrs.get('size') or self.field_info.get('size')
        if size:
            self.widget.set_max_length(int(size))
        
        # Password
        if self.attrs.get('password') or self.field_info.get('password'):
            self.widget.set_visibility(False)
        
        # Placeholder
        placeholder = self.attrs.get('placeholder') or self.field_info.get('string', '')
        if placeholder:
            self.widget.set_placeholder_text(placeholder)

    def set_value(self, value):
        if value is None or value is False:
            self.widget.set_text('')
            return
        
        # Odoo 19: multilingual char fields can be JSON dicts
        if isinstance(value, dict):
            try:
                # Try to display the user's language, fallback to 'en_US' or first value
                lang = 'fr_FR'  # TODO: get from session context
                text = value.get(lang) or value.get('en_US') or next(iter(value.values()), '')
            except Exception:
                text = json.dumps(value, ensure_ascii=False)
        elif isinstance(value, str):
            text = value
        else:
            text = str(value)
        
        self.widget.set_text(text)

    def get_value(self):
        text = self.widget.get_text().strip()
        return text or False

    def set_readonly(self, readonly):
        self._readonly = readonly
        self.widget.set_editable(not readonly)
