# Instructions du Projet : Odoo Client GTK (Gero)

## Objectif
Migration et amélioration du client Odoo vers GTK4/Adwaita pour Odoo 19, en préservant la rapidité et l'architecture fonctionnelle de l'ancien projet.

## Règles de Développement

### 1. Interface Utilisateur (UI)
- **Positionnement** : La barre de recherche doit toujours être en haut (`prepend`).
- **Adaptabilité** : Utiliser `Gtk.FlowBox` pour les champs de recherche afin qu'ils s'adaptent à la largeur de la fenêtre (wrapping).
- **Navigation** : 
    - Afficher la recherche UNIQUEMENT dans les modes Liste, Kanban, Graphe, Pivot.
    - Supprimer/Masquer la recherche UNIQUEMENT dans le mode Formulaire.
- **Organisation Recherche** : 
    - Saisie directe pour les `<field>`.
    - Bouton Popover "Filtres" pour les `<filter>` de domaine.
    - Bouton Popover "Regrouper par" pour les `<filter>` de contexte group_by.

### 2. Architecture Technique
- **Modularité** : Conserver le système de widgets séparés (un fichier par type de widget).
- **Widgets de Recherche** : Réutiliser et adapter le dossier `ui/widget_search/` (migré en GTK4).
- **Gestion Odoo 19** : 
    - Utiliser `session.client.call_kw` pour les appels RPC.
    - Gérer les Many2one avec des IDs entiers, pas des chaînes de caractères.
    - Filtrer rigoureusement les dictionnaires envoyés au serveur pour éviter les "Invalid field".

### 3. Priorités
1. **Fonctionnalité et Rapidité** : Le client doit être réactif (éviter les appels bloquants sur le thread principal).
2. **Fidélité Odoo** : Respecter le comportement des vues XML d'Odoo (domaines, contextes, attrs).
3. **Esthétique Adwaita** : Utiliser les classes CSS standard (`flat`, `caption`, `card`) pour un look premium.

## Fichiers Clés
- `ui/tab_page.py` : Orchestrateur des vues et de la recherche.
- `ui/widget_search/form.py` : Constructeur de la barre de recherche adaptative.
- `ui/widgets/one2many.py` : Gestion complexe des lignes de document.
- `core/session.py` : Gestion de la connexion et du cache RPC.
