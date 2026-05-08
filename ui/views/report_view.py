# -*- coding: utf-8 -*-
from gi.repository import Gtk, Pango, Gdk
from core import session

class ReportView(Gtk.Box):
    def __init__(self, model_name, res_id, report_name):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_vexpand(True)
        self.set_hexpand(True)
        
        # Scrolled window to handle long reports
        self.scroll = Gtk.ScrolledWindow()
        self.append(self.scroll)
        
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=25)
        self.content_box.set_margin_start(50)
        self.content_box.set_margin_end(50)
        self.content_box.set_margin_top(40)
        self.content_box.set_margin_bottom(40)
        self.content_box.add_css_class('report-paper')
        self.scroll.set_child(self.content_box)

        self.model_name = model_name
        self.res_id = res_id
        
        self._load_and_render()

    def _load_and_render(self):
        try:
            fields = ['name', 'partner_id', 'date_order', 'amount_total', 'amount_untaxed', 'amount_tax', 'currency_id', 'user_id', 'validity_date']
            if self.model_name == 'sale.order':
                fields.append('order_line')
            
            data = session.client.call_kw(self.model_name, 'read', [[self.res_id]], {'fields': fields})[0]
            
            # 1. TOP HEADER (Logo placeholder and Title)
            header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            self.content_box.append(header_box)
            
            partner_name = data.get('partner_id', [0, ''])[1]
            p_label = Gtk.Label(label=partner_name, xalign=0)
            p_label.add_css_class('report-partner-name')
            header_box.append(p_label)
            
            spacer = Gtk.Box(hexpand=True)
            header_box.append(spacer)
            
            title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            title_label = Gtk.Label(xalign=1)
            title_label.set_markup(f"<span color='#5D4373' size='28000'>Devis # {data.get('name', '')}</span>")
            title_box.append(title_label)
            header_box.append(title_box)

            # 2. INFO BOX (Rounded Grey Box)
            info_frame = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            info_frame.add_css_class('report-info-frame')
            self.content_box.append(info_frame)
            
            # Columns
            date_val = data.get('date_order', '').split(' ')[0]
            validity = data.get('validity_date', '') or 'N/A'
            vendeur = data.get('user_id', [0, 'Administrator'])[1]
            
            info_frame.append(self._create_info_col("Date du devis", date_val, expand=True))
            info_frame.append(self._create_info_col("Expiration", validity, expand=True))
            info_frame.append(self._create_info_col("Vendeur", vendeur, expand=True, last=True))

            # 3. LINES TABLE
            if 'order_line' in data:
                self._render_table(data['order_line'])
            
            # 4. TOTALS
            totals_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            self.content_box.append(totals_container)
            totals_container.append(Gtk.Box(hexpand=True))
            
            totals_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            totals_box.add_css_class('report-totals-box')
            totals_container.append(totals_box)
            
            curr = data.get('currency_id', [0, 'TND'])[1]
            totals_box.append(self._create_total_row("Total", data.get('amount_total', 0), curr))

        except Exception as e:
            self.content_box.append(Gtk.Label(label=f"Erreur: {e}"))

    def _create_info_col(self, title, value, expand=False, last=False):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, hexpand=expand)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(15)
        if not last:
            box.add_css_class('report-info-col-sep')
        
        t = Gtk.Label(label=title, xalign=0)
        t.add_css_class('report-info-title')
        v = Gtk.Label(label=str(value), xalign=0)
        v.add_css_class('report-info-value')
        box.append(t)
        box.append(v)
        return box

    def _render_table(self, line_ids):
        lines = session.client.call_kw('sale.order.line', 'read', [line_ids], 
                                     {'fields': ['name', 'product_uom_qty', 'price_unit', 'price_subtotal', 'product_uom']})
        
        table_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        table_box.add_css_class('report-table')
        self.content_box.append(table_box)
        
        # Header Row
        h_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        h_row.add_css_class('report-table-header')
        table_box.append(h_row)
        
        h_row.append(self._table_cell("DESCRIPTION", hexpand=True))
        h_row.append(self._table_cell("QUANTITÉ", width=120))
        h_row.append(self._table_cell("PRIX UNITAIRE", width=120))
        h_row.append(self._table_cell("MONTANT", width=120))
        
        # Data Rows
        for line in lines:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            row.add_css_class('report-table-row')
            table_box.append(row)
            
            uom = line.get('product_uom', [0, 'Unité(s)'])[1]
            qty_str = f"{line.get('product_uom_qty', 0):.2f} {uom}"
            
            row.append(self._table_cell(line.get('name', ''), hexpand=True, align=0))
            row.append(self._table_cell(qty_str, width=120))
            row.append(self._table_cell(f"{line.get('price_unit', 0):.2f}", width=120))
            row.append(self._table_cell(f"{line.get('price_subtotal', 0):.2f}", width=120))

    def _table_cell(self, text, hexpand=False, width=-1, align=0.5):
        l = Gtk.Label(label=text, xalign=align, hexpand=hexpand)
        if width > 0:
            l.set_size_request(width, -1)
        l.add_css_class('report-cell')
        return l

    def _create_total_row(self, label, value, currency):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.add_css_class('report-total-row')
        l = Gtk.Label(label=label, xalign=0, hexpand=True)
        l.set_margin_start(20)
        v = Gtk.Label(label=f"{value:,.3f} {currency}", xalign=1)
        v.set_margin_end(20)
        box.append(l)
        box.append(v)
        return box

