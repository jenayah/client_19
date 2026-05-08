# -*- coding: utf-8 -*-
# Odoo GTK 19 — Widget Registry
# Inspired by widgets_type in E:\odoo-client-19\widget\view\form_gtk\parser.py (line 984)

from .char import CharWidget
from .integer import IntegerWidget
from .float_field import FloatWidget, MonetaryWidget
from .boolean import BooleanWidget, ToggleWidget, FavoriteWidget
from .selection import SelectionWidget, RadioWidget
from .date import DateWidget, DatetimeWidget
from .text import TextWidget, HtmlWidget
from .binary import BinaryWidget, ImageWidget
from .many2one import Many2oneWidget
from .many2many import Many2manyWidget, Many2manyTagsWidget
from .one2many import One2manyWidget
from .tax_totals import TaxTotalsWidget
from .statusbar import StatusbarWidget, BadgeWidget, StatInfoWidget, PriorityWidget, HandleWidget
from .url_field import UrlWidget, EmailWidget, PhoneWidget
from .json_field import JsonWidget, ProgressBarWidget, ReferenceWidget, ColorWidget, PropertiesWidget

# ── Type-based registry ───────────────────────────────────────────
# Format: { field_type: (WidgetClass, default_colspan, expand, fill) }
widgets_type = {
    'char':                 (CharWidget,        1, False, False),
    'integer':              (IntegerWidget,     1, False, False),
    'float':                (FloatWidget,       1, False, False),
    'monetary':             (MonetaryWidget,    1, False, False),
    'boolean':              (BooleanWidget,     1, False, False),
    'selection':            (SelectionWidget,   1, False, False),
    'date':                 (DateWidget,        1, False, False),
    'datetime':             (DatetimeWidget,    1, False, False),
    'text':                 (TextWidget,        1, True,  True),
    'html':                 (HtmlWidget,        1, True,  True),
    'binary':               (BinaryWidget,      1, False, False),
    'image':                (ImageWidget,       1, False, False),
    'many2one':             (Many2oneWidget,    1, False, False),
    'many2many':            (Many2manyWidget,   1, True,  True),
    'one2many':             (One2manyWidget,    1, True,  True),
    'reference':            (ReferenceWidget,   1, False, False),
    'json':                 (JsonWidget,        1, False, False),
    'properties':           (PropertiesWidget,  1, False, False),
    'url':                  (UrlWidget,         1, False, False),
    'email':                (EmailWidget,       1, False, False),
    'phone':                (PhoneWidget,       1, False, False),
    'float_time':           (FloatWidget,       1, False, False),
    'analytic_distribution':(JsonWidget,        1, False, False),
    'many2one_reference':   (IntegerWidget,     1, False, False),
}

# ── Widget-attribute overrides ────────────────────────────────────
# When XML has widget="xxx", use this class instead of the type default
widgets_optional = {
    'many2many_tags':       Many2manyTagsWidget,
    'radio':                RadioWidget,
    'toggle':               ToggleWidget,
    'boolean_toggle':       ToggleWidget,
    'boolean_favorite':     FavoriteWidget,
    'statusbar':            StatusbarWidget,
    'badge':                BadgeWidget,
    'image':                ImageWidget,
    'monetary':             MonetaryWidget,
    'statinfo':             StatInfoWidget,
    'progressbar':          ProgressBarWidget,
    'priority':             PriorityWidget,
    'handle':               HandleWidget,
    'color':                ColorWidget,
    'properties':           PropertiesWidget,
    'url':                  UrlWidget,
    'email':                EmailWidget,
    'phone':                PhoneWidget,
    'sol_o2m':              One2manyWidget,
    'account-tax-totals-field': TaxTotalsWidget,
}


def create_field_widget(field_name, field_info, attrs=None, record=None):
    """Factory: create the appropriate widget for a field.
    
    Lookup order:
      1. attrs['widget'] → widgets_optional
      2. Auto-detect image fields by name pattern
      3. field_info['type'] → widgets_type
      4. Fallback → CharWidget
    """
    attrs = attrs or {}
    widget_attr = attrs.get('widget', '')
    field_type = field_info.get('type', 'char')

    # 1. Check optional widget override
    if widget_attr and widget_attr in widgets_optional:
        cls = widgets_optional[widget_attr]
        return cls(field_name, field_info, attrs, record)

    # 2. Auto-detect image fields by name when type is binary
    if field_type == 'binary':
        image_patterns = ('avatar_', 'image_', 'picture', 'photo', 'logo')
        if any(p in field_name for p in image_patterns):
            return ImageWidget(field_name, field_info, attrs, record)

    # 3. Check type registry
    if field_type in widgets_type:
        cls = widgets_type[field_type][0]
        return cls(field_name, field_info, attrs, record)

    # 4. Fallback
    return CharWidget(field_name, field_info, attrs, record)
