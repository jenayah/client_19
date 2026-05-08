# -*- coding: utf-8 -*-
# Odoo GTK 19 — Widget Base Interface
# Inspired by E:\odoo-client-19\widget\view\form_gtk\interface.py

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk


class WidgetBase:
    """Base interface for all Odoo field widgets (GTK4).
    
    Every field widget must subclass this and implement:
      - _build_widget() → create self.widget (Gtk.Widget)
      - set_value(value) → push a Python value into the GTK widget
      - get_value() → pull the current value from the GTK widget
    """

    # ── Construction ──────────────────────────────────────────────
    def __init__(self, field_name, field_info, attrs=None, record=None):
        """
        Args:
            field_name: Technical field name (e.g. 'name', 'partner_id')
            field_info: Dict from fields_get / get_view (type, string, relation, selection, …)
            attrs:      Raw XML attributes (widget, class, readonly, invisible, nolabel, …)
            record:     Current record data dict (for expression evaluation)
        """
        self.field_name = field_name
        self.field_info = field_info or {}
        self.attrs = attrs or {}
        self.record = record or {}
        
        self._readonly = False
        self._required = self.attrs.get('required') not in (False, '0', 'False', None)
        self._invisible = False
        
        # The actual GTK widget — subclasses fill this in _build_widget()
        self.widget = None
        self._build_widget()
        
        # Apply XML classes
        if self.widget:
            cls = self.attrs.get('class', '')
            if cls:
                for c in cls.split():
                    self.widget.add_css_class(c)

    # ── Abstract methods (override in subclasses) ─────────────────
    def _build_widget(self):
        """Create self.widget. Must be overridden."""
        raise NotImplementedError

    def set_value(self, value):
        """Push a value into the GTK widget for display."""
        raise NotImplementedError

    def get_value(self):
        """Read the current value from the GTK widget."""
        raise NotImplementedError

    # ── State management ──────────────────────────────────────────
    def set_readonly(self, readonly):
        self._readonly = readonly
        if hasattr(self.widget, 'set_editable'):
            self.widget.set_editable(not readonly)
        elif hasattr(self.widget, 'set_sensitive'):
            self.widget.set_sensitive(not readonly)

    def set_required(self, required):
        self._required = required
        if self.widget:
            if required:
                self.widget.add_css_class('o_required_modifier')
            else:
                self.widget.remove_css_class('o_required_modifier')

    def set_invisible(self, invisible):
        self._invisible = invisible
        if self.widget:
            self.widget.set_visible(not invisible)

    # ── Display helpers ───────────────────────────────────────────
    def display(self, value, record=None):
        """High-level display: update record reference then set value."""
        if record is not None:
            self.record = record
        self.set_value(value)

    @property
    def field_type(self):
        return self.field_info.get('type', 'char')

    @property
    def field_string(self):
        return self.field_info.get('string', self.field_name)

    @property
    def field_relation(self):
        return self.field_info.get('relation', '')

    # ── Utilities ─────────────────────────────────────────────────
    def grab_focus(self):
        if self.widget:
            self.widget.grab_focus()

    def destroy(self):
        pass

    @staticmethod
    def format_value(value):
        """Format a raw Odoo value for display as text."""
        if value is False or value is None or value == [] or value == ():
            return ''
        if isinstance(value, (list, tuple)):
            # Many2one: (id, name)
            if len(value) > 1:
                return str(value[1])
            if len(value) > 0:
                return str(value[0])
            return ''
        return str(value)
