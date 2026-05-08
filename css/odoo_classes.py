# -*- coding: utf-8 -*-
# Odoo GTK 19 — CSS Classes for Odoo Standard
# All Odoo o_* and oe_* classes mapped to GTK4 CSS

ODOO_CSS = """
/* ── Global Colors & Variables ──────────────────────────────── */
@define-color accent_color #714B67; /* Odoo Purple */
@define-color accent_bg_color #714B67;
@define-color accent_fg_color #ffffff;

/* ── Full White Interface ────────────────────────────────── */
window, 
headerbar,
.navigation-sidebar,
listbox,
listview,
columnview,
scrolledwindow,
viewport,
stack,
.o_form_view,
.o_form_sheet,
.o_kanban_view {
    background-color: #FFFFFF;
    background-image: none;
    border-color: #F0F0F0;
}

/* Remove headerbar border for a cleaner look */
headerbar {
    border-bottom: 1px solid #F0F0F0;
    box-shadow: none;
}

.o_form_sheet {
    background-color: #FFFFFF;
    border: 1px solid #EEEEEE;
    border-radius: 4px;
    padding: 24px 32px;
    margin: 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.03);
}
.o_form_label {
    font-weight: 500;
    color: alpha(@window_fg_color, 0.7);
    margin-right: 8px;
}
.o_required_modifier .o_form_label {
    color: @accent_color;
    font-weight: bold;
}

/* ── Header / Statusbar ─────────────────────────────────────── */
.statusbar {
    background-color: @headerbar_bg_color;
    padding: 8px 16px;
    border-bottom: 1px solid @border_color;
}
.o_arrow_button {
    border-radius: 2px;
    margin-right: -1px;
    padding: 4px 12px;
    background-color: @window_bg_color;
    border: 1px solid @border_color;
    font-weight: 500;
    color: alpha(@window_fg_color, 0.8);
}
.o_arrow_button_current {
    background-color: #f1f1f1;
    color: @accent_color;
    font-weight: bold;
}

/* ── Titles ──────────────────────────────────────────────────── */
.title-1 {
    font-size: 2rem;
    font-weight: 600;
    color: #212529;
}
.title-4 {
    font-size: 1.1rem;
    font-weight: 600;
    color: @accent_color;
    margin-top: 16px;
    margin-bottom: 8px;
    border-bottom: 1px solid alpha(@border_color, 0.5);
    padding-bottom: 4px;
}
.oe_title {
    margin-bottom: 24px;
}

/* ── Smart Buttons ───────────────────────────────────────────── */
.oe_button_box {
    margin-bottom: 16px;
}
.oe_stat_button {
    min-width: 100px;
    min-height: 44px;
    background-color: transparent;
    border: 1px solid @border_color;
    border-radius: 0;
    padding: 4px 12px;
}
.oe_stat_button:hover {
    background-color: alpha(@accent_color, 0.05);
}
.o_stat_value {
    font-weight: bold;
    font-size: 1.2rem;
    color: @accent_color;
}
.o_stat_text {
    font-size: 0.75rem;
    text-transform: uppercase;
    color: alpha(@window_fg_color, 0.6);
}

/* ── Avatar / Image ──────────────────────────────────────────── */
.oe_avatar {
    border: 1px solid @border_color;
    padding: 4px;
    background-color: white;
    border-radius: 2px;
}

/* ── Groups ──────────────────────────────────────────────────── */
.o_inner_group {
    margin-bottom: 16px;
}
.o_inner_group > label {
    padding-right: 12px;
}
.o_row {
    /* spacing handled by Box */
}

/* ── Badges / Tags ────────────────────────────────────────────── */
/* ── Tax Totals ──────────────────────────────────────────────── */
.o_tax_totals {
    margin-top: 16px;
    padding: 16px;
    border-top: 1px solid @border_color;
    background-color: alpha(@window_bg_color, 0.5);
}
.o_tax_totals label.title-4 {
    border-bottom: none;
    margin-top: 0;
}
.badge {
    border-radius: 12px;
    padding: 2px 10px;
    font-size: 0.85rem;
    background-color: #e9ecef;
    color: #495057;
    font-weight: normal;
}
.badge button.flat.circular {
    padding: 0;
    min-width: 16px;
    min-height: 16px;
    margin-left: 4px;
    opacity: 0.6;
}
.badge button.flat.circular:hover {
    opacity: 1.0;
    background-color: rgba(0,0,0,0.1);
}

/* Tags colors (Odoo Standard) */
.o_tag_color_1 { background-color: #f8d7da; color: #721c24; }
.o_tag_color_2 { background-color: #d1e7dd; color: #0f5132; }
.o_tag_color_3 { background-color: #fff3cd; color: #856404; }
.o_tag_color_4 { background-color: #cfe2ff; color: #084298; }
.o_tag_color_5 { background-color: #e2e3e5; color: #41464b; }
.o_tag_color_6 { background-color: #d1e7dd; color: #0f5132; }
.o_tag_color_7 { background-color: #f8d7da; color: #721c24; }
.o_tag_color_8 { background-color: #fff3cd; color: #856404; }
.o_tag_color_9 { background-color: #cfe2ff; color: #084298; }
.o_tag_color_10 { background-color: #d1e7dd; color: #0f5132; }

/* ── Kanban Record Styling ────────────────────────────────────── */
.o_kanban_record {
    background-color: @window_bg_color;
    border: 1px solid shade(@border_color, 0.95);
    border-radius: 8px;
    padding: 12px;
    margin: 4px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.o_kanban_record:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    border-color: @accent_color;
}
.o_kanban_record .card {
    background: transparent;
    border: none;
    box-shadow: none;
}

/* ── Bootstrap Utilities ─────────────────────────────────────── */
.fs-1 { font-size: 2.5rem; }
.fs-2 { font-size: 2rem; }
.fs-3 { font-size: 1.75rem; }
.fs-4 { font-size: 1.5rem; }
.fs-5 { font-size: 1.25rem; }
.fs-6 { font-size: 1rem; }

.fw-bold, .fw-bolder { font-weight: 700; }
.fw-normal { font-weight: 400; }

.text-muted, .dim-label { color: alpha(@window_fg_color, 0.55); }
.text-success { color: #198754; }
.text-info { color: #0dcaf0; }
.text-warning { color: #ffc107; }
.text-danger { color: #dc3545; }

.mb-1 { margin-bottom: 4px; }
.mb-2 { margin-bottom: 8px; }
.me-1 { margin-right: 4px; }
.me-2 { margin-right: 8px; }

.badge {
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.75rem;
    font-weight: 600;
}
.badge-success { background-color: #d1e7dd; color: #0f5132; }
.badge-info { background-color: #cff4fc; color: #055160; }

/* ── Specific Odoo Tags ──────────────────────────────────────── */
footer {
    border-top: 1px solid alpha(@border_color, 0.3);
    margin-top: 8px;
    padding-top: 8px;
}

.o_kanban_record_title {
    color: #212529;
    font-weight: 700;
    font-size: 1.1rem;
}

/* ── Notebook ────────────────────────────────────────────────── */
notebook header tabs {
    background-color: transparent;
    border-bottom: 1px solid @border_color;
}
notebook header tab {
    padding: 8px 16px;
    border-bottom: 2px solid transparent;
}
notebook header tab:checked {
    border-bottom-color: @accent_color;
    color: @accent_color;
    font-weight: bold;
}

/* ── Pivot Table Styling ────────────────────────────────────── */
.pivot-table {
    background-color: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 12px;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.pivot-table label {
    padding: 4px 8px;
}

.pivot-table .fw-bold {
    color: #714B67;
    border-bottom: 2px solid #714B67;
    margin-bottom: 4px;
}

/* --- Native Report Styling --- */
.report-paper {
    background-color: white;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    border: 1px solid #E0E0E0;
}

.report-partner-name {
    font-size: 18px;
    color: #333333;
    font-weight: 500;
}

.report-info-frame {
    background-color: #F8F9FA;
    border: 1.5px solid #333333;
    border-radius: 10px;
}

.report-info-col-sep {
    border-right: 1px solid #CCCCCC;
}

.report-info-title {
    font-weight: bold;
    color: #333333;
    font-size: 13px;
}

.report-info-value {
    color: #444444;
    font-size: 15px;
}

.report-table {
    border: 1px solid #CCCCCC;
    border-radius: 8px;
}

.report-table-header {
    background-color: #5D4373;
    color: white;
    font-weight: bold;
    font-size: 12px;
    padding: 5px;
    border-radius: 6px 6px 0 0;
}

.report-table-row {
    border-bottom: 1px solid #EEEEEE;
    padding: 8px;
}

.report-cell {
    padding: 5px;
}

.report-totals-box {
    background-color: #5D4373;
    color: white;
    border-radius: 0 0 8px 8px;
    min-width: 250px;
}

.report-total-row {
    padding: 10px;
    font-size: 16px;
    font-weight: bold;
}
"""

