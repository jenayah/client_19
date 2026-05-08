import json
import os
from gi.repository import Gtk, Adw, Gio
from core import session

CONFIG_FILE = "config.json"

class LoginDialog(Adw.Window):
    def __init__(self, parent_app, on_success):
        super().__init__(application=parent_app, modal=True)
        self.parent_app = parent_app
        self.on_success = on_success
        
        self.set_title("Connexion Gero")
        self.set_default_size(400, 450)
        
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.main_box.set_margin_start(24)
        self.main_box.set_margin_end(24)
        self.main_box.set_margin_top(24)
        self.main_box.set_margin_bottom(24)
        self.set_content(self.main_box)
        
        # Logo / Title
        title_label = Gtk.Label(label="Odoo 19 Client")
        title_label.add_css_class("title-1")
        self.main_box.append(title_label)
        
        # Load saved config
        config = self._load_config()
        
        # Form
        self.entry_url = Adw.EntryRow(title="URL du serveur")
        self.entry_url.set_text(config.get("url", "http://localhost:1969"))
        self.entry_url.connect("changed", self._on_url_changed)
        
        # Database selector (ComboRow)
        self.db_model = Gtk.StringList.new([])
        self.entry_db = Adw.ComboRow(title="Base de données")
        self.entry_db.set_model(self.db_model)
        
        # Search DB Button
        btn_refresh_db = Gtk.Button(icon_name="view-refresh-symbolic")
        btn_refresh_db.add_css_class("flat")
        btn_refresh_db.set_tooltip_text("Rafraîchir la liste des bases")
        btn_refresh_db.connect("clicked", self._refresh_databases)
        self.entry_db.add_suffix(btn_refresh_db)
        
        self.entry_login = Adw.EntryRow(title="Utilisateur")
        self.entry_login.set_text(config.get("login", "admin"))
        
        self.entry_password = Adw.PasswordEntryRow(title="Mot de passe")
        self.entry_password.set_text("")
        
        group = Adw.PreferencesGroup()
        group.add(self.entry_url)
        group.add(self.entry_db)
        group.add(self.entry_login)
        group.add(self.entry_password)
        self.main_box.append(group)
        
        # Buttons Box
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.CENTER)
        btn_box.set_margin_top(12)
        self.main_box.append(btn_box)
        
        # Login Button
        self.btn_login = Gtk.Button(label="Se connecter")
        self.btn_login.add_css_class("suggested-action")
        self.btn_login.add_css_class("pill")
        self.btn_login.connect("clicked", self._on_login_clicked)
        btn_box.append(self.btn_login)
        
        # Cancel Button
        self.btn_cancel = Gtk.Button(label="Annuler")
        self.btn_cancel.add_css_class("pill")
        self.btn_cancel.connect("clicked", lambda b: self.parent_app.quit())
        btn_box.append(self.btn_cancel)
        
        # Error label
        self.error_label = Gtk.Label(label="")
        self.error_label.add_css_class("error")
        self.error_label.set_wrap(True)
        self.main_box.append(self.error_label)
        
        # Initial DB refresh
        self._refresh_databases()
        
        # Set saved DB if possible
        saved_db = config.get("db")
        if saved_db:
            self._select_db_by_name(saved_db)

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except: pass
        return {}

    def _save_config(self, url, db, login):
        config = {"url": url, "db": db, "login": login}
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)

    def _on_url_changed(self, entry):
        # Maybe auto-refresh DBs when URL changes?
        pass

    def _refresh_databases(self, button=None):
        url = self.entry_url.get_text()
        try:
            dbs = session.list_db(url)
            self.db_model.splice(0, self.db_model.get_n_items(), dbs)
            if dbs:
                self.entry_db.set_selected(0)
        except Exception as e:
            print(f"Error fetching DBs: {e}")

    def _select_db_by_name(self, db_name):
        for i in range(self.db_model.get_n_items()):
            if self.db_model.get_string(i) == db_name:
                self.entry_db.set_selected(i)
                break

    def _on_login_clicked(self, button):
        url = self.entry_url.get_text()
        
        selected_idx = self.entry_db.get_selected()
        if selected_idx == Gtk.INVALID_LIST_POSITION:
            self.error_label.set_text("Veuillez sélectionner une base de données")
            return
        db = self.db_model.get_string(selected_idx)
        
        login = self.entry_login.get_text()
        password = self.entry_password.get_text()
        
        self.btn_login.set_sensitive(False)
        self.error_label.set_text("Connexion en cours...")
        
        try:
            if session.connect(url, db, login, password):
                self._save_config(url, db, login)
                self.on_success()
                self.close()
        except Exception as e:
            self.error_label.set_text(f"Erreur: {str(e)}")
            self.btn_login.set_sensitive(True)
