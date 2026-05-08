# -*- coding: utf-8 -*-
# Odoo GTK 19 — Main Entry Point

import sys
import os
print(f"DEBUG: Running from {os.getcwd()}")
print(f"DEBUG: main.py path: {__file__}")
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, Gdk
from core import session
from ui.login import LoginDialog
from ui.window import OdooMainWindow
from css.odoo_classes import ODOO_CSS


class OdooApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.odoo.gtk19.v2',
                         flags=Gio.ApplicationFlags.NON_UNIQUE)

    def do_activate(self):
        # Force Light Theme (White background)
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)

        # Apply CSS early
        try:
            provider = Gtk.CssProvider()
            provider.load_from_string(ODOO_CSS)
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception as e:
            print(f"CSS load error: {e}")

        if not session.is_authenticated:
            self.login_dlg = LoginDialog(self, self._on_login_success)
            self.login_dlg.present()
        else:
            self._show_main_window()

    def _on_login_success(self):
        self._show_main_window()

    def _show_main_window(self):
        self.win = OdooMainWindow(application=self)
        self.win.present()

if __name__ == '__main__':
    app = OdooApp()
    sys.exit(app.run(sys.argv))
