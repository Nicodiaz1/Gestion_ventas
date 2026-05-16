# ─────────────────────────────────────────────────────────────
#  ui/styles.py  –  Estilos y paleta centralizada
# ─────────────────────────────────────────────────────────────
import os as _os
_ASSETS    = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "assets")
_ARROW     = _os.path.join(_ASSETS, "arrow_down.svg").replace("\\", "/")
_ARROW_UP  = _os.path.join(_ASSETS, "arrow_up.svg").replace("\\", "/")

# ── Paleta ────────────────────────────────────────────────────
# Superficie base:   #0E0E13  (negro con tinte azul muy sutil)
# Superficie card:   #171620  (panel, un nivel arriba)
# Superficie input:  #111019  (inputs y campos, más profundo)
# Superficie elevada:#1F1E2B  (dialogs, tablas)
# Borde sutil:       #242336  (separadores, bordes de inputs)
# Borde fuerte:      #332F4E  (focus, divisores principales)
# Acento wine:       #7D2535  (brand color, botones primarios)
# Acento hover:      #9A2E42
# Dorado:            #C49A2A  (métricas, precios, énfasis)
# Texto primario:    #E0DFEB  (blanco ligeramente frío)
# Texto secundario:  #7A7A95  (labels, placeholders)
# Éxito:             #1D7A42  (verde oscuro refinado)
# Peligro:           #A82830  (rojo oscuro)
# Advertencia:       #B07020  (ámbar oscuro)

