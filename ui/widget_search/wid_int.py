# -*- coding: utf-8 -*-
from gi.repository import Gtk, Gdk, GObject, Pango
from core.session import session as rpc_session

def _(s): return s

class wid_int(object):
    def __init__(self, name, parent, attrs={}, call=None):
        self.call = call
        self._value = None
        self.parent = parent
        self.name = name
        self.model = attrs.get('model', None)
        self.attrs = attrs
        self.default_search = False
        if self.attrs.get('name',False):
            if isinstance(call, (list, tuple)):
               default_context = call[0].context
            elif call:
               default_context = call.context
            else:
               default_context = {}
               
            context_str = 'search_default_' + str(self.attrs['name'])
            self.default_search = default_context.get(context_str,False)
            if attrs.get('type') == 'boolean':
                if context_str not in default_context:
                    self.default_search = ''

    def clear(self):
        self.value = ''

    def _value_get(self):
        return {'domain': [(self.name,'=',self._value)]}

    def _value_set(self, value):
        self._value = value

    value = property(_value_get, _value_set, None, _('The content of the widget or exception if not valid'))

    def _readonly_set(self, value):
        pass

    def sig_activate(self, fct):
        pass
