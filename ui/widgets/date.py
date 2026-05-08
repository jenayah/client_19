# -*- coding: utf-8 -*-
# Odoo GTK 19 — Date / Datetime Widget
# Inspired by E:\odoo-client-19\widget\view\form_gtk\date_widget.py

from gi.repository import Gtk
from .base import WidgetBase


class DateWidget(WidgetBase):
    """date field → Gtk.Entry with calendar button"""

    def _build_widget(self):
        self.widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.widget.set_hexpand(True)

        self.entry = Gtk.Entry()
        self.entry.set_hexpand(True)
        self.entry.set_placeholder_text('YYYY-MM-DD')
        self.widget.append(self.entry)

        self.cal_btn = Gtk.Button(icon_name='x-office-calendar-symbolic')
        self.cal_btn.add_css_class('flat')
        self.cal_btn.connect('clicked', self._show_calendar)
        self.widget.append(self.cal_btn)

    def _show_calendar(self, btn):
        popover = Gtk.Popover()
        popover.set_parent(btn)
        calendar = Gtk.Calendar()
        calendar.connect('day-selected', lambda c: self._on_date_selected(c, popover))
        popover.set_child(calendar)
        popover.popup()

    def _on_date_selected(self, calendar, popover):
        dt = calendar.get_date()
        date_str = f'{dt.get_year():04d}-{dt.get_month():02d}-{dt.get_day_of_month():02d}'
        self.entry.set_text(date_str)
        popover.popdown()

    def set_value(self, value):
        if value is False or value is None:
            self.entry.set_text('')
        else:
            self.entry.set_text(str(value)[:10])

    def get_value(self):
        text = self.entry.get_text().strip()
        return text or False

    def set_readonly(self, readonly):
        self._readonly = readonly
        self.entry.set_editable(not readonly)
        self.cal_btn.set_sensitive(not readonly)


class DatetimeWidget(DateWidget):
    """datetime field → Gtk.Entry with calendar + time"""

    def _build_widget(self):
        super()._build_widget()
        self.entry.set_placeholder_text('YYYY-MM-DD HH:MM:SS')

    def set_value(self, value):
        if value is False or value is None:
            self.entry.set_text('')
        else:
            # Show full datetime
            self.entry.set_text(str(value)[:19])
