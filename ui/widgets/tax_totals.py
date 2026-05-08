# -*- coding: utf-8 -*-
# Odoo GTK 19 — Tax Totals Widget
# For widget="account-tax-totals-field"

from gi.repository import Gtk
from .base import WidgetBase
import json


class TaxTotalsWidget(WidgetBase):
    """Widget for rendering the tax totals summary (subtotals, taxes, grand total)."""

    def _build_widget(self):
        self.widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.widget.set_halign(Gtk.Align.END)
        self.widget.add_css_class('o_tax_totals')
        
        self.grid = Gtk.Grid()
        self.grid.set_column_spacing(20)
        self.grid.set_row_spacing(8)
        self.widget.append(self.grid)

    def set_value(self, value):
        # Clear grid
        while child := self.grid.get_first_child():
            self.grid.remove(child)
            
        if not value:
            return
            
        data = {}
        if isinstance(value, str):
            try:
                data = json.loads(value)
            except Exception:
                return
        elif isinstance(value, dict):
            data = value
        
        if not data:
            return

        # Odoo 19 tax_totals structure:
        # {
        #   'subtotals': [
        #     {
        #       'name': 'Untaxed Amount',
        #       'base_amount_currency': 100.0,
        #       'tax_groups': [
        #         {'group_name': 'Taxes', 'tax_amount_currency': 15.0, ...}
        #       ]
        #     }
        #   ],
        #   'total_amount_currency': 115.0
        # }
        
        row = 0
        subtotals = data.get('subtotals', [])
        
        def format_val(val):
            if isinstance(val, (int, float)):
                return f"{val:,.2f}"
            return str(val)

        for sub in subtotals:
            # Subtotal label
            name_lbl = Gtk.Label(label=sub.get('name', 'Subtotal'), xalign=1)
            name_lbl.add_css_class('fw-bold')
            self.grid.attach(name_lbl, 0, row, 1, 1)
            
            # Subtotal amount
            amt = sub.get('base_amount_currency', 0.0)
            amt_lbl = Gtk.Label(label=format_val(amt), xalign=1)
            amt_lbl.add_css_class('fw-bold')
            self.grid.attach(amt_lbl, 1, row, 1, 1)
            row += 1
            
            # Taxes for this subtotal
            for group in sub.get('tax_groups', []):
                tax_name = Gtk.Label(label=group.get('group_name', 'Tax'), xalign=1)
                tax_name.add_css_class('text-muted')
                self.grid.attach(tax_name, 0, row, 1, 1)
                
                tax_amt = group.get('tax_amount_currency', 0.0)
                tax_val_lbl = Gtk.Label(label=format_val(tax_amt), xalign=1)
                self.grid.attach(tax_val_lbl, 1, row, 1, 1)
                row += 1

        # Final Total
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(8)
        sep.set_margin_bottom(8)
        self.grid.attach(sep, 0, row, 2, 1)
        row += 1
        
        total_lbl = Gtk.Label(label='Total', xalign=1)
        total_lbl.add_css_class('title-4')
        total_lbl.add_css_class('mb-0')
        self.grid.attach(total_lbl, 0, row, 1, 1)
        
        total_val_raw = data.get('total_amount_currency', 0.0)
        total_val_lbl = Gtk.Label(label=format_val(total_val_raw), xalign=1)
        total_val_lbl.add_css_class('title-4')
        total_val_lbl.add_css_class('mb-0')
        total_val_lbl.add_css_class('o_total_amount')
        self.grid.attach(total_val_lbl, 1, row, 1, 1)

    def get_value(self):
        return False
