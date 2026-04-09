# ─────────────────────────────────────────────────────────────
#  ui/config_panel.py  –  Configuración de la aplicación
# ─────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout, QGroupBox, QSpinBox,
    QMessageBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QTextEdit, QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import database as db


class ConfigPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._cargar_config()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(24, 16, 24, 16)

        titulo = QLabel("⚙️   Configuración")
        titulo.setObjectName("titulo_seccion")
        lay.addWidget(titulo)

        tabs = QTabWidget()

        # ── Tab: Negocio ─────────────────────────────────────
        tab_negocio = QWidget()
        lay_neg = QVBoxLayout(tab_negocio)
        lay_neg.setSpacing(12)

        grp_negocio = QGroupBox("Datos del negocio")
        form_neg = QFormLayout(grp_negocio)
        self.txt_nombre_negocio = QLineEdit()
        form_neg.addRow("Nombre del negocio:", self.txt_nombre_negocio)
        self.txt_moneda = QLineEdit()
        form_neg.addRow("Símbolo de moneda:", self.txt_moneda)
        self.spin_stock_min = QSpinBox()
        self.spin_stock_min.setRange(0, 999)
        form_neg.addRow("Alerta stock mínimo por defecto:", self.spin_stock_min)

        self.spin_dias_venc = QSpinBox()
        self.spin_dias_venc.setRange(1, 365)
        self.spin_dias_venc.setSuffix(" días")
        self.spin_dias_venc.setToolTip(
            "Cuántos días antes del vencimiento se muestra la alerta en la pantalla de stock")
        form_neg.addRow("⏰ Alerta vencimiento anticipada:", self.spin_dias_venc)
        lay_neg.addWidget(grp_negocio)

        btn_guardar_neg = QPushButton("💾  Guardar configuración")
        btn_guardar_neg.clicked.connect(self._guardar_config)
        lay_neg.addWidget(btn_guardar_neg)
        lay_neg.addStretch()
        tabs.addTab(tab_negocio, "🏪  Negocio")

        # ── Tab: SQL Server ───────────────────────────────────
        tab_sql = QWidget()
        lay_sql = QVBoxLayout(tab_sql)

        grp_sql = QGroupBox("Conexión SQL Server (sincronización)")
        form_sql = QFormLayout(grp_sql)
        self.txt_sql_server = QLineEdit()
        self.txt_sql_server.setPlaceholderText("Ej: localhost\\SQLEXPRESS")
        form_sql.addRow("Servidor:", self.txt_sql_server)
        self.txt_sql_db = QLineEdit("vinoteca")
        form_sql.addRow("Base de datos:", self.txt_sql_db)
        self.txt_sql_user = QLineEdit()
        form_sql.addRow("Usuario:", self.txt_sql_user)
        self.txt_sql_pass = QLineEdit()
        self.txt_sql_pass.setEchoMode(QLineEdit.EchoMode.Password)
        form_sql.addRow("Contraseña:", self.txt_sql_pass)
        lay_sql.addWidget(grp_sql)

        btn_row = QHBoxLayout()
        btn_test = QPushButton("🔌  Probar conexión")
        btn_test.setObjectName("btn_secundario")
        btn_test.clicked.connect(self._probar_sql)
        btn_guardar_sql = QPushButton("💾  Guardar")
        btn_guardar_sql.clicked.connect(self._guardar_sql)
        btn_row.addWidget(btn_test)
        btn_row.addWidget(btn_guardar_sql)
        lay_sql.addLayout(btn_row)
        lay_sql.addStretch()
        tabs.addTab(tab_sql, "☁️  SQL Server")

        # ── Tab: Categorías ───────────────────────────────────
        tab_cats = QWidget()
        lay_cats = QVBoxLayout(tab_cats)

        header_cats = QHBoxLayout()
        header_cats.addWidget(QLabel("Categorías de productos"))
        header_cats.addStretch()
        btn_nueva_cat = QPushButton("➕  Nueva categoría")
        btn_nueva_cat.clicked.connect(self._nueva_categoria)
        header_cats.addWidget(btn_nueva_cat)
        lay_cats.addLayout(header_cats)

        self.tabla_cats = QTableWidget(0, 3)
        self.tabla_cats.setHorizontalHeaderLabels(["ID", "Nombre", "Descripción"])
        self.tabla_cats.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla_cats.setColumnWidth(0, 50)
        self.tabla_cats.setAlternatingRowColors(True)
        self.tabla_cats.verticalHeader().setVisible(False)
        lay_cats.addWidget(self.tabla_cats)
        self._cargar_categorias()
        tabs.addTab(tab_cats, "🏷️  Categorías")

        # ── Tab: Proveedores ─────────────────────────────────
        tab_prov = QWidget()
        lay_prov = QVBoxLayout(tab_prov)

        header_prov = QHBoxLayout()
        header_prov.addWidget(QLabel("Proveedores"))
        header_prov.addStretch()
        btn_nuevo_prov = QPushButton("➕  Nuevo proveedor")
        btn_nuevo_prov.clicked.connect(self._nuevo_proveedor)
        header_prov.addWidget(btn_nuevo_prov)
        lay_prov.addLayout(header_prov)

        self.tabla_prov = QTableWidget(0, 4)
        self.tabla_prov.setHorizontalHeaderLabels(["Nombre", "Teléfono", "Email", "Notas"])
        self.tabla_prov.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tabla_prov.setAlternatingRowColors(True)
        self.tabla_prov.verticalHeader().setVisible(False)
        lay_prov.addWidget(self.tabla_prov)
        self._cargar_proveedores()
        tabs.addTab(tab_prov, "🚚  Proveedores")

        # ── Tab: Acerca de ─────────────────────────────────
        tab_about = QWidget()
        lay_about = QVBoxLayout(tab_about)
        lay_about.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay_about.setSpacing(10)

        lbl_logo = QLabel("🍷")
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_logo.setStyleSheet("font-size: 60pt;")
        lay_about.addWidget(lbl_logo)

        from version import VERSION_ACTUAL
        for texto, estilo in [
            ("Vinoteca — Sistema de Gestión", "font-size:16pt; font-weight:800; color:#C9A84C;"),
            (f"Versión {VERSION_ACTUAL}", "color:#888; font-size:11pt;"),
            ("Desarrollado con Python + PyQt6", "color:#666; font-size:10pt;"),
        ]:
            lbl = QLabel(texto)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(estilo)
            lay_about.addWidget(lbl)

        lay_about.addSpacing(16)

        self.lbl_update_estado = QLabel("")
        self.lbl_update_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_update_estado.setStyleSheet("color:#AAAAAA; font-size:10pt;")
        lay_about.addWidget(self.lbl_update_estado)

        btn_check = QPushButton("🔄  Buscar actualización")
        btn_check.setObjectName("btn_secundario")
        btn_check.setFixedWidth(220)
        btn_check.clicked.connect(lambda: self._buscar_actualizacion(VERSION_ACTUAL))
        lay_about.addWidget(btn_check, alignment=Qt.AlignmentFlag.AlignCenter)

        tabs.addTab(tab_about, "ℹ️  Acerca de")

        lay.addWidget(tabs, 1)

    def _buscar_actualizacion(self, version_actual: str):
        from config import GITHUB_USUARIO, GITHUB_REPO, BASE_DIR
        from sync.updater import UpdateChecker, DialogoActualizacion

        self.lbl_update_estado.setText("Buscando actualizaciones...")
        self.lbl_update_estado.setStyleSheet("color:#AAAAAA; font-size:10pt;")

        self._checker = UpdateChecker(GITHUB_USUARIO, GITHUB_REPO, version_actual)

        def _on_update(version_nueva, download_url):
            self.lbl_update_estado.setText(f"¡Nueva versión disponible: v{version_nueva}!")
            self.lbl_update_estado.setStyleSheet("color:#C9A84C; font-size:10pt; font-weight:700;")
            dlg = DialogoActualizacion(version_nueva, download_url, version_actual, BASE_DIR, self)
            dlg.exec()

        def _on_finished():
            if self.lbl_update_estado.text() == "Buscando actualizaciones...":
                self.lbl_update_estado.setText("✅  Ya tenés la versión más reciente.")
                self.lbl_update_estado.setStyleSheet("color:#4CAF50; font-size:10pt;")

        self._checker.update_disponible.connect(_on_update)
        self._checker.finished.connect(_on_finished)
        self._checker.start()

    def _cargar_config(self):
        self.txt_nombre_negocio.setText(db.get_config("nombre_negocio", "La Vinoteca"))
        self.txt_moneda.setText(db.get_config("moneda", "$"))
        self.spin_stock_min.setValue(int(db.get_config("stock_min_alerta", 3)))
        self.spin_dias_venc.setValue(int(db.get_config("dias_alerta_vencimiento", 30)))
        self.txt_sql_server.setText(db.get_config("sql_server", ""))
        self.txt_sql_db.setText(db.get_config("sql_database", "vinoteca"))
        self.txt_sql_user.setText(db.get_config("sql_username", ""))
        self.txt_sql_pass.setText(db.get_config("sql_password", ""))

    def _guardar_config(self):
        db.set_config("nombre_negocio", self.txt_nombre_negocio.text())
        db.set_config("moneda", self.txt_moneda.text())
        db.set_config("stock_min_alerta", self.spin_stock_min.value(), "int")
        db.set_config("dias_alerta_vencimiento", self.spin_dias_venc.value(), "int")
        QMessageBox.information(self, "✅  Guardado", "Configuración guardada correctamente.")

    def _guardar_sql(self):
        db.set_config("sql_server",   self.txt_sql_server.text())
        db.set_config("sql_database", self.txt_sql_db.text())
        db.set_config("sql_username", self.txt_sql_user.text())
        db.set_config("sql_password", self.txt_sql_pass.text())
        QMessageBox.information(self, "✅  Guardado", "Configuración SQL Server guardada.")

    def _probar_sql(self):
        try:
            import pyodbc
            server   = self.txt_sql_server.text()
            database = self.txt_sql_db.text()
            username = self.txt_sql_user.text()
            password = self.txt_sql_pass.text()
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server};DATABASE={database};"
                f"UID={username};PWD={password}"
            )
            conn = pyodbc.connect(conn_str, timeout=5)
            conn.close()
            QMessageBox.information(self, "✅  Conexión exitosa",
                                    "La conexión a SQL Server funcionó correctamente.")
        except ImportError:
            QMessageBox.warning(self, "pyodbc no instalado",
                                "Ejecutá: pip install pyodbc")
        except Exception as e:
            QMessageBox.critical(self, "Error de conexión", str(e))

    def _cargar_categorias(self):
        cats = db.obtener_categorias()
        self.tabla_cats.setRowCount(len(cats))
        for i, c in enumerate(cats):
            self.tabla_cats.setItem(i, 0, QTableWidgetItem(str(c["id"])))
            self.tabla_cats.setItem(i, 1, QTableWidgetItem(c["nombre"]))
            self.tabla_cats.setItem(i, 2, QTableWidgetItem(c["descripcion"] or ""))

    def _nueva_categoria(self):
        from PyQt6.QtWidgets import QInputDialog
        nombre, ok = QInputDialog.getText(self, "Nueva categoría", "Nombre:")
        if ok and nombre.strip():
            from db.database import get_connection
            with get_connection() as conn:
                conn.execute("INSERT OR IGNORE INTO categorias (nombre) VALUES (?)",
                             (nombre.strip(),))
            self._cargar_categorias()

    def _cargar_proveedores(self):
        provs = db.obtener_proveedores()
        self.tabla_prov.setRowCount(len(provs))
        for i, p in enumerate(provs):
            self.tabla_prov.setItem(i, 0, QTableWidgetItem(p["nombre"]))
            self.tabla_prov.setItem(i, 1, QTableWidgetItem(p["telefono"] or ""))
            self.tabla_prov.setItem(i, 2, QTableWidgetItem(p["email"] or ""))
            self.tabla_prov.setItem(i, 3, QTableWidgetItem(p["notas"] or ""))

    def _nuevo_proveedor(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Nuevo Proveedor")
        dlg.setMinimumWidth(380)
        lay = QVBoxLayout(dlg)
        form = QFormLayout()
        txt_nombre = QLineEdit()
        txt_tel    = QLineEdit()
        txt_email  = QLineEdit()
        txt_notas  = QLineEdit()
        form.addRow("Nombre *:", txt_nombre)
        form.addRow("Teléfono:", txt_tel)
        form.addRow("Email:",    txt_email)
        form.addRow("Notas:",    txt_notas)
        lay.addLayout(form)
        btn_row = QHBoxLayout()
        btn_ok = QPushButton("Guardar")
        btn_ok.clicked.connect(dlg.accept)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("btn_secundario")
        btn_cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        lay.addLayout(btn_row)
        if dlg.exec() == QDialog.DialogCode.Accepted and txt_nombre.text().strip():
            db.crear_proveedor(txt_nombre.text(), txt_tel.text(),
                               txt_email.text(), txt_notas.text())
            self._cargar_proveedores()
