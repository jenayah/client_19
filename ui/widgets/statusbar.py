# -*- coding: utf-8 -*-
# Odoo GTK 19 — Statusbar Widget

from gi.repository import Gtk
from .base import WidgetBase


class StatusbarWidget(WidgetBase):
    """widget="statusbar" → Linked arrow buttons for workflow stages"""

    def _build_widget(self):
        self.widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.widget.add_css_class('linked')
        self.widget.set_hexpand(True)
        self.widget.set_halign(Gtk.Align.END)
        self._buttons = []
        self._selection = self.field_info.get('selection', [])

    def set_value(self, value):
        # Clear existing
        while child := self.widget.get_first_child():
            self.widget.remove(child)
        self._buttons = []

        for sval, slabel in self._selection:
            btn = Gtk.Button(label=str(slabel))
            btn.add_css_class('o_arrow_button')
            if sval == value:
                btn.add_css_class('o_arrow_button_current')
            self._buttons.append((sval, btn))
            self.widget.append(btn)

    def get_value(self):
        for sval, btn in self._buttons:
            if 'o_arrow_button_current' in (btn.get_css_classes() or []):
                return sval
        return False


class BadgeWidget(WidgetBase):
    """widget="badge" → Colored label"""

    def _build_widget(self):
        self.widget = Gtk.Label()
        self.widget.add_css_class('badge')

    def set_value(self, value):
        if value is False or value is None:
            self.widget.set_text('')
            return
        
        # If selection field, show the label not the value
        selection = self.field_info.get('selection', [])
        text = str(value)
        for sval, slabel in selection:
            if sval == value:
                text = str(slabel)
                break
        
        self.widget.set_text(text)

    def get_value(self):
        return self.widget.get_text()


class StatInfoWidget(WidgetBase):
    """widget="statinfo" → Stat button content (value + text)"""

    def _build_widget(self):
        self.widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        
        self.value_label = Gtk.Label(label='0')
        self.value_label.add_css_class('o_stat_value')
        self.widget.append(self.value_label)
        
        self.text_label = Gtk.Label(label=self.field_string)
        self.text_label.add_css_class('o_stat_text')
        self.widget.append(self.text_label)

    def set_value(self, value):
        if value is False or value is None:
            self.value_label.set_text('0')
        else:
            self.value_label.set_text(str(value))

    def get_value(self):
        return self.value_label.get_text()


class PriorityWidget(WidgetBase):
    """widget="priority" → Star rating"""

    def _build_widget(self):
        self.widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self._selection = self.field_info.get('selection', [])
        self._buttons = []
        
        for i, (val, label) in enumerate(self._selection):
            btn = Gtk.ToggleButton()
            btn.set_icon_name('starred-symbolic')
            btn.add_css_class('flat')
            btn.add_css_class('circular')
            btn._priority_val = val
            btn._priority_idx = i
            btn.connect('toggled', self._on_toggled, i)
            self._buttons.append(btn)
            self.widget.append(btn)

    def _on_toggled(self, btn, idx):
        for i, b in enumerate(self._buttons):
            b.set_active(i <= idx)

    def set_value(self, value):
        for btn in self._buttons:
            btn.set_active(False)
        if value:
            for i, (val, _) in enumerate(self._selection):
                if val == value:
                    for j in range(i + 1):
                        self._buttons[j].set_active(True)
                    break

    def get_value(self):
        last_active = False
        for btn in self._buttons:
            if btn.get_active():
                last_active = btn._priority_val
        return last_active


class HandleWidget(WidgetBase):
    """widget="handle" → Drag handle icon (display only)"""
    def _build_widget(self):
        self.widget = Gtk.Image.new_from_icon_name('list-drag-handle-symbolic')
    def set_value(self, value): pass
    def get_value(self): return False
