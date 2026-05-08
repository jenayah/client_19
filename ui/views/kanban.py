# -*- coding: utf-8 -*-
# Odoo GTK 19 — Kanban View (Refactored)
# Supports Odoo 19 templates: kanban-box AND card

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject
from core import Model, session
from core.expression import safe_eval
from ui.widgets.binary import ImageWidget
from ui.widgets.base import WidgetBase
import xml.etree.ElementTree as ET


class KanbanView(Gtk.Box):
    __gsignals__ = {
        'record-activated': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    def __init__(self, model_name, view_id=None, domain=None, context=None, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        self.model_name = model_name
        self.model = Model(model_name)
        self.view_id = view_id
        self.domain = domain or []
        self.context = context or {}
        self.view_arch = None
        self.view_fields = {}
        self.kanban_fields = []  # Fields needed for data loading
        self.kanban_template = None  # The <t t-name="card"> or <t t-name="kanban-box">

        self._load_view_arch()
        self._setup_kanban()
        self.load_data()

    def _load_view_arch(self):
        try:
            res = session.client.get_view(self.model_name, view_id=self.view_id, view_type='kanban')
            self.view_arch = res.get('arch', '<kanban/>')
            self.view_fields = res.get('fields', {})
            print(f"DEBUG: get_view for {self.model_name} (kanban)")

            # Fetch full field defs
            try:
                all_fields = session.client.call_kw(
                    self.model_name, 'fields_get', [],
                    {'attributes': ['type', 'string', 'relation', 'selection', 'digits']})
                print(f"DEBUG: fetching field definitions for {self.model_name}...")
                for fname, finfo in all_fields.items():
                    if fname in self.view_fields:
                        merged = dict(finfo)
                        merged.update(self.view_fields[fname])
                        self.view_fields[fname] = merged
            except Exception:
                pass

            # Parse the kanban arch
            root = ET.fromstring(self.view_arch)
            
            # Collect all field names mentioned in the arch
            for f in root.iter('field'):
                fname = f.get('name', '')
                if fname and fname not in self.kanban_fields:
                    self.kanban_fields.append(fname)

            # Find the template node
            templates = root.find('templates')
            if templates is not None:
                # Try standard names
                for t in templates.findall('t'):
                    tname = t.get('t-name', '')
                    if tname in ('kanban-box', 'kanban-card', 'card'):
                        self.kanban_template = t
                        break
                # Fallback to first t if no standard name found
                if self.kanban_template is None:
                    all_ts = templates.findall('t')
                    if all_ts:
                        self.kanban_template = all_ts[0]

        except Exception as e:
            print(f"Erreur arch Kanban {self.model_name}: {e}")

    def _setup_kanban(self):
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_vexpand(True)
        
        self.flow_box = Gtk.FlowBox()
        self.flow_box.set_homogeneous(False)
        self.flow_box.set_max_children_per_line(4)
        self.flow_box.set_min_children_per_line(1)
        self.flow_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flow_box.set_column_spacing(12)
        self.flow_box.set_row_spacing(12)
        self.flow_box.set_margin_start(12)
        self.flow_box.set_margin_end(12)
        self.flow_box.set_margin_top(12)
        self.flow_box.set_margin_bottom(12)
        self.flow_box.set_valign(Gtk.Align.START)

        self.scroll.set_child(self.flow_box)
        self.append(self.scroll)

    def load_data(self):
        # Only request known valid fields
        valid_fields = [f for f in self.kanban_fields 
                        if f in self.view_fields]
        if 'id' not in valid_fields:
            valid_fields.append('id')
        if 'display_name' not in valid_fields:
            valid_fields.append('display_name')

        try:
            records = self.model.search_read(
                domain=self.domain, fields=valid_fields, limit=40,
                context=self.context)
            
            # Pre-fetch M2M names if necessary
            self._fetch_m2m_names(records)
            
            self._render_cards(records)
        except Exception as e:
            print(f"Erreur données Kanban {self.model_name}: {e}")
            # Retry with minimal fields
            try:
                records = self.model.search_read(
                    domain=[], fields=['id', 'display_name'], limit=40)
                self._render_cards(records)
            except Exception as e2:
                print(f"Retry Kanban failed: {e2}")

    def _fetch_m2m_names(self, records):
        """Fetch display names for many2many fields that only returned IDs."""
        m2m_fields = []
        for fname, finfo in self.view_fields.items():
            if finfo.get('type') == 'many2many' and fname in self.kanban_fields:
                m2m_fields.append((fname, finfo.get('relation')))
        
        if not m2m_fields or not records:
            return
            
        for fname, relation in m2m_fields:
            if not relation: continue
            
            # Collect all IDs
            all_ids = set()
            for rec in records:
                val = rec.get(fname)
                if isinstance(val, list):
                    for v in val:
                        if isinstance(v, int):
                            all_ids.add(v)
            
            if not all_ids: continue
            
            try:
                # Fetch names
                res = session.client.call_kw(relation, 'search_read', [], {
                    'domain': [('id', 'in', list(all_ids))],
                    'fields': ['display_name']
                })
                name_map = {r['id']: r.get('display_name', 'Unknown') for r in res}
                
                # Replace in records
                for rec in records:
                    val = rec.get(fname)
                    if isinstance(val, list):
                        new_val = []
                        for v in val:
                            if isinstance(v, int) and v in name_map:
                                new_val.append([v, name_map[v]])
                            else:
                                new_val.append(v)
                        rec[fname] = new_val
            except Exception as e:
                print(f"Warning: Could not fetch M2M names for {relation}: {e}")

    def _render_cards(self, records):
        # Clear
        while child := self.flow_box.get_first_child():
            self.flow_box.remove(child)

        for rec in records:
            card = self._build_card(rec)
            if card:
                # Wrap card in a clickable container
                rec_id = rec.get('id')
                if rec_id:
                    gesture = Gtk.GestureClick.new()
                    gesture.set_button(1)
                    gesture.connect('released', self._on_card_clicked, rec_id)
                    card.add_controller(gesture)
                    card.set_cursor_from_name('pointer')
                self.flow_box.append(card)

    def _on_card_clicked(self, gesture, n_press, x, y, rec_id):
        """Open the record in form view when a kanban card is clicked."""
        self.emit('record-activated', rec_id)

    def _build_card(self, data):
        """Build a single kanban card from a record."""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card.add_css_class('card')
        card.add_css_class('o_kanban_record')
        card.set_size_request(260, -1)
        card.set_valign(Gtk.Align.START)

        if self.kanban_template is not None:
            # Use the template to build the card
            t_class = self.kanban_template.get('class', self.kanban_template.get('t-attf-class', ''))
            # Support Bootstrap grid 'row' or 'd-flex' at root
            if 'flex-row' in t_class or 'row' in t_class or ('d-flex' in t_class and 'flex-column' not in t_class):
                card.set_orientation(Gtk.Orientation.HORIZONTAL)
                card.set_spacing(8)

            for child in self.kanban_template:
                widget = self._render_node(child, data)
                if widget:
                    c_cls = child.get('class', child.get('t-attf-class', ''))
                    # Handle col-* expansion
                    if 'col-' in c_cls or 'ms-auto' in c_cls or 'float-end' in c_cls or 'o_kanban_aside_full' in c_cls:
                        widget.set_hexpand(True)
                        if 'float-end' in c_cls or 'ms-auto' in c_cls:
                            widget.set_halign(Gtk.Align.END)

                    card.append(widget)
        else:
            # Fallback: simple field listing
            name = data.get('display_name', data.get('name', ''))
            if name:
                label = Gtk.Label(label=str(name), xalign=0)
                label.add_css_class('heading')
                label.set_wrap(True)
                label.set_max_width_chars(30)
                card.append(label)

        return card

    def _render_node(self, node, data):
        """Recursively render a single template node."""
        tag = node.tag
        attrs = dict(node.attrib)

        # Handle t-if
        t_if = attrs.get('t-if', '')
        if t_if:
            # Build evaluation context: record.field.value style
            eval_ctx = dict(data)
            # Odoo QWeb uses record.field.value
            class _FieldProxy:
                def __init__(self, val):
                    self.value = val
                    self.raw_value = val
                def __bool__(self):
                    return bool(self.value)
            
            record_proxy = type('RecordProxy', (), {})()
            for fname, fval in data.items():
                setattr(record_proxy, fname, _FieldProxy(fval))
            eval_ctx['record'] = record_proxy
            
            try:
                if not safe_eval(t_if, eval_ctx):
                    return None
            except Exception:
                pass  # If eval fails, show anyway

        # ── Container tags ────────────────────────────────────────
        container_tags = ('div', 'span', 'main', 'aside', 'strong', 'a', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'li', 'section', 'header', 'footer', 'i', 'b', 'u')
        
        if tag in container_tags:
            cls = attrs.get('class', attrs.get('t-attf-class', ''))
            
            # Icon handling (FA to GTK)
            if tag == 'i' or 'fa' in cls:
                icon_name = 'image-missing-symbolic'
                for c in cls.split():
                    if c.startswith('fa-'):
                        fa_map = {
                            'fa-envelope': 'mail-message-new-symbolic',
                            'fa-phone': 'call-start-symbolic',
                            'fa-map-marker': 'mark-location-symbolic',
                            'fa-pencil-square-o': 'document-edit-symbolic',
                            'fa-usd': 'money-symbolic',
                            'fa-clock-o': 'alarm-symbolic',
                            'fa-suitcase': 'work-symbolic',
                            'fa-user': 'avatar-default-symbolic',
                            'fa-star': 'starred-symbolic'
                        }
                        icon_name = fa_map.get(c, icon_name)
                img = Gtk.Image.new_from_icon_name(icon_name)
                img.set_pixel_size(14)
                if 'text-primary' in cls: img.add_css_class('accent-icon')
                return img

            # Default orientation
            orient = Gtk.Orientation.VERTICAL
            
            # Inline tags or explicit flex should be horizontal
            inline_tags = ('span', 'strong', 'a', 'i', 'b', 'u')
            is_flex = 'd-flex' in cls or 'row' in cls or 'o_kanban_record_top' in cls or 'o_kanban_record_bottom' in cls or tag == 'footer'
            
            if tag in inline_tags or (is_flex and 'flex-column' not in cls) or 'flex-row' in cls:
                orient = Gtk.Orientation.HORIZONTAL
            
            spacing = 0
            if orient == Gtk.Orientation.HORIZONTAL:
                spacing = 4
            
            box = Gtk.Box(orientation=orient, spacing=spacing)
            if cls:
                for c in cls.split():
                    box.add_css_class(c)
                
                if 'justify-content-between' in cls or 'o_kanban_record_top' in cls:
                    pass

            # Text before children
            if node.text and node.text.strip():
                text = node.text.strip()
                lbl = Gtk.Label(label=text, xalign=0)
                lbl.set_wrap(True)
                if tag == 'strong' or 'fw-bold' in cls or 'fw-bolder' in cls or 'o_kanban_record_title' in cls:
                    lbl.add_css_class('fw-bold')
                
                # Apply fs-* classes
                for c in cls.split():
                    if c.startswith('fs-'):
                        lbl.add_css_class(c)
                
                if tag.startswith('h') and len(tag) == 2:
                    lbl.add_css_class('heading')
                if 'text-muted' in cls:
                    lbl.add_css_class('dim-label')
                box.append(lbl)

            for child in node:
                widget = self._render_node(child, data)
                if widget:
                    c_cls = child.get('class', child.get('t-attf-class', ''))
                    if 'float-end' in c_cls or 'ms-auto' in c_cls or 'col-2' in c_cls:
                        widget.set_hexpand(True)
                        widget.set_halign(Gtk.Align.END)
                    
                    if 'col-' in c_cls:
                        widget.set_hexpand(True)

                    box.append(widget)
                
                # Tail text
                if child.tail and child.tail.strip():
                    tail = Gtk.Label(label=child.tail.strip(), xalign=0)
                    if 'text-muted' in cls:
                        tail.add_css_class('dim-label')
                    box.append(tail)

            if box.get_first_child() is None:
                return None
            return box

        # ── Field ─────────────────────────────────────────────────
        elif tag == 'field':
            fname = attrs.get('name', '')
            val = data.get(fname)
            widget_attr = attrs.get('widget', '')
            f_info = self.view_fields.get(fname, {})
            f_type = f_info.get('type', 'char')
            cls = attrs.get('class', attrs.get('t-attf-class', ''))

            # Image fields
            if widget_attr == 'image' or f_type == 'binary':
                if val and isinstance(val, str) and len(val) > 100:
                    return ImageWidget.create_from_base64(val, size=64)
                return None

            # Boolean favorite
            if widget_attr == 'boolean_favorite':
                img = Gtk.Image.new_from_icon_name(
                    'starred-symbolic' if val else 'non-starred-symbolic')
                return img

            # Many2many tags in kanban
            if widget_attr == 'many2many_tags':
                if isinstance(val, list) and val:
                    tags_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
                    tags_box.add_css_class('flex-wrap')
                    for v in val[:8]: # Show more tags
                        tag_id = v[0] if isinstance(v, (list, tuple)) else v
                        name = str(v[1]) if isinstance(v, (list, tuple)) and len(v) > 1 else str(v)
                        tag_lbl = Gtk.Label(label=name)
                        tag_lbl.add_css_class('badge')
                        
                        # Apply a deterministic color based on ID (1 to 10)
                        color_idx = (int(tag_id) % 10) + 1
                        tag_lbl.add_css_class(f'o_tag_color_{color_idx}')
                        
                        tags_box.append(tag_lbl)
                    return tags_box
                return None

            # Render statistics badges (Invoices, Sales, etc.)
            if widget_attr in ('contact_statistics', 'application_statistics') and val:
                try:
                    stats = val if isinstance(val, list) else safe_eval(str(val))
                    if stats and isinstance(stats, list):
                        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                        for s in stats:
                            badge = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
                            badge.add_css_class('badge')
                            if 'tagClass' in s: badge.add_css_class(s['tagClass'])
                            
                            icon_name = 'image-missing-symbolic'
                            fa_cls = s.get('iconClass', '')
                            if fa_cls:
                                fa_map = {
                                    'fa-pencil-square-o': 'document-edit-symbolic', 
                                    'fa-usd': 'money-symbolic',
                                    'fa-shopping-cart': 'emblem-package-symbolic'
                                }
                                icon_name = fa_map.get(fa_cls, icon_name)
                            
                            img = Gtk.Image.new_from_icon_name(icon_name)
                            img.set_pixel_size(12)
                            badge.append(img)
                            badge.append(Gtk.Label(label=str(s.get('value', 0))))
                            box.append(badge)
                        return box
                except Exception:
                    pass
                return None

            # Hide complex JSON fields for now
            if widget_attr in ('properties', 'kanban_button'):
                return None

            # Label Selection / Selection Badge
            if widget_attr in ('label_selection', 'selection_badge', 'state_selection'):
                if val:
                    label_text = val
                    if isinstance(val, (list, tuple)) and len(val) > 1:
                        label_text = val[1]
                    
                    lbl = Gtk.Label(label=str(label_text))
                    lbl.add_css_class('badge')
                    
                    # Try to map status to color via options
                    try:
                        options = safe_eval(attrs.get('options', '{}'))
                        classes = options.get('classes', {})
                        raw_val = val[0] if isinstance(val, (list, tuple)) else val
                        if raw_val in classes:
                            lbl.add_css_class(f'badge-{classes[raw_val]}')
                    except Exception:
                        pass
                    return lbl
                return None

            # Monetary
            if widget_attr == 'monetary' and val is not None and val is not False:
                currency = ""
                if 'currency_id' in data and isinstance(data['currency_id'], (list, tuple)):
                    currency = data['currency_id'][1]
                
                text = f'{float(val):,.2f}'
                if currency:
                    # Handle currency positioning (symbol)
                    text = f'{currency} {text}' if len(currency) <= 3 else f'{text} {currency}'
                
                lbl = Gtk.Label(label=text, xalign=1)
                lbl.add_css_class('fw-bold')
                if 'fs-5' in cls: lbl.add_css_class('h5')
                return lbl

            # Default: text label
            if val is not False and val is not None:
                text = ''
                if isinstance(val, (list, tuple)) and len(val) > 1:
                    text = str(val[1])
                elif isinstance(val, str):
                    if len(val) > 200:
                        return None
                    text = val
                else:
                    text = str(val)

                if not text:
                    return None
                lbl = Gtk.Label(label=text, xalign=0)
                lbl.set_wrap(True)
                lbl.set_max_width_chars(30)
                
                if 'fw-bold' in cls or 'fw-bolder' in cls or 'o_kanban_record_title' in cls:
                    lbl.add_css_class('fw-bold')
                if 'text-muted' in cls:
                    lbl.add_css_class('dim-label')
                
                for c in cls.split():
                    if c.startswith('fs-'):
                        lbl.add_css_class(c)
                    else:
                        lbl.add_css_class(c)
                return lbl

            return None

        # ── t tag (QWeb control) ──────────────────────────────────
        elif tag == 't':
            if 't-call' in attrs:
                return None
                
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            if node.text and node.text.strip():
                box.append(Gtk.Label(label=node.text.strip(), xalign=0))
            for child in node:
                widget = self._render_node(child, data)
                if widget:
                    box.append(widget)
                if child.tail and child.tail.strip():
                    box.append(Gtk.Label(label=child.tail.strip(), xalign=0))
            if box.get_first_child() is None:
                return None
            return box

        # ── img tag ───────────────────────────────────────────────
        elif tag == 'img':
            # Try kanban_image pattern
            t_att_src = attrs.get('t-att-src', '')
            if 'kanban_image' in t_att_src:
                # Extract field name from kanban_image(model, field, id)
                try:
                    parts = t_att_src.split("'")
                    if len(parts) >= 4:
                        img_field = parts[3]
                        val = data.get(img_field)
                        if val:
                            return ImageWidget.create_from_base64(val, size=48)
                except Exception:
                    pass
            return None

        # ── progressbar ───────────────────────────────────────────
        elif tag == 'progressbar':
            return None  # TODO

        # ── Fallback for unknown tags (treat as generic box) ──────
        else:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            for child in node:
                w = self._render_node(child, data)
                if w: box.append(w)
            return box if box.get_first_child() else None
