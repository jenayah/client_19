# -*- coding: utf-8 -*-
# Odoo GTK 19 — XML Form Parser
# Inspired by E:\odoo-client-19\widget\view\form_gtk\parser.py (1028 lines)
# Rebuilt for GTK4/Adwaita with Odoo 19 support

import xml.etree.ElementTree as ET
from gi.repository import Gtk, Adw
from ui.widgets import create_field_widget
from core.expression import safe_eval


class FormParser:
    """Recursive XML parser that builds a GTK4 widget tree from Odoo form arch.
    
    This is the heart of the form rendering engine. It walks the XML tree
    and creates the appropriate GTK4 widgets for each node, inspired by the
    old parser_form.parse() method.
    """

    def __init__(self, view_fields, record_data=None, button_callback=None):
        """
        Args:
            view_fields: Dict from get_view → fields (field_name → field_info)
            record_data: Current record dict for expression evaluation
            button_callback: fn(btn_name, btn_type, btn_context) called when a
                             form button is clicked
        """
        self.view_fields = view_fields
        self.record = record_data or {}
        self.field_widgets = {}  # field_name → WidgetBase instance
        self.button_callback = button_callback

    def parse(self, arch_xml):
        """Parse the full arch XML string and return a GTK4 widget tree.
        
        Returns:
            Gtk.Widget — the root widget of the form
        """
        root = ET.fromstring(arch_xml)
        return self._parse_node(root)

    def _parse_node(self, node):
        """Recursively parse a single XML node and return a GTK widget."""
        tag = node.tag
        attrs = dict(node.attrib)

        # Check visibility
        invisible = attrs.get('invisible', '')
        if invisible and invisible not in ('0', 'False', 'false'):
            if invisible in ('1', 'True', 'true'):
                return None
            if safe_eval(invisible, self.record):
                return None

        # ── Structural tags ───────────────────────────────────────
        if tag == 'form':
            return self._parse_form(node, attrs)
        elif tag == 'header':
            return self._parse_header(node, attrs)
        elif tag == 'sheet':
            return self._parse_sheet(node, attrs)
        elif tag == 'group':
            return self._parse_group(node, attrs)
        elif tag == 'notebook':
            return self._parse_notebook(node, attrs)
        elif tag == 'page':
            return self._parse_page(node, attrs)
        elif tag == 'field':
            return self._parse_field(node, attrs)
        elif tag == 'button':
            return self._parse_button(node, attrs)
        elif tag == 'separator':
            return self._parse_separator(node, attrs)
        elif tag == 'label':
            return self._parse_label(node, attrs)
        elif tag == 'newline':
            return None  # Handled by group layout
        elif tag in ('div', 'span', 'main', 'aside', 'footer'):
            return self._parse_div(node, attrs, tag)
        elif tag == 'widget':
            return self._parse_widget_tag(node, attrs)
        elif tag in ('chatter',):
            return None  # Not rendered in GTK
        else:
            # Unknown tag: recurse into children
            return self._parse_container(node, attrs)

    def _parse_children(self, node, container):
        """Parse all children of a node and append them to a container."""
        for child in node:
            widget = self._parse_node(child)
            if widget:
                container.append(widget)

    def _parse_container(self, node, attrs):
        """Generic container for unknown tags."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._apply_classes(box, attrs)
        self._parse_children(node, box)
        if box.get_first_child() is None:
            return None
        return box

    # ── Form ──────────────────────────────────────────────────────
    def _parse_form(self, node, attrs):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.add_css_class('o_form_view')
        self._apply_classes(box, attrs)
        self._parse_children(node, box)
        return box

    # ── Header ────────────────────────────────────────────────────
    def _parse_header(self, node, attrs):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header.add_css_class('statusbar')
        header.set_margin_bottom(12)
        
        # Buttons go left, statusbar goes right
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        statusbar_widget = None

        for child in node:
            w = self._parse_node(child)
            if w is None:
                continue
            # Check if it's a statusbar (hexpand + halign END)
            child_attrs = dict(child.attrib)
            if child.tag == 'field' and child_attrs.get('widget') == 'statusbar':
                statusbar_widget = w
            else:
                btn_box.append(w)

        header.append(btn_box)
        if statusbar_widget:
            statusbar_widget.set_hexpand(True)
            statusbar_widget.set_halign(Gtk.Align.END)
            header.append(statusbar_widget)

        return header

    # ── Sheet ─────────────────────────────────────────────────────
    def _parse_sheet(self, node, attrs):
        sheet = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sheet.add_css_class('card')
        sheet.add_css_class('o_form_sheet')
        sheet.set_margin_start(12)
        sheet.set_margin_end(12)
        sheet.set_margin_top(12)
        sheet.set_margin_bottom(12)
        self._apply_classes(sheet, attrs)

        # First pass: separate avatar + button_box from rest
        avatar_widget = None
        button_box = None
        rest_children = []
        
        for child in node:
            child_attrs = dict(child.attrib)
            child_cls = child_attrs.get('class', '')
            
            # Avatar image (top-right)
            if child.tag == 'field' and 'oe_avatar' in child_cls:
                avatar_widget = self._parse_field(child, child_attrs)
                continue
            # Button box (top-right, above avatar or alone)
            if child.tag == 'div' and 'oe_button_box' in child_cls:
                button_box = self._parse_div(child, child_attrs, 'div')
                continue
            rest_children.append(child)

        # Build top row: button_box + avatar on the right
        if button_box or avatar_widget:
            top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            top_row.set_halign(Gtk.Align.END)
            top_row.set_hexpand(True)
            if button_box:
                top_row.append(button_box)
            if avatar_widget:
                top_row.append(avatar_widget)
            sheet.append(top_row)

        # Parse remaining children
        for child in rest_children:
            w = self._parse_node(child)
            if w:
                sheet.append(w)

        return sheet

    # ── Group (grid or column layout) ─────────────────────────────
    def _parse_group(self, node, attrs):
        """Parse a <group> tag.
        
        Odoo has two group patterns:
        1. OUTER group: contains inner <group> children → horizontal columns
        2. INNER group: contains <field> children → label:value grid
        """
        title = attrs.get('string', '')
        
        # Check if this group contains sub-groups (column layout)
        has_subgroups = any(child.tag == 'group' for child in node)
        
        if has_subgroups:
            return self._parse_group_columns(node, attrs, title)
        else:
            return self._parse_group_grid(node, attrs, title)

    def _parse_group_columns(self, node, attrs, title):
        """Outer <group> containing inner <group> children → max 2 columns grid."""
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._apply_classes(outer, attrs)
        
        if title:
            lbl = Gtk.Label(label=title, xalign=0)
            lbl.add_css_class('title-4')
            outer.append(lbl)
        
        # Use a Grid to allow wrapping after 2 columns
        grid = Gtk.Grid(column_spacing=24, row_spacing=16)
        grid.set_hexpand(True)
        
        col_idx = 0
        row_idx = 0
        max_cols = 2 # Standard Odoo column limit
        
        for child in node:
            child_attrs = dict(child.attrib)
            
            # Check visibility
            invisible = child_attrs.get('invisible', '')
            if invisible and invisible not in ('0', 'False', 'false'):
                if invisible in ('1', 'True', 'true'):
                    continue
                if safe_eval(invisible, self.record):
                    continue
            
            w = self._parse_node(child)
            if w:
                if child.tag == 'group':
                    w.set_hexpand(True)
                    w.set_valign(Gtk.Align.START)
                
                grid.attach(w, col_idx, row_idx, 1, 1)
                
                col_idx += 1
                if col_idx >= max_cols:
                    col_idx = 0
                    row_idx += 1
        
        outer.append(grid)
        return outer

    def _parse_group_grid(self, node, attrs, title):
        """Inner <group> with fields → label:value grid layout."""
        col = int(attrs.get('col', 2))
        
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        container.set_hexpand(True)
        self._apply_classes(container, attrs)
        
        if title:
            lbl = Gtk.Label(label=title, xalign=0)
            lbl.add_css_class('title-4')
            lbl.set_margin_bottom(4)
            container.append(lbl)
        
        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(16)
        grid.add_css_class('o_inner_group')
        # Labels should be aligned to the right, fields to the left
        container.append(grid)
        
        self._fill_grid(node, grid, col)
        return container

    def _fill_grid(self, node, grid, max_col):
        """Fill a Gtk.Grid with children, respecting col/colspan like the old parser."""
        x, y = 0, 0
        for child in node:
            child_attrs = dict(child.attrib)
            
            # Check visibility
            invisible = child_attrs.get('invisible', '')
            if invisible and invisible not in ('0', 'False', 'false'):
                if invisible in ('1', 'True', 'true'):
                    continue
                if safe_eval(invisible, self.record):
                    continue

            colspan = int(child_attrs.get('colspan', 1))
            if child.tag == 'newline':
                x, y = 0, y + 1
                continue

            if child.tag == 'field':
                fname = child_attrs.get('name', '')
                nolabel = child_attrs.get('nolabel', '0') == '1'
                f_info = self.view_fields.get(fname, {})
                
                # In Odoo, a field normally takes 2 grid columns (1 for label, 1 for widget)
                # unless nolabel=1 or it takes the full width.
                effective_colspan = colspan if nolabel else colspan + 1
                
                if x + effective_colspan > max_col:
                    x, y = 0, y + 1
                
                if not nolabel:
                    # Add label
                    label_text = child_attrs.get('string', f_info.get('string', fname))
                    if label_text:
                        label_text += ' :'
                    label = Gtk.Label(label=label_text or '', xalign=1)
                    label.add_css_class('o_form_label')
                    label.set_valign(Gtk.Align.CENTER)
                    label.set_margin_end(4)
                    grid.attach(label, x, y, 1, 1)
                    
                    # Add field widget
                    widget = self._parse_field(child, child_attrs)
                    if widget:
                        widget.set_hexpand(True)
                        grid.attach(widget, x + 1, y, colspan, 1)
                else:
                    # No label, just attach widget at current x
                    widget = self._parse_field(child, child_attrs)
                    if widget:
                        widget.set_hexpand(True)
                        grid.attach(widget, x, y, effective_colspan, 1)
                
                x += effective_colspan
            elif child.tag == 'group':
                if x > 0: x, y = 0, y + 1
                widget = self._parse_node(child)
                if widget:
                    widget.set_hexpand(True)
                    grid.attach(widget, x, y, max_col, 1)
                x = 0
                y += 1
            elif child.tag == 'div':
                if x + colspan > max_col: x, y = 0, y + 1
                widget = self._parse_node(child)
                if widget:
                    widget.set_hexpand(True)
                    grid.attach(widget, x, y, colspan, 1)
                x += colspan
            else:
                if x + colspan > max_col: x, y = 0, y + 1
                widget = self._parse_node(child)
                if widget:
                    grid.attach(widget, x, y, colspan, 1)
                x += colspan

            if x >= max_col:
                x, y = 0, y + 1

    # ── Notebook ──────────────────────────────────────────────────
    def _parse_notebook(self, node, attrs):
        nb = Gtk.Notebook()
        nb.set_margin_top(12)
        self._apply_classes(nb, attrs)
        
        for child in node:
            if child.tag == 'page':
                page_attrs = dict(child.attrib)
                
                # Check visibility
                invisible = page_attrs.get('invisible', '')
                if invisible and invisible not in ('0', 'False', 'false'):
                    if invisible in ('1', 'True', 'true'):
                        continue
                    if safe_eval(invisible, self.record):
                        continue
                
                title = page_attrs.get('string', 'Tab')
                page_widget = self._parse_page(child, page_attrs)
                if page_widget:
                    label = Gtk.Label(label=title)
                    nb.append_page(page_widget, label)
        return nb

    def _parse_page(self, node, attrs):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_bottom(12)
        self._apply_classes(box, attrs)
        self._parse_children(node, box)
        return box

    # ── Field ─────────────────────────────────────────────────────
    def _parse_field(self, node, attrs):
        fname = attrs.get('name', '')
        if not fname:
            return None

        f_info = dict(self.view_fields.get(fname, {}))
        if not f_info:
            return None

        # Merge XML attrs into field_info
        for k in ('widget', 'domain', 'context', 'options', 'class',
                   'placeholder', 'password', 'nolabel', 'string'):
            if k in attrs:
                f_info[k] = attrs[k]

        # Extract nested views (for X2many)
        nested_views = {}
        for child in node:
            if child.tag in ('tree', 'list', 'form', 'kanban'):
                import xml.etree.ElementTree as ET
                nested_views[child.tag] = ET.tostring(child, encoding='unicode')

        # Get current value
        value = self.record.get(fname)

        # Create widget instance
        wid = create_field_widget(fname, f_info, attrs, self.record)
        
        # Pass nested views to widget if applicable
        if hasattr(wid, 'set_nested_views'):
            wid.set_nested_views(nested_views)

        # Set value
        try:
            wid.set_value(value)
        except Exception as e:
            print(f"Error setting value for {fname}: {e}")

        # Set readonly
        readonly = attrs.get('readonly', '')
        if readonly and readonly not in ('0', 'False', 'false'):
            if readonly in ('1', 'True', 'true'):
                wid.set_readonly(True)
            elif safe_eval(readonly, self.record):
                wid.set_readonly(True)

        self.field_widgets[fname] = wid
        return wid.widget

    # ── Button ────────────────────────────────────────────────────
    def _parse_button(self, node, attrs):
        label = attrs.get('string', '')
        icon = attrs.get('icon', '')
        btn_name = attrs.get('name', '')
        btn_type = attrs.get('type', 'object')  # 'object' or 'action'
        
        btn = Gtk.Button(label=label)
        if icon:
            # Map FontAwesome to GTK icons
            icon_map = {
                'fa-pencil': 'document-edit-symbolic',
                'fa-trash': 'user-trash-symbolic',
                'fa-print': 'printer-symbolic',
                'fa-envelope': 'mail-send-symbolic',
                'fa-check': 'object-select-symbolic',
                'fa-times': 'window-close-symbolic',
                'fa-refresh': 'view-refresh-symbolic',
                'fa-send': 'mail-send-symbolic',
                'fa-download': 'document-save-symbolic',
                'fa-upload': 'document-open-symbolic',
                'fa-copy': 'edit-copy-symbolic',
                'fa-eye': 'view-reveal-symbolic',
                'fa-ban': 'action-unavailable-symbolic',
                'fa-undo': 'edit-undo-symbolic',
            }
            gtk_icon = icon_map.get(icon, 'application-x-executable-symbolic')
            btn.set_icon_name(gtk_icon)

        btn_class = attrs.get('class', '')
        if 'oe_stat_button' in btn_class:
            btn.add_css_class('oe_stat_button')
        elif 'btn-primary' in btn_class:
            btn.add_css_class('suggested-action')
        elif 'btn-secondary' in btn_class:
            btn.add_css_class('flat')

        self._apply_classes(btn, attrs)
        
        # Handle visibility
        invisible = attrs.get('invisible', '')
        if invisible and invisible not in ('0', 'False', 'false'):
            if invisible in ('1', 'True', 'true'):
                return None
            if safe_eval(invisible, self.record):
                return None

        # Connect click signal to the callback
        if btn_name and self.button_callback:
            # Parse optional context from button
            import ast
            btn_ctx = None
            ctx_str = attrs.get('context', '')
            if ctx_str:
                try:
                    btn_ctx = ast.literal_eval(ctx_str)
                except Exception:
                    pass
            btn.connect('clicked', lambda b, n=btn_name, t=btn_type, c=btn_ctx:
                        self.button_callback(n, t, c))
            if label:
                btn.set_tooltip_text(f"{label} ({btn_type}: {btn_name})")
        
        # Parse children (stat buttons often contain field + text)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        has_children = False
        for child in node:
            w = self._parse_node(child)
            if w:
                inner.append(w)
                has_children = True
        
        if has_children:
            btn.set_child(inner)
        
        return btn

    # ── Separator ─────────────────────────────────────────────────
    def _parse_separator(self, node, attrs):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title = attrs.get('string', '')
        if title:
            label = Gtk.Label(label=title, xalign=0)
            label.add_css_class('title-4')
            box.append(label)
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        box.append(sep)
        return box

    # ── Label ─────────────────────────────────────────────────────
    def _parse_label(self, node, attrs):
        text = attrs.get('string', '')
        for_field = attrs.get('for', '')
        
        if not text and for_field:
            f_info = self.view_fields.get(for_field, {})
            text = f_info.get('string', for_field)
        
        if not text:
            return None
        
        label = Gtk.Label(label=text, xalign=0)
        label.add_css_class('o_form_label')
        self._apply_classes(label, attrs)
        return label

    # ── Div / Span ────────────────────────────────────────────────
    def _parse_div(self, node, attrs, tag='div'):
        cls = attrs.get('class', '')
        orient = Gtk.Orientation.VERTICAL
        spacing = 4

        # Detect horizontal layouts
        if 'o_row' in cls:
            orient = Gtk.Orientation.HORIZONTAL
            spacing = 6
        elif 'd-flex' in cls and 'flex-column' not in cls:
            orient = Gtk.Orientation.HORIZONTAL
        elif 'flex-row' in cls:
            orient = Gtk.Orientation.HORIZONTAL
        elif tag in ('main', 'aside'):
            orient = Gtk.Orientation.VERTICAL if tag == 'main' else Gtk.Orientation.HORIZONTAL
        
        if 'gap-3' in cls: spacing = 12
        elif 'gap-2' in cls: spacing = 8
        elif 'gap-1' in cls: spacing = 4

        box = Gtk.Box(orientation=orient, spacing=spacing)
        self._apply_classes(box, attrs)

        # Special class handling
        if 'oe_button_box' in cls:
            box.set_halign(Gtk.Align.END)
            box.set_hexpand(True)
            box.set_orientation(Gtk.Orientation.HORIZONTAL)
            box.set_spacing(6)
        
        if 'oe_title' in cls:
            box.set_hexpand(True)

        if 'flex-grow-1' in cls:
            box.set_hexpand(True)

        # Text content
        if node.text and node.text.strip():
            text_label = Gtk.Label(label=node.text.strip(), xalign=0)
            text_label.set_wrap(True)
            box.append(text_label)

        self._parse_children(node, box)

        # Tail text (text after closing child tags)
        for child in node:
            if child.tail and child.tail.strip():
                tail_label = Gtk.Label(label=child.tail.strip(), xalign=0)
                box.append(tail_label)

        return box

    # ── Widget tag ────────────────────────────────────────────────
    def _parse_widget_tag(self, node, attrs):
        """Handle <widget name="xxx"/> tags"""
        return None  # Most widget tags are server-side only

    # ── Utilities ─────────────────────────────────────────────────
    def _apply_classes(self, widget, attrs):
        """Apply all CSS classes from the XML to the GTK widget."""
        cls = attrs.get('class', '')
        if cls:
            for c in cls.split():
                widget.add_css_class(c)

    def update_record(self, record_data):
        """Update the record data and refresh all field widgets."""
        self.record = record_data
        for fname, wid in self.field_widgets.items():
            val = record_data.get(fname)
            wid.record = record_data
            try:
                wid.set_value(val)
            except Exception as e:
                print(f"Error updating {fname}: {e}")