STYLESHEET = """
/* ── Base ──────────────────────────────────────────────────── */
QMainWindow, QDialog, QWidget {
    background-color: #0E0E13;
    color: #E0DFEB;
    font-family: "Helvetica Neue", "Segoe UI", Arial, sans-serif;
    font-size: 10pt;
}

/* ── Contenedores dentro de celdas ─────────────────────────── */
QTableWidget QWidget {
    background-color: transparent;
}

/* ── Sidebar ─────────────────────────────────────────────────*/
#sidebar {
    background-color: #0A0912;
    border-right: 1px solid #1E1C2E;
}
#sidebar QPushButton {
    background-color: transparent;
    color: #7A7A95;
    border: none;
    border-radius: 10px;
    padding: 10px 14px;
    text-align: left;
    font-size: 10pt;
    font-weight: 500;
}
#sidebar QPushButton:hover {
    background-color: #1A1828;
    color: #E0DFEB;
}
#sidebar QPushButton:checked, #sidebar QPushButton[active="true"] {
    background-color: #2A1520;
    color: #E0DFEB;
    font-weight: 700;
    border-left: 3px solid #7D2535;
}
#logo_label {
    color: #C49A2A;
    font-size: 16pt;
    font-weight: 800;
    padding: 20px 16px 8px 16px;
}
#sub_logo_label {
    color: #4A4A62;
    font-size: 8pt;
    padding: 0px 16px 20px 16px;
}

/* ── Botones generales ──────────────────────────────────────── */
QPushButton {
    background-color: #7D2535;
    color: #F0EEF8;
    border: none;
    border-radius: 20px;
    padding: 8px 20px;
    font-weight: 600;
    font-size: 10pt;
}
QPushButton:hover   { background-color: #9A2E42; }
QPushButton:pressed { background-color: #5E1C2A; }
QPushButton:disabled { background-color: #252332; color: #4A4A62; border-radius: 20px; }

QPushButton#btn_secundario {
    background-color: #1C1B28;
    border: 1px solid #2E2C44;
    color: #C0BFCE;
    border-radius: 20px;
}
QPushButton#btn_secundario:hover {
    background-color: #242338;
    border-color: #3E3C58;
    color: #E0DFEB;
}

QPushButton#btn_exito {
    background-color: #1D7A42;
}
QPushButton#btn_exito:hover { background-color: #238F4E; }

QPushButton#btn_advertencia {
    background-color: #B07020;
}
QPushButton#btn_advertencia:hover { background-color: #CC8225; }

QPushButton#btn_peligro {
    background-color: #A82830;
}
QPushButton#btn_peligro:hover { background-color: #C22F38; }

QPushButton#btn_grande {
    font-size: 14pt;
    padding: 16px 32px;
    border-radius: 28px;
}

QPushButton#btn_periodo_activo {
    background-color: #261020;
    border: 1px solid #7D2535;
    color: #E8C0C8;
    font-weight: 700;
    padding: 6px 14px;
    font-size: 11pt;
}
QPushButton#btn_periodo_activo:hover { background-color: #351828; }

QPushButton#btn_secundario_compacto {
    background-color: #1C1B28;
    border: 1px solid #2E2C44;
    color: #C0BFCE;
    padding: 6px 14px;
    font-size: 11pt;
    border-radius: 20px;
}
QPushButton#btn_secundario_compacto:hover {
    background-color: #242338;
    border-color: #3E3C58;
}

/* ── Inputs ─────────────────────────────────────────────────── */
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #111019;
    border: 1px solid #242336;
    border-radius: 8px;
    padding: 6px 10px;
    color: #E0DFEB;
    font-size: 10pt;
    selection-background-color: #7D2535;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #7D2535;
    background-color: #15131E;
}
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #7D2535;
}
QLineEdit::placeholder { color: #4A4A62; }
QTextEdit::placeholder { color: #4A4A62; }

QLineEdit#scan_input {
    font-size: 16pt;
    padding: 10px 14px;
    border: 1px solid #C49A2A;
    border-radius: 10px;
    background-color: #141220;
}

QComboBox::drop-down { border: none; }
QComboBox::down-arrow { image: none; width: 0; }
QComboBox QAbstractItemView {
    background-color: #17162A;
    selection-background-color: #7D2535;
    border: 1px solid #2E2C44;
    border-radius: 6px;
    color: #E0DFEB;
    outline: none;
}
QComboBox QAbstractItemView::item:hover { background-color: #242338; }

/* ── Tabla ──────────────────────────────────────────────────── */
QTableWidget {
    background-color: #111019;
    gridline-color: #1C1B28;
    border: 1px solid #1E1C2E;
    border-radius: 10px;
    selection-background-color: #2A1520;
    alternate-background-color: #141221;
}
QTableWidget::item {
    padding: 6px 10px;
    border: none;
    color: #DDDCEA;
}
QTableWidget::item:alternate { color: #DDDCEA; }
QTableWidget::item:selected {
    background-color: #2A1520;
    color: #F0EEF8;
}
QTableWidget::item:hover:!selected {
    background-color: #1A1828;
}
QTableWidget::indicator {
    width: 16px; height: 16px;
    border: 1px solid #3A3852;
    border-radius: 4px;
    background: #111019;
    margin: 2px;
}
QTableWidget::indicator:unchecked { background: #111019; }
QTableWidget::indicator:checked {
    background: #7D2535;
    border-color: #9A2E42;
    image: none;
}
QTableWidget::indicator:checked:hover { background: #8B2A3E; }
QTableWidget::indicator:unchecked:hover { border-color: #5A587A; background: #1A1828; }

/* ── QCheckBox ──────────────────────────────────────────────── */
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid #3A3852;
    border-radius: 4px;
    background: #111019;
}
QCheckBox::indicator:checked {
    background: #7D2535;
    border-color: #9A2E42;
    image: none;
}
QCheckBox::indicator:checked:hover { background: #8B2A3E; }
QCheckBox::indicator:unchecked:hover { border-color: #5A587A; background: #1A1828; }

/* ── Lista ──────────────────────────────────────────────────── */
QListWidget {
    background-color: #111019;
    alternate-background-color: #141221;
    border: 1px solid #1E1C2E;
    border-radius: 8px;
    color: #E0DFEB;
    outline: none;
}
QListWidget::item {
    padding: 8px 12px;
    border-bottom: 1px solid #1A1828;
    color: #DDDCEA;
}
QListWidget::item:alternate { color: #DDDCEA; background-color: #141221; }
QListWidget::item:selected { background-color: #2A1520; color: #F0EEF8; }
QListWidget::item:hover:!selected { background-color: #1A1828; }

/* ── Header de tabla ────────────────────────────────────────── */
QHeaderView::section {
    background-color: #0E0E13;
    color: #C49A2A;
    font-weight: 700;
    font-size: 9pt;
    letter-spacing: 0.5px;
    padding: 10px 10px;
    border: none;
    border-bottom: 1px solid #2A1520;
    text-transform: uppercase;
}
QHeaderView::section:hover {
    background-color: #141221;
    color: #D4AA3A;
}

/* ── Tarjetas de métricas ─────────────────────────────────── */
#card_widget {
    background-color: #17162A;
    border-radius: 14px;
    border: 1px solid #232236;
}
#card_titulo { color: #5A5872; font-size: 8pt; font-weight: 700; letter-spacing: 0.8px; background: transparent; text-transform: uppercase; }
#card_valor  { color: #E0DFEB; font-size: 22pt; font-weight: 800; background: transparent; }
#card_subtitulo { color: #C49A2A; font-size: 9pt; background: transparent; }

/* ── Labels ─────────────────────────────────────────────────── */
QLabel#titulo_seccion {
    font-size: 18pt;
    font-weight: 800;
    color: #E0DFEB;
    padding-bottom: 4px;
}
QLabel#alerta_stock {
    color: #D4901A;
    font-weight: 700;
}
QLabel#precio_total {
    font-size: 26pt;
    font-weight: 900;
    color: #C49A2A;
}

/* ── Medios de pago (POS) ─────────────────────────────────── */
QPushButton#mp_efectivo,
QPushButton#mp_debito,
QPushButton#mp_credito,
QPushButton#mp_transferencia,
QPushButton#mp_qr,
QPushButton#mp_fiado {
    border-radius: 18px;
    color: #F0EEF8;
    border: none;
    font-weight: 700;
    font-size: 10pt;
    padding: 8px 20px;
}
QPushButton#mp_efectivo      { background-color: #155230; }
QPushButton#mp_efectivo:hover{ background-color: #1A6839; }
QPushButton#mp_debito        { background-color: #0D3570; }
QPushButton#mp_debito:hover  { background-color: #104088; }
QPushButton#mp_credito       { background-color: #3A0F6E; }
QPushButton#mp_credito:hover { background-color: #4A1585; }
QPushButton#mp_transferencia       { background-color: #8A4510; }
QPushButton#mp_transferencia:hover { background-color: #A85215; }
QPushButton#mp_qr            { background-color: #054650; }
QPushButton#mp_qr:hover      { background-color: #075864; }
QPushButton#mp_fiado         { background-color: #3A1A1A; }
QPushButton#mp_fiado:hover   { background-color: #4A2222; }
QPushButton#mp_efectivo:checked,
QPushButton#mp_debito:checked,
QPushButton#mp_credito:checked,
QPushButton#mp_transferencia:checked,
QPushButton#mp_qr:checked,
QPushButton#mp_fiado:checked { border: 2px solid #C49A2A; }

/* ── ScrollBar ──────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #0E0E13; width: 6px; border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #2A2840; border-radius: 3px; min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #3A3860; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: #0E0E13; height: 6px; border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background: #2A2840; border-radius: 3px; min-width: 24px;
}
QScrollBar::handle:horizontal:hover { background: #3A3860; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Tabs ───────────────────────────────────────────────────── */
QTabWidget::pane  { border: none; background: transparent; }
QTabBar {
    background: transparent;
    border: none;
}
QTabBar::tab {
    background: #17162A;
    color: #5A5872;
    padding: 9px 22px;
    border-radius: 10px;
    margin-right: 4px;
    border: 1px solid #232236;
    font-size: 10pt;
    font-weight: 500;
}
QTabBar::tab:selected {
    background: #2A1520;
    color: #F0EEF8;
    font-weight: 700;
    border-color: #7D2535;
}
QTabBar::tab:hover:!selected {
    background: #1E1D30;
    color: #C0BFCE;
    border-color: #2E2C44;
}

/* ── DateEdit ───────────────────────────────────────────────── */
QDateEdit {
    background-color: #111019;
    border: 1px solid #242336;
    border-radius: 8px;
    padding: 6px 10px;
    color: #E0DFEB;
}
QDateEdit::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 28px;
    border-left: 1px solid #242336;
    border-top-right-radius: 7px;
    border-bottom-right-radius: 7px;
    background-color: #1C1B2A;
}
QDateEdit::drop-down:hover {
    background-color: #7D2535;
}
QDateEdit::down-arrow {
    image: none;
    width: 0;
    height: 0;
}

/* ── CalendarWidget ─────────────────────────────────────────── */
QCalendarWidget {
    background-color: #111019;
    color: #E0DFEB;
}
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #17162A;
    border-bottom: 1px solid #242336;
    padding: 4px 2px;
}
QCalendarWidget QToolButton {
    background-color: #1C1B2A;
    color: #E0DFEB;
    border: 1px solid #242336;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12pt;
    font-weight: 700;
    min-width: 28px;
    min-height: 28px;
}
QCalendarWidget QToolButton:hover {
    background-color: #7D2535;
    border-color: #9A2E42;
}
QCalendarWidget QToolButton::menu-indicator { image: none; }
QCalendarWidget QSpinBox {
    background-color: #111019;
    color: #E0DFEB;
    border: 1px solid #242336;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 11pt;
}
QCalendarWidget QWidget { alternate-background-color: #141221; }
QCalendarWidget QAbstractItemView {
    background-color: #111019;
    color: #E0DFEB;
    selection-background-color: #7D2535;
    selection-color: white;
    gridline-color: #1C1B28;
    outline: none;
}
QCalendarWidget QAbstractItemView:enabled { color: #E0DFEB; }
QCalendarWidget QAbstractItemView:disabled { color: #303048; }

/* ── GroupBox ───────────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #232236;
    border-radius: 10px;
    margin-top: 12px;
    padding-top: 8px;
    color: #5A5872;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px; top: -6px;
    color: #C49A2A;
}

/* ── MessageBox ─────────────────────────────────────────────── */
QMessageBox { background-color: #17162A; }
QMessageBox QPushButton { min-width: 80px; }

/* ── SpinBox subcontroles ────────────────────────────────────── */
QSpinBox, QDoubleSpinBox {
    padding: 4px 22px 4px 8px;
}
QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    background-color: #1C1B2A;
    border-left: 1px solid #242336;
    border-bottom: 1px solid #242336;
    border-top-right-radius: 7px;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover { background-color: #2A2840; }
QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed { background-color: #5E1C2A; }
QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    background-color: #1C1B2A;
    border-left: 1px solid #242336;
    border-bottom-right-radius: 7px;
}
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover { background-color: #2A2840; }
QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed { background-color: #5E1C2A; }
""" + f"""
QDateEdit::down-arrow {{
    image: url({_ARROW});
    width: 10px;
    height: 6px;
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url({_ARROW_UP}); width: 8px; height: 5px;
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url({_ARROW}); width: 8px; height: 5px;
}}
"""

