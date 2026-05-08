# -*- coding: utf-8 -*-
from gi.repository import Gtk, Gdk, GObject, Pango
from core.session import session as rpc_session
from . import wid_int

def _(s): return s

class char(wid_int.wid_int):
    def __init__(self, name, parent, attrs={}, screen=None):
        wid_int.wid_int.__init__(self, name, parent, attrs, screen)
        self.attrs = attrs
        self.screen = screen
        self.widget = Gtk.Entry()
        if attrs.get('type') == 'char':
            self.widget.set_max_length(int(attrs.get('size',16)))
        self.widget.set_width_chars(15)
        self.widget.set_property('activates_default', True)
        self.default_value = False
        if self.default_search:
            model = self.attrs.get('relation', '')
            if attrs.get('type','') == 'many2one' and model:
                try:
                    value = rpc_session.client.call_kw(model, 'name_get', [self.default_search], {'context': self.screen.context if self.screen else {}})
                except:
                    value = [(0,'')]
                self.default_value, self.default_search = value and value[0]
            self.widget.set_text(str(self.default_search) if self.default_search else '')

    def _value_get(self):
        s = self.widget.get_text()
        domain = []
        context = {}
        if s:
            if self.attrs.get('filter_domain'):
                # Simplified eval for now
                domain = [(self.name, 'ilike', s)] 
            else:
                if self.default_value:
                    domain = [(self.name,'=', self.default_value)]
                    self.default_value = False
                else:
                    domain = [(self.name,self.attrs.get('comparato','ilike'),s)]
        return {
            'domain':domain,
            'context': context
        }

    def _value_set(self, value):
        self.widget.set_text(str(value) if value else "")

    value = property(_value_get, _value_set, None, _('The content of the widget or ValueError if not valid'))

    def clear(self):
        self.value = ''

    def grab_focus(self):
        self.widget.grab_focus()
        
    def _readonly_set(self, value):
        self.widget.set_editable(not value)
        self.widget.set_sensitive(not value)

    def sig_activate(self, fct):
        self.widget.connect_after('activate', fct)
