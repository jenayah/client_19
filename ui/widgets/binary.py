# -*- coding: utf-8 -*-
# Odoo GTK 19 — Binary / Image Widget
# Inspired by E:\odoo-client-19\widget\view\form_gtk\binary.py + image.py

import base64
from gi.repository import Gtk, GdkPixbuf, Gdk
from .base import WidgetBase


class BinaryWidget(WidgetBase):
    """binary field → File name label + download/upload buttons"""

    def _build_widget(self):
        self.widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.widget.set_hexpand(True)

        self.filename_label = Gtk.Label(label='(no file)', xalign=0)
        self.filename_label.set_hexpand(True)
        self.widget.append(self.filename_label)

        self.save_btn = Gtk.Button(icon_name='document-save-symbolic')
        self.save_btn.add_css_class('flat')
        self.widget.append(self.save_btn)

        self.clear_btn = Gtk.Button(icon_name='edit-clear-symbolic')
        self.clear_btn.add_css_class('flat')
        self.widget.append(self.clear_btn)
        
        self._raw_value = False

    def set_value(self, value):
        self._raw_value = value
        if value:
            size = len(str(value)) * 3 // 4  # approximate base64 decoded size
            if size > 1024 * 1024:
                self.filename_label.set_text(f'({size // (1024*1024):.1f} MB)')
            elif size > 1024:
                self.filename_label.set_text(f'({size // 1024:.0f} KB)')
            else:
                self.filename_label.set_text(f'({size} B)')
        else:
            self.filename_label.set_text('(no file)')

    def get_value(self):
        return self._raw_value


class ImageWidget(WidgetBase):
    """image field or widget="image" → Gtk.Picture from base64"""

    def _build_widget(self):
        self.widget = Gtk.Picture()
        self.widget.set_can_shrink(True)
        
        # Determine size from context
        size = 128
        widget_name = self.attrs.get('widget', '')
        field_name = self.field_name
        if '128' in field_name:
            size = 128
        elif '256' in field_name:
            size = 256
        elif '1920' in field_name:
            size = 256  # Don't render at full size in GTK
        
        self._size = size
        self.widget.set_size_request(size, size)
        self.widget.add_css_class('oe_avatar')

    def set_value(self, value):
        if not value or value is False:
            self.widget.set_paintable(None)
            return
        
        try:
            img_data = value
            if isinstance(img_data, str):
                # Remove possible data: prefix
                if ',' in img_data:
                    img_data = img_data.split(',', 1)[1]
                img_bytes = base64.b64decode(img_data)
            elif isinstance(img_data, bytes):
                img_bytes = img_data
            else:
                return

            loader = GdkPixbuf.PixbufLoader()
            loader.write(img_bytes)
            loader.close()
            pixbuf = loader.get_pixbuf()
            
            if pixbuf:
                # Scale proportionally
                w, h = pixbuf.get_width(), pixbuf.get_height()
                if w > 0 and h > 0:
                    ratio = min(self._size / w, self._size / h)
                    new_w = int(w * ratio)
                    new_h = int(h * ratio)
                    pixbuf = pixbuf.scale_simple(new_w, new_h, GdkPixbuf.InterpType.BILINEAR)
                
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                self.widget.set_paintable(texture)
        except Exception as e:
            print(f"Image decode error for {self.field_name}: {e}")

    def get_value(self):
        return False  # Read-only for now

    @staticmethod
    def create_from_base64(data, size=64):
        """Utility: create a Gtk.Picture from base64 data without a full widget."""
        if not data:
            return Gtk.Image.new_from_icon_name('image-x-generic-symbolic')
        try:
            if isinstance(data, str):
                if ',' in data:
                    data = data.split(',', 1)[1]
                raw = base64.b64decode(data)
            else:
                raw = data
            
            loader = GdkPixbuf.PixbufLoader()
            loader.write(raw)
            loader.close()
            pixbuf = loader.get_pixbuf()
            if pixbuf:
                w, h = pixbuf.get_width(), pixbuf.get_height()
                if w > 0 and h > 0:
                    ratio = min(size / w, size / h)
                    pixbuf = pixbuf.scale_simple(
                        int(w * ratio), int(h * ratio), GdkPixbuf.InterpType.BILINEAR)
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                pic = Gtk.Picture.new_for_paintable(texture)
                pic.set_size_request(size, size)
                pic.set_can_shrink(True)
                return pic
        except Exception:
            pass
        return Gtk.Image.new_from_icon_name('image-x-generic-symbolic')