# ── Subcontroles mínimos para setStyleSheet() inline ─────────
_SPIN_SUBCONTROLES = (
    "QSpinBox::up-button,QDoubleSpinBox::up-button{"
    "subcontrol-origin:border;subcontrol-position:top right;"
    "width:20px;background:#1C1B2A;"
    "border-left:1px solid #242336;border-bottom:1px solid #242336;"
    "border-top-right-radius:7px;}"
    "QSpinBox::up-button:hover,QDoubleSpinBox::up-button:hover{background:#2A2840;}"
    "QSpinBox::up-button:pressed,QDoubleSpinBox::up-button:pressed{background:#5E1C2A;}"
    f"QSpinBox::up-arrow,QDoubleSpinBox::up-arrow{{image:url({_ARROW_UP});width:8px;height:5px;}}"
    "QSpinBox::down-button,QDoubleSpinBox::down-button{"
    "subcontrol-origin:border;subcontrol-position:bottom right;"
    "width:20px;background:#1C1B2A;"
    "border-left:1px solid #242336;border-bottom-right-radius:7px;}"
    "QSpinBox::down-button:hover,QDoubleSpinBox::down-button:hover{background:#2A2840;}"
    "QSpinBox::down-button:pressed,QDoubleSpinBox::down-button:pressed{background:#5E1C2A;}"
    f"QSpinBox::down-arrow,QDoubleSpinBox::down-arrow{{image:url({_ARROW});width:8px;height:5px;}}"
)
