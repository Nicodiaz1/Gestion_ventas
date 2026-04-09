# ─────────────────────────────────────────────────────────────
#  ui/styles.py  –  Estilos y paleta centralizada
# ─────────────────────────────────────────────────────────────

STYLESHEET = """
QMainWindow, QDialog, QWidget {
    background-color: #1A1A1A;
    color: #F5F5F5;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13pt;
}

/* ── Sidebar ───────────────────────────────────────────── */
#sidebar {
    background-color: #111111;
    border-right: 2px solid #722F37;
}
#sidebar QPushButton {
    background-color: transparent;
    color: #CCCCCC;
    border: none;
    border-radius: 8px;
    padding: 12px 16px;
    text-align: left;
    font-size: 13pt;
    font-weight: 500;
}
#sidebar QPushButton:hover {
    background-color: #2C1A1D;
    color: #F5F5F5;
}
#sidebar QPushButton:checked, #sidebar QPushButton[active="true"] {
    background-color: #722F37;
    color: white;
    font-weight: 700;
}
#logo_label {
    color: #C9A84C;
    font-size: 16pt;
    font-weight: 800;
    padding: 20px 16px 8px 16px;
}
#sub_logo_label {
    color: #888888;
    font-size: 8pt;
    padding: 0px 16px 20px 16px;
}

/* ── Botones generales ─────────────────────────────────── */
QPushButton {
    background-color: #722F37;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 9px 20px;
    font-weight: 600;
    font-size: 13pt;
}
QPushButton:hover   { background-color: #8B3A44; }
QPushButton:pressed { background-color: #5C2530; }
QPushButton:disabled { background-color: #444; color: #888; }

QPushButton#btn_secundario {
    background-color: #2C2C2C;
    border: 1px solid #555;
    color: #F5F5F5;
}
QPushButton#btn_secundario:hover { background-color: #3C3C3C; }

QPushButton#btn_exito {
    background-color: #2E7D32;
}
QPushButton#btn_exito:hover { background-color: #388E3C; }

QPushButton#btn_advertencia {
    background-color: #E65100;
}
QPushButton#btn_advertencia:hover { background-color: #F57C00; }

QPushButton#btn_peligro {
    background-color: #B71C1C;
}
QPushButton#btn_peligro:hover { background-color: #C62828; }

QPushButton#btn_grande {
    font-size: 14pt;
    padding: 16px 32px;
    border-radius: 10px;
}

/* ── Inputs ────────────────────────────────────────────── */
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #2C2C2C;
    border: 1px solid #444;
    border-radius: 6px;
    padding: 7px 10px;
    color: #F5F5F5;
    font-size: 13pt;
}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QComboBox:focus {
    border: 2px solid #722F37;
}
QLineEdit#scan_input {
    font-size: 16pt;
    padding: 10px 14px;
    border: 2px solid #C9A84C;
    border-radius: 8px;
}

QComboBox::drop-down { border: none; }
QComboBox::down-arrow { image: none; width: 0; }
QComboBox QAbstractItemView {
    background-color: #2C2C2C;
    selection-background-color: #722F37;
    border: 1px solid #444;
}

/* ── Tabla ─────────────────────────────────────────────── */
QTableWidget {
    background-color: #1E1E1E;
    gridline-color: #333;
    border: none;
    border-radius: 8px;
    selection-background-color: #722F37;
    alternate-background-color: #252525;
}
QTableWidget::item { padding: 6px 10px; border: none; color: #F5F5F5; }
QTableWidget::item:alternate { color: #F5F5F5; }
QTableWidget::item:selected { background-color: #722F37; color: white; }
QTableWidget::indicator {
    width: 16px; height: 16px;
    border: 2px solid #888;
    border-radius: 3px;
    background: #2A2A2A;
    margin: 2px;
}
QTableWidget::indicator:unchecked { background: #2A2A2A; }
QTableWidget::indicator:checked {
    background: #722F37;
    border-color: #9E3A43;
    image: none;
}
QTableWidget::indicator:checked:hover { background: #8B3540; }
QTableWidget::indicator:unchecked:hover { border-color: #BBB; background: #383838; }

/* ── Lista (buscador y otros QListWidget) ─────────────── */
QListWidget {
    background-color: #1E1E1E;
    alternate-background-color: #252525;
    border: 1px solid #333;
    border-radius: 6px;
    color: #F5F5F5;
}
QListWidget::item {
    padding: 8px 12px;
    border-bottom: 1px solid #2E2E2E;
    color: #F5F5F5;
}
QListWidget::item:alternate { color: #F5F5F5; background-color: #252525; }
QListWidget::item:selected { background-color: #722F37; color: white; }
QListWidget::item:hover { background-color: #2E2E2E; }

QHeaderView::section {
    background-color: #2C2C2C;
    color: #C9A84C;
    font-weight: 700;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #722F37;
}

/* ── Tarjetas de métricas ──────────────────────────────── */
#card_widget {
    background-color: #2C2C2C;
    border-radius: 12px;
    border: 1px solid #3C3C3C;
}
#card_titulo { color: #AAAAAA; font-size: 9pt; }
#card_valor  { color: #F5F5F5; font-size: 22pt; font-weight: 800; }
#card_subtitulo { color: #C9A84C; font-size: 9pt; }

/* ── Labels ────────────────────────────────────────────── */
QLabel#titulo_seccion {
    font-size: 18pt;
    font-weight: 800;
    color: #F5F5F5;
    padding-bottom: 4px;
}
QLabel#alerta_stock {
    color: #FF9800;
    font-weight: 700;
}
QLabel#precio_total {
    font-size: 26pt;
    font-weight: 900;
    color: #C9A84C;
}

/* ── Tags de medio de pago ─────────────────────────────── */
QPushButton#mp_efectivo    { background-color: #1B5E20; }
QPushButton#mp_debito      { background-color: #0D47A1; }
QPushButton#mp_credito     { background-color: #4A148C; }
QPushButton#mp_transferencia{ background-color: #E65100; }
QPushButton#mp_qr          { background-color: #006064; }
QPushButton#mp_efectivo:checked,
QPushButton#mp_debito:checked,
QPushButton#mp_credito:checked,
QPushButton#mp_transferencia:checked,
QPushButton#mp_qr:checked  { border: 3px solid #C9A84C; }

/* ── ScrollBar ─────────────────────────────────────────── */
QScrollBar:vertical {
    background: #1A1A1A; width: 8px; border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #444; border-radius: 4px; min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

/* ── Tabs ──────────────────────────────────────────────── */
QTabWidget::pane  { border: 1px solid #444; border-radius: 8px; }
QTabBar::tab {
    background: #2C2C2C; color: #AAAAAA;
    padding: 8px 20px; border-radius: 6px 6px 0 0;
}
QTabBar::tab:selected { background: #722F37; color: white; font-weight: 700; }

/* ── DateEdit ──────────────────────────────────────────── */
QDateEdit {
    background-color: #2C2C2C;
    border: 1px solid #444;
    border-radius: 6px;
    padding: 6px 10px;
    color: #F5F5F5;
}

/* ── GroupBox ──────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #3C3C3C;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    color: #AAAAAA;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px; top: -6px;
    color: #C9A84C;
}

/* ── MessageBox ────────────────────────────────────────── */
QMessageBox { background-color: #2C2C2C; }
QMessageBox QPushButton { min-width: 80px; }
"""
