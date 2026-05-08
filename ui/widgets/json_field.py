# -*- coding: utf-8 -*-
# Odoo GTK 19 — JSON / Progressbar / Reference Widgets

from gi.repository import Gtk
from .base import WidgetBase
import json


class JsonWidget(WidgetBase):
    """json / analytic_distribution → Gtk.Entry showing JSON"""

    def _build_widget(self):
        self.widget = Gtk.Entry()
        self.widget.set_hexpand(True)
        self._raw = {}

    def set_value(self, value):
        self._raw = value or {}
        if isinstance(value, dict):
            self.widget.set_text(json.dumps(value, ensure_ascii=False))
        elif value:
            self.widget.set_text(str(value))
        else:
            self.widget.set_text('')

    def get_value(self):
        try:
            return json.loads(self.widget.get_text())
        except Exception:
            return self._raw


class ProgressBarWidget(WidgetBase):
    """widget="progressbar" → Gtk.ProgressBar"""

    def _build_widget(self):
        self.widget = Gtk.ProgressBar()
        self.widget.set_hexpand(True)
        self.widget.set_show_text(True)

    def set_value(self, value):
        if value is False or value is None:
            value = 0
        frac = max(0.0, min(1.0, float(value) / 100.0))
        self.widget.set_fraction(frac)
        self.widget.set_text(f'{float(value):.0f}%')

    def get_value(self):
        return self.widget.get_fraction() * 100


class ReferenceWidget(WidgetBase):
    """reference field → Model selector + Many2one entry"""

    def _build_widget(self):
        self.widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.widget.set_hexpand(True)

        self.model_entry = Gtk.Entry()
        self.model_entry.set_placeholder_text('Model')
        self.model_entry.set_hexpand(False)
        self.model_entry.set_width_chars(20)
        self.widget.append(self.model_entry)

        self.value_entry = Gtk.Entry()
        self.value_entry.set_placeholder_text('Record')
        self.value_entry.set_hexpand(True)
        self.widget.append(self.value_entry)

    def set_value(self, value):
        if not value or value is False:
            self.model_entry.set_text('')
            self.value_entry.set_text('')
            return
        # reference format: "model,id"
        if isinstance(value, str) and ',' in value:
            model, rid = value.split(',', 1)
            self.model_entry.set_text(model)
            self.value_entry.set_text(rid)
        else:
            self.value_entry.set_text(str(value))

    def get_value(self):
        model = self.model_entry.get_text().strip()
        rid = self.value_entry.get_text().strip()
        if model and rid:
            return f'{model},{rid}'
        return False


class ColorWidget(WidgetBase):
    """widget="color" → Gtk.ColorButton"""

    def _build_widget(self):
        self.widget = Gtk.ColorButton()

    def set_value(self, value):
        pass  # TODO: parse color index

    def get_value(self):
        return False


class PropertiesWidget(WidgetBase):
    """widget="properties" → simple label (complex server-side widget)"""

    def _build_widget(self):
        self.widget = Gtk.Label(label='', xalign=0)
        self.widget.set_hexpand(True)

    def set_value(self, value):
        if value and isinstance(value, list):
            texts = []
            for prop in value:
                if isinstance(prop, dict):
                    texts.append(f"{prop.get('string', '')}: {prop.get('value', '')}")
            self.widget.set_text(', '.join(texts))
        else:
            self.widget.set_text('')

    def get_value(self):
        return False
