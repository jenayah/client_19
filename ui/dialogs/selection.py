# -*- coding: utf-8 -*-
from gi.repository import Gtk, GObject
from ui.views.list import ListView

class SelectionDialog(Gtk.Window):
    """A dialog to select a record from a model."""
    __gsignals__ = {
        'record-selected': (GObject.SignalFlags.RUN_FIRST, None, (int, str)),
    }

    def __init__(self, parent, model_name, title="Sélectionner"):
        super().__init__(title=title, transient_for=parent, modal=True)
        self.set_default_size(800, 600)
        
        hb = Gtk.HeaderBar()
        self.set_titlebar(hb)
        
        self.model_name = model_name
        
        # Build the list view for selection
        # We reuse the existing ListView
        self.list_view = ListView(model_name)
        self.list_view.connect('record-activated', self._on_record_activated)
        
        self.set_child(self.list_view)
        
        btn_cancel = Gtk.Button(label="Annuler")
        btn_cancel.connect('clicked', lambda b: self.destroy())
        hb.pack_start(btn_cancel)

    def _on_record_activated(self, list_view, res_id):
        # We need the display_name. ListView stores record data in _RowData
        # Let's try to find it in the store
        display_name = f"#{res_id}"
        for i in range(list_view.store.get_n_items()):
            item = list_view.store.get_item(i)
            if item.data.get('id') == res_id:
                display_name = item.data.get('display_name', item.data.get('name', display_name))
                break
        
        self.emit('record-selected', res_id, display_name)
