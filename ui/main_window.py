# ─────────────────────────────────────────────────────────────
#  ui/main_window.py  –  Ventana principal con sidebar
# ─────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QSizePolicy,
    QFrame, QStatusBar, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import sys, os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import database as db
from ui.styles import STYLESHEET


# ─────────────────────────────────────────────────────────────
#  Worker para sincronización en background
# ─────────────────────────────────────────────────────────────

class SyncWorker(QThread):
    resultado = pyqtSignal(bool, str)

    def run(self):
        try:
            from sync.sync_manager import SyncManager
            mgr = SyncManager()
            mgr.sincronizar()
            self.resultado.emit(True, "Sincronización completada")
        except Exception as e:
            self.resultado.emit(False, str(e))


# ─────────────────────────────────────────────────────────────
#  Ventana principal
# ─────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🍷  Vinoteca — Sistema de Gestión")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)
        self.setStyleSheet(STYLESHEET)

        # Inicializar base de datos
        db.init_db()

        self._build_ui()
        self._setup_status_bar()

        # Timer para actualizar reloj
        self.timer_reloj = QTimer()
        self.timer_reloj.timeout.connect(self._actualizar_reloj)
        self.timer_reloj.start(1000)

        # Timer para alertas de stock (cada 5 min)
        self.timer_stock = QTimer()
        self.timer_stock.timeout.connect(self._verificar_stock)
        self.timer_stock.start(300_000)
        QTimer.singleShot(2000, self._verificar_stock)

    # ── Construcción ──────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # ── Sidebar ──────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(8, 0, 8, 16)
        sb_lay.setSpacing(2)

        # Logo
        lbl_logo = QLabel("🍷  Vinoteca")
        lbl_logo.setObjectName("logo_label")
        sb_lay.addWidget(lbl_logo)

        lbl_sub = QLabel("Sistema de Gestión")
        lbl_sub.setObjectName("sub_logo_label")
        sb_lay.addWidget(lbl_sub)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #333;")
        sb_lay.addWidget(sep)
        sb_lay.addSpacing(8)

        # Botones de navegación
        self.nav_buttons = []
        nav_items = [
            ("🛒  Punto de Venta",    0, "F5"),
            ("📦  Stock",             1, "F6"),
            ("📊  Reportes",          2, "F7"),
            ("🧾  Cuentas",           3, "F9"),
            ("⚙️   Configuración",    4, "F8"),
        ]
        for texto, idx, atajo in nav_items:
            btn = QPushButton(texto)
            btn.setCheckable(True)
            btn.setProperty("active", "false")
            btn.clicked.connect(lambda _, i=idx: self._navegar(i))
            sb_lay.addWidget(btn)
            self.nav_buttons.append(btn)

        sb_lay.addStretch()

        # Separador inferior
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color: #333;")
        sb_lay.addWidget(sep2)
        sb_lay.addSpacing(4)

        # Botón de sincronización
        self.btn_sync = QPushButton("☁️  Sincronizar")
        self.btn_sync.setObjectName("btn_secundario")
        self.btn_sync.setToolTip("Sincronizar con SQL Server")
        self.btn_sync.clicked.connect(self._iniciar_sync)
        sb_lay.addWidget(self.btn_sync)

        # Info de versión
        lbl_ver = QLabel("v1.2")
        lbl_ver.setStyleSheet("color:#555; font-size:8pt; padding:4px 16px;")
        sb_lay.addWidget(lbl_ver)

        root.addWidget(sidebar)

        # ── Stack de páginas ─────────────────────────────────
        self.stack = QStackedWidget()

        # POS
        from ui.pos import PosWidget
        self.pos_widget = PosWidget()
        self.pos_widget.venta_realizada.connect(self._on_venta_realizada)
        self.stack.addWidget(self.pos_widget)

        # Stock
        from ui.stock import StockWidget
        self.stock_widget = StockWidget()
        self.stack.addWidget(self.stock_widget)

        # Reportes
        from ui.reportes import ReportesWidget
        self.reportes_widget = ReportesWidget()
        self.stack.addWidget(self.reportes_widget)

        # Cuentas corrientes de proveedores
        from ui.cuentas_proveedor import CuentasProveedorWidget
        self.cuentas_widget = CuentasProveedorWidget()
        self.stack.addWidget(self.cuentas_widget)

        # Configuración
        from ui.config_panel import ConfigPanel
        self.config_panel = ConfigPanel()
        self.stack.addWidget(self.config_panel)

        root.addWidget(self.stack, 1)

        # Página inicial: POS
        self._navegar(0)

    def _setup_status_bar(self):
        sb = QStatusBar()
        sb.setStyleSheet(
            "QStatusBar { background: #111; color: #888; font-size: 9pt; border-top: 1px solid #333; }"
        )
        self.setStatusBar(sb)
        self.lbl_reloj = QLabel("")
        self.lbl_reloj.setStyleSheet("color:#888; padding-right:12px;")
        sb.addPermanentWidget(self.lbl_reloj)
        self.lbl_status = QLabel("  ✅  Sistema listo")
        sb.addWidget(self.lbl_status)
        self._actualizar_reloj()

    def _actualizar_reloj(self):
        ahora = datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
        self.lbl_reloj.setText(ahora)

    # ── Navegación ────────────────────────────────────────────

    def _navegar(self, idx: int):
        self.stack.setCurrentIndex(idx)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == idx)
            btn.setProperty("active", "true" if i == idx else "false")
            btn.setStyle(btn.style())  # fuerza re-apply style

        # Refrescar datos al cambiar de página
        if idx == 1:
            self.stock_widget.cargar_productos()
        elif idx == 2:
            self.reportes_widget._actualizar_resumen_hoy()
        elif idx == 3:
            self.cuentas_widget.cargar()
        elif idx == 0:
            QTimer.singleShot(50, self.pos_widget.scan_input.setFocus)

    # ── Eventos ───────────────────────────────────────────────

    def _on_venta_realizada(self, venta_id: int):
        self.lbl_status.setText(f"  ✅  Venta #{venta_id} registrada correctamente")
        QTimer.singleShot(4000, lambda: self.lbl_status.setText("  ✅  Sistema listo"))

    def _verificar_stock(self):
        bajos = db.productos_bajo_stock()
        if bajos:
            self.lbl_status.setText(
                f"  ⚠️  {len(bajos)} producto(s) con stock bajo")

    def _iniciar_sync(self):
        self.btn_sync.setEnabled(False)
        self.btn_sync.setText("⏳  Sincronizando…")
        self.lbl_status.setText("  ⏳  Sincronizando con SQL Server…")
        self.worker = SyncWorker()
        self.worker.resultado.connect(self._on_sync_resultado)
        self.worker.start()

    def _on_sync_resultado(self, ok: bool, msg: str):
        self.btn_sync.setEnabled(True)
        self.btn_sync.setText("☁️  Sincronizar")
        if ok:
            self.lbl_status.setText(f"  ✅  {msg}")
        else:
            self.lbl_status.setText(f"  ❌  Error de sincronización: {msg[:60]}")

    def closeEvent(self, event):
        resp = QMessageBox.question(
            self, "Salir",
            "¿Cerrar la aplicación?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
