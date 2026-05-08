from gi.repository import Gtk, Adw
from .views.form import FormView

class DetailWindow(Adw.Window):
    def __init__(self, model_name, res_id, title="Détails"):
        super().__init__(modal=True)
        self.set_default_size(800, 600)
        self.set_title(title)
        
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.main_box)
        
        self.header = Adw.HeaderBar()
        self.main_box.append(self.header)
        
        # Save Button
        save_btn = Gtk.Button(label="Enregistrer")
        save_btn.add_css_class("suggested-action")
        self.header.pack_start(save_btn)
        
        self.form_view = FormView(model_name, res_id)
        self.main_box.append(self.form_view)
