# -*- coding: utf-8 -*-
# Odoo GTK 19 — Float / Monetary Widget
# Inspired by E:\odoo-client-19\widget\view\form_gtk\spinbutton.py

from gi.repository import Gtk
from .base import WidgetBase


class FloatWidget(WidgetBase):
    """float field → Gtk.SpinButton with configurable digits"""

    def _build_widget(self):
        digits = 2
        raw = self.field_info.get('digits')
        if isinstance(raw, (list, tuple)) and len(raw) >= 2:
            digits = raw[1]
        elif isinstance(raw, int):
            digits = raw

        step = 10 ** (-digits) if digits > 0 else 1
        # GTK4 Adjustment: value, lower, upper, step_increment, page_increment, page_size
        adj = Gtk.Adjustment.new(0, -1e15, 1e15, step, step * 10, 0)
        self.widget = Gtk.SpinButton(adjustment=adj, digits=digits)
        self.widget.set_hexpand(True)
        self.widget.set_numeric(True)

    def set_value(self, value):
        if value is False or value is None:
            self.widget.set_value(0.0)
        else:
            self.widget.set_value(float(value))

    def get_value(self):
        return self.widget.get_value()


class MonetaryWidget(WidgetBase):
    """monetary field → Gtk.Box with currency label + entry"""

    def _build_widget(self):
        self.widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.widget.set_hexpand(True)

        self.currency_label = Gtk.Label(label='$')
        self.currency_label.add_css_class('dim-label')

        self.entry = Gtk.Entry()
        self.entry.set_hexpand(True)
        self.entry.set_input_purpose(Gtk.InputPurpose.NUMBER)

        self.widget.append(self.currency_label)
        self.widget.append(self.entry)

    def set_value(self, value):
        if value is False or value is None:
            self.entry.set_text('')
        else:
            # Format with 2 decimals by default
            try:
                self.entry.set_text(f'{float(value):,.2f}')
            except (ValueError, TypeError):
                self.entry.set_text(str(value))

        # Try to get currency symbol from record
        options = self.attrs.get('options', {})
        if isinstance(options, str):
            try:
                import ast
                options = ast.literal_eval(options)
            except Exception:
                options = {}
        currency_field = options.get('currency_field', 'currency_id') if isinstance(options, dict) else 'currency_id'
        if isinstance(currency_field, str) and self.record:
            cur = self.record.get(currency_field)
            if isinstance(cur, (list, tuple)) and len(cur) > 1:
                self.currency_label.set_text(str(cur[1]))

    def get_value(self):
        text = self.entry.get_text().replace(',', '').replace(' ', '').strip()
        try:
            return float(text)
        except ValueError:
            return 0.0
