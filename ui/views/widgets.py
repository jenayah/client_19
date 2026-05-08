from gi.repository import Gtk, Adw, Pango, GObject

class WidgetFactory:
    @staticmethod
    def create_widget(field_info, value, record=None, editable=False):
        field_type = field_info.get('type', 'char')
        widget_type = field_info.get('widget')
        decorations = field_info.get('decorations', {})
        
        widget = None
        
        if field_type == 'boolean':
            widget = WidgetFactory._create_boolean(value, editable)
        elif field_type == 'integer':
            widget = WidgetFactory._create_integer(value, editable)
        elif field_type == 'float':
            widget = WidgetFactory._create_float(value, editable)
        elif widget_type == 'image' or field_type == 'binary':
            size = 128 if editable else 32
            widget = WidgetFactory._create_image(value, size=size)
        elif widget_type == 'badge':
            widget = WidgetFactory._create_badge(value, record, decorations)
        elif widget_type == 'radio':
            widget = WidgetFactory._create_radio(value, field_info, editable)
        elif widget_type == 'many2many_tags':
            widget = WidgetFactory._create_m2m_tags(value)
        elif widget_type == 'statusbar':
            widget = WidgetFactory._create_statusbar(value, field_info, editable)
        elif widget_type == 'boolean_toggle':
            widget = WidgetFactory._create_boolean_toggle(value, editable)
        elif field_type == 'char' and isinstance(value, str) and value.startswith('[') and value.endswith(']'):
            # Potentially a JSON stat list
            widget = WidgetFactory._create_json_stats(value)
        elif field_type == 'many2one':
            widget = WidgetFactory._create_m2o(value, editable)
        elif field_type in ('one2many', 'many2many'):
            widget = WidgetFactory._create_x2m(value)
        else:
            widget = WidgetFactory._create_char(value, editable)
            
        # Apply decorations if not already handled
        if widget and record and decorations and widget_type != 'badge':
            WidgetFactory._apply_decorations(widget, record, decorations)
            
        return widget

    @staticmethod
    def _apply_decorations(widget, record, decorations):
        # Map decoration names to colors
        color_map = {
            'decoration-info': '#0dcaf0',
            'decoration-success': '#198754',
            'decoration-danger': '#dc3545',
            'decoration-warning': '#ffc107',
            'decoration-muted': '#6c757d',
            'decoration-bf': 'bold',
            'decoration-it': 'italic'
        }
        
        for deco, expr in decorations.items():
            try:
                # Simple evaluation
                safe_eval_ctx = record.copy()
                if eval(expr, {"__builtins__": {}}, safe_eval_ctx):
                    color = color_map.get(deco)
                    if color:
                        if color == 'bold':
                            if isinstance(widget, Gtk.Label):
                                widget.set_markup(f"<b>{widget.get_text()}</b>")
                        elif isinstance(widget, Gtk.Label):
                            widget.set_markup(f"<span foreground='{color}'>{widget.get_text()}</span>")
            except:
                pass

    @staticmethod
    def _create_badge(value, record, decorations):
        text = str(value) if value else ""
        label = Gtk.Label()
        label.set_margin_start(8)
        label.set_margin_end(8)
        
        # Default badge style (gray)
        bg_color = "#e9ecef"
        fg_color = "#495057"
        
        color_map = {
            'decoration-info': ('#cff4fc', '#055160'),
            'decoration-success': ('#d1e7dd', '#0f5132'),
            'decoration-danger': ('#f8d7da', '#842029'),
            'decoration-warning': ('#fff3cd', '#664d03'),
            'decoration-muted': ('#f8f9fa', '#6c757d'),
        }
        
        if record:
            for deco, expr in decorations.items():
                try:
                    if eval(expr, {"__builtins__": {}}, record):
                        colors = color_map.get(deco)
                        if colors:
                            bg_color, fg_color = colors
                            break
                except:
                    pass
        
        box = Gtk.Box()
        box.append(label)
        box.add_css_class("badge")
        label.set_markup(f"<span background='{bg_color}' foreground='{fg_color}'>  {text}  </span>")
        return box

    @staticmethod
    def _create_json_stats(value):
        try:
            import json
            # Odoo sometimes outputs single quotes in JSON-like strings
            json_str = value.replace("'", "\"")
            stats = json.loads(json_str)
            if not isinstance(stats, list): return WidgetFactory._create_char(value, False)
            
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            for item in stats:
                label_text = f"{item.get('label', '')}: {item.get('value', '')}"
                badge = Gtk.Label()
                badge.set_markup(f"<span background='#f0f0f0' foreground='#333' size='small'>  {label_text}  </span>")
                hbox.append(badge)
            return hbox
        except:
            return WidgetFactory._create_char(value, False)

    @staticmethod
    def _create_char(value, editable):
        if editable:
            entry = Gtk.Entry()
            entry.set_text(str(value) if value else "")
            return entry
        label = Gtk.Label(label=str(value) if value else "", xalign=0)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        return label

    @staticmethod
    def _create_boolean(value, editable):
        if editable:
            switch = Gtk.Switch()
            switch.set_active(bool(value))
            return switch
        check = Gtk.CheckButton()
        check.set_active(bool(value))
        check.set_sensitive(False)
        return check

    @staticmethod
    def _create_integer(value, editable):
        if editable:
            adj = Gtk.Adjustment(value=float(value or 0), lower=-2147483648, upper=2147483647, step_increment=1)
            return Gtk.SpinButton(adjustment=adj, digits=0)
        return Gtk.Label(label=str(value or 0), xalign=1)

    @staticmethod
    def _create_float(value, editable):
        if editable:
            adj = Gtk.Adjustment(value=float(value or 0), lower=-1e12, upper=1e12, step_increment=0.1)
            return Gtk.SpinButton(adjustment=adj, digits=2)
        return Gtk.Label(label=f"{float(value or 0):.2f}", xalign=1)

    @staticmethod
    def _create_m2o(value, editable):
        # value is [id, name] or id
        text = ""
        if isinstance(value, (list, tuple)) and len(value) > 1:
            text = str(value[1])
        elif value:
            text = str(value)
            
        if editable:
            entry = Gtk.Entry()
            entry.set_text(text)
            entry.add_css_class("m2o-entry")
            return entry
        
        label = Gtk.Label(label=text, xalign=0)
        label.add_css_class("m2o-label")
        return label

    @staticmethod
    def _create_x2m(value):
        count = len(value) if isinstance(value, list) else 0
        return Gtk.Label(label=f"({count} enregistrements)", xalign=0)

    @staticmethod
    def _create_image(value, size=32):
        if not value:
            return Gtk.Image.new_from_icon_name("image-x-generic-symbolic")
        
        try:
            import base64
            from gi.repository import GdkPixbuf
            
            # Handle modern Odoo base64 headers
            if isinstance(value, str) and ',' in value[:30]:
                value = value.split(',')[1]
                
            data = base64.b64decode(value)
            loader = GdkPixbuf.PixbufLoader()
            loader.write(data)
            loader.close()
            pixbuf = loader.get_pixbuf()
            
            if pixbuf:
                # Scale down for list view
                w = pixbuf.get_width()
                h = pixbuf.get_height()
                if w > size or h > size:
                    if w > h:
                        nw, nh = size, max(1, int(size * h / w))
                    else:
                        nw, nh = max(1, int(size * w / h)), size
                    pixbuf = pixbuf.scale_simple(nw, nh, GdkPixbuf.InterpType.BILINEAR)
                
                return Gtk.Image.new_from_pixbuf(pixbuf)
        except Exception as e:
            # print(f"DEBUG: Failed to render image: {e}")
            pass
            
        return Gtk.Image.new_from_icon_name("image-broken-symbolic")

    @staticmethod
    def _create_radio(value, field_info, editable):
        # field_info selection is usually available
        selection = field_info.get('selection', [])
        if not selection: return WidgetFactory._create_char(value, editable)
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.add_css_class("radio-group")
        group = None
        for key, label in selection:
            btn = Gtk.CheckButton(label=label)
            if group is None:
                group = btn
            else:
                btn.set_group(group)
            
            if str(key) == str(value):
                btn.set_active(True)
            
            if not editable:
                btn.set_sensitive(False)
                
            box.append(btn)
        return box

    @staticmethod
    def _create_m2m_tags(value):
        # value is a list of [id, name] or just ids
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        if not value: return hbox
        
        for item in value:
            text = ""
            if isinstance(item, (list, tuple)) and len(item) > 1:
                text = str(item[1])
            else:
                text = str(item)
            
            badge = Gtk.Label()
            badge.set_markup(f"<span background='#e1e1e1' foreground='#333' size='small'>  {text}  </span>")
            badge.add_css_class("badge")
            hbox.append(badge)
        return hbox

    @staticmethod
    def _create_statusbar(value, field_info, editable):
        selection = field_info.get('selection', [])
        if not selection: return Gtk.Label(label=str(value))
        
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.add_css_class("linked")
        
        for key, label in selection:
            btn = Gtk.Button(label=label)
            btn.add_css_class("o_arrow_button")
            if str(key) == str(value):
                btn.add_css_class("o_arrow_button_current")
            hbox.append(btn)
        return hbox

    @staticmethod
    def _create_boolean_toggle(value, editable):
        switch = Gtk.Switch()
        switch.set_active(bool(value))
        if not editable:
            switch.set_sensitive(False)
        return switch
