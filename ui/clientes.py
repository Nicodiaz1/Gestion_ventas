# ─────────────────────────────────────────────────────────────
#  ui/clientes.py  –  Gestión de clientes y cuenta corriente (fiado)
# ─────────────────────────────────────────────────────────────

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QLineEdit, QSpinBox, QTextEdit, QMessageBox,
    QAbstractItemView, QFrame, QTabWidget, QDoubleSpinBox,
    QCompleter, QSizePolicy, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QStringListModel, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from db import database as db


# ─────────────────────────────────────────────────────────────
#  Diálogo: nuevo / editar cliente
# ─────────────────────────────────────────────────────────────

class DialogoCliente(QDialog):
    def __init__(self, parent=None, cliente: dict = None):
        super().__init__(parent)
        self._cliente = cliente
        es_nuevo = cliente is None
        self.setWindowTitle("Nuevo cliente" if es_nuevo else "Editar cliente")
        self.setMinimumWidth(420)
        self.setModal(True)
        self._build_ui()
        if not es_nuevo:
            self._cargar_datos()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(24, 20, 24, 20)

        titulo = QLabel("👤  " + self.windowTitle())
        titulo.setObjectName("titulo_seccion")
        lay.addWidget(titulo)

        form = QFormLayout()
        form.setSpacing(10)

        self.txt_nombre   = QLineEdit()
        self.txt_nombre.setPlaceholderText("Nombre *")
        form.addRow("Nombre *:", self.txt_nombre)

        self.txt_apellido = QLineEdit()
        self.txt_apellido.setPlaceholderText("Apellido")
        form.addRow("Apellido:", self.txt_apellido)

        self.txt_telefono = QLineEdit()
        self.txt_telefono.setPlaceholderText("Ej: 11-1234-5678")
        form.addRow("Teléfono:", self.txt_telefono)

        self.spin_edad = QSpinBox()
        self.spin_edad.setRange(0, 120)
        self.spin_edad.setValue(0)
        self.spin_edad.setSpecialValueText("—")   # 0 muestra "—"
        form.addRow("Edad:", self.spin_edad)

        self.txt_notas = QTextEdit()
        self.txt_notas.setMaximumHeight(70)
        self.txt_notas.setPlaceholderText("Notas opcionales…")
        form.addRow("Notas:", self.txt_notas)

        lay.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("btn_secundario")
        btn_cancel.setAutoDefault(False)
        btn_cancel.setDefault(False)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_ok = QPushButton("💾  Guardar")
        btn_ok.setAutoDefault(False)
        btn_ok.setDefault(False)
        btn_ok.clicked.connect(self._guardar)
        btn_row.addWidget(btn_ok)
        lay.addLayout(btn_row)

        # Enter-navigation
        self.txt_nombre.returnPressed.connect(self.txt_apellido.setFocus)
        self.txt_apellido.returnPressed.connect(self.txt_telefono.setFocus)
        self.txt_telefono.returnPressed.connect(self.spin_edad.setFocus)

    def _cargar_datos(self):
        c = self._cliente
        self.txt_nombre.setText(c.get("nombre") or "")
        self.txt_apellido.setText(c.get("apellido") or "")
        self.txt_telefono.setText(c.get("telefono") or "")
        self.spin_edad.setValue(c.get("edad") or 0)
        self.txt_notas.setPlainText(c.get("notas") or "")

    def _guardar(self):
        nombre = self.txt_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Nombre requerido", "Ingresá el nombre del cliente.")
            self.txt_nombre.setFocus()
            return
        datos = {
            "nombre":   nombre,
            "apellido": self.txt_apellido.text().strip(),
            "telefono": self.txt_telefono.text().strip(),
            "edad":     self.spin_edad.value() or None,
            "notas":    self.txt_notas.toPlainText().strip(),
        }
        try:
            if self._cliente:
                db.actualizar_cliente(self._cliente["id"], datos)
            else:
                db.crear_cliente(datos)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


# ─────────────────────────────────────────────────────────────
#  Diálogo: detalle de cliente (movimientos + estadísticas)
# ─────────────────────────────────────────────────────────────

class DialogoDetalleCliente(QDialog):
    def __init__(self, cliente: dict, parent=None):
        super().__init__(parent)
        self._cliente = cliente
        nombre_completo = f"{cliente['nombre']} {cliente.get('apellido') or ''}".strip()
        self.setWindowTitle(f"Cuenta de {nombre_completo}")
        self.setMinimumWidth(560)
        self.setMinimumHeight(500)
        self.setModal(True)
        self._build_ui()
        self._cargar()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(20, 16, 20, 16)

        # Encabezado
        nombre_completo = f"{self._cliente['nombre']} {self._cliente.get('apellido') or ''}".strip()
        titulo = QLabel(f"👤  {nombre_completo}")
        titulo.setObjectName("titulo_seccion")
        lay.addWidget(titulo)

        # Info básica
        info_parts = []
        if self._cliente.get("telefono"):
            info_parts.append(f"📞 {self._cliente['telefono']}")
        if self._cliente.get("edad"):
            info_parts.append(f"🎂 {self._cliente['edad']} años")
        if info_parts:
            lbl_info = QLabel("   ·   ".join(info_parts))
            lbl_info.setStyleSheet("color:#888; font-size:10pt;")
            lay.addWidget(lbl_info)

        # Tarjetas de estadísticas
        stats_row = QHBoxLayout()
        self._stats_row = stats_row   # debe asignarse ANTES de llamar a _card()
        self.lbl_saldo     = self._card("DEUDA ACTUAL",    "$ 0",  "#FF9800")
        self.lbl_visitas   = self._card("VISITAS",         "0",    "#C9A84C")
        self.lbl_comprado  = self._card("TOTAL COMPRADO",  "$ 0",  "#4CAF50")
        self.lbl_ticket    = self._card("TICKET PROM.",    "$ 0",  "#2196F3")
        lay.addLayout(stats_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#333;")
        lay.addWidget(sep)

        # Botón abonar
        abono_row = QHBoxLayout()
        lbl_abono = QLabel("Registrar abono de deuda:")
        lbl_abono.setStyleSheet("color:#AAAAAA; font-size:10pt;")
        abono_row.addWidget(lbl_abono)
        self.spin_abono = QDoubleSpinBox()
        self.spin_abono.setRange(0.01, 9_999_999)
        self.spin_abono.setDecimals(2)
        self.spin_abono.setPrefix("$ ")
        self.spin_abono.setSingleStep(100)
        self.spin_abono.setFixedWidth(140)
        abono_row.addWidget(self.spin_abono)
        btn_abonar = QPushButton("💳  Abonar")
        btn_abonar.setStyleSheet(
            "QPushButton{background:#2E7D32;color:white;font-weight:700;"
            "border-radius:6px;padding:6px 14px;}"
            "QPushButton:hover{background:#388E3C;}")
        btn_abonar.clicked.connect(self._registrar_abono)
        abono_row.addWidget(btn_abonar)
        abono_row.addStretch()
        lay.addLayout(abono_row)

        # Tabla de movimientos
        lbl_mov = QLabel("Historial de movimientos")
        lbl_mov.setStyleSheet("color:#888; font-size:9pt; font-weight:700;")
        lay.addWidget(lbl_mov)

        self.tabla = QTableWidget(0, 4)
        self.tabla.setHorizontalHeaderLabels(["Fecha", "Tipo", "Monto", "Descripción"])
        hdr = self.tabla.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        lay.addWidget(self.tabla, 1)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setObjectName("btn_secundario")
        btn_cerrar.clicked.connect(self.accept)
        lay.addWidget(btn_cerrar, alignment=Qt.AlignmentFlag.AlignRight)

    def _card(self, titulo: str, valor: str, color: str) -> QLabel:
        card = QFrame()
        card.setObjectName("card_widget")
        card.setMinimumWidth(120)
        cl = QVBoxLayout(card)
        cl.setSpacing(4)
        cl.setContentsMargins(12, 8, 12, 8)
        lbl_t = QLabel(titulo)
        lbl_t.setObjectName("card_titulo")
        lbl_v = QLabel(valor)
        lbl_v.setStyleSheet(f"font-size:14pt; font-weight:800; color:{color};")
        cl.addWidget(lbl_t)
        cl.addWidget(lbl_v)
        self._stats_row.addWidget(card)
        return lbl_v

    def _cargar(self):
        saldo = db.saldo_cliente(self._cliente["id"])
        stats = db.estadisticas_cliente(self._cliente["id"])
        movimientos = db.obtener_movimientos_cliente(self._cliente["id"])

        color_saldo = "#F44336" if saldo > 0 else "#4CAF50"
        self.lbl_saldo.setStyleSheet(
            f"font-size:14pt; font-weight:800; color:{color_saldo};")
        self.lbl_saldo.setText(f"$ {saldo:,.2f}" if saldo != 0 else "$ 0  ✅")
        self.lbl_visitas.setText(str(stats["total_visitas"]))
        self.lbl_comprado.setText(f"$ {stats['total_comprado']:,.0f}")
        self.lbl_ticket.setText(f"$ {stats['ticket_promedio']:,.0f}")

        self.tabla.setRowCount(len(movimientos))
        for i, m in enumerate(movimientos):
            fecha = str(m["fecha"])[:16].replace("T", "  ")
            tipo  = m["tipo"]
            monto = m["monto"]
            desc  = m.get("descripcion") or ""
            if m.get("venta_id"):
                desc = f"Venta #{m['venta_id']}" + (f" — {desc}" if desc else "")

            color = "#F44336" if tipo == "cargo" else "#4CAF50"
            tipo_txt = "⬆ Cargo" if tipo == "cargo" else "⬇ Abono"

            def _c(txt, clr=None, al=Qt.AlignmentFlag.AlignLeft):
                it = QTableWidgetItem(txt)
                it.setTextAlignment(al | Qt.AlignmentFlag.AlignVCenter)
                if clr:
                    it.setForeground(QColor(clr))
                return it

            self.tabla.setItem(i, 0, _c(fecha, "#AAAAAA"))
            self.tabla.setItem(i, 1, _c(tipo_txt, color))
            self.tabla.setItem(i, 2, _c(f"$ {monto:,.2f}", color,
                                        Qt.AlignmentFlag.AlignRight))
            self.tabla.setItem(i, 3, _c(desc))
            self.tabla.setRowHeight(i, 34)

    def _registrar_abono(self):
        monto = self.spin_abono.value()
        saldo_actual = db.saldo_cliente(self._cliente["id"])
        if saldo_actual <= 0:
            QMessageBox.information(self, "Sin deuda",
                "Este cliente no tiene deuda pendiente.")
            return
        nombre = f"{self._cliente['nombre']} {self._cliente.get('apellido') or ''}".strip()
        resp = QMessageBox.question(
            self, "Confirmar abono",
            f"Registrar abono de ${monto:,.2f} para {nombre}?\n"
            f"Deuda actual: ${saldo_actual:,.2f}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp == QMessageBox.StandardButton.Yes:
            db.registrar_movimiento_fiado(
                self._cliente["id"], "abono", monto, "Abono manual")
            self._cargar()


# ─────────────────────────────────────────────────────────────
#  Widget principal de Clientes
# ─────────────────────────────────────────────────────────────

class ClientesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.cargar()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(16, 16, 16, 16)

        # Encabezado
        header = QHBoxLayout()
        titulo = QLabel("👥  Clientes")
        titulo.setObjectName("titulo_seccion")
        header.addWidget(titulo, 1)
        btn_nuevo = QPushButton("➕  Nuevo cliente")
        btn_nuevo.clicked.connect(self._nuevo_cliente)
        header.addWidget(btn_nuevo)
        lay.addLayout(header)

        # Tarjetas resumen
        self._resumen_row = QHBoxLayout()
        lay.addLayout(self._resumen_row)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # ── Tab 1: Todos los clientes ──────────────────────────
        tab_todos = QWidget()
        lay_todos = QVBoxLayout(tab_todos)
        lay_todos.setSpacing(6)

        buscar_row = QHBoxLayout()
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("🔍  Buscar por nombre, apellido o teléfono…")
        self.txt_buscar.setClearButtonEnabled(True)
        self.txt_buscar.textChanged.connect(lambda t: self._filtrar(t))
        buscar_row.addWidget(self.txt_buscar)
        lay_todos.addLayout(buscar_row)

        self.tabla_clientes = QTableWidget(0, 6)
        self.tabla_clientes.setHorizontalHeaderLabels(
            ["Nombre", "Apellido", "Teléfono", "Edad", "Deuda", "Acciones"])
        hdr = self.tabla_clientes.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.tabla_clientes.setColumnWidth(5, 220)
        self.tabla_clientes.verticalHeader().setVisible(False)
        self.tabla_clientes.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_clientes.setAlternatingRowColors(True)
        self.tabla_clientes.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_clientes.itemDoubleClicked.connect(self._doble_click)
        lay_todos.addWidget(self.tabla_clientes, 1)
        self.tabs.addTab(tab_todos, "📋  Todos los clientes")

        # ── Tab 2: Con deuda ──────────────────────────────────
        tab_deuda = QWidget()
        lay_deuda = QVBoxLayout(tab_deuda)
        lay_deuda.setSpacing(6)
        self.tabla_deuda = QTableWidget(0, 5)
        self.tabla_deuda.setHorizontalHeaderLabels(
            ["Nombre", "Apellido", "Teléfono", "Deuda", "Acciones"])
        hdr2 = self.tabla_deuda.horizontalHeader()
        hdr2.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr2.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr2.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr2.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr2.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.tabla_deuda.setColumnWidth(4, 180)
        self.tabla_deuda.verticalHeader().setVisible(False)
        self.tabla_deuda.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_deuda.setAlternatingRowColors(True)
        self.tabla_deuda.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_deuda.itemDoubleClicked.connect(
            lambda item: self._abrir_detalle(
                item.data(Qt.ItemDataRole.UserRole)))
        lay_deuda.addWidget(self.tabla_deuda, 1)
        self.tabs.addTab(tab_deuda, "💳  Con deuda")

        self.tabs.currentChanged.connect(self._tab_changed)
        lay.addWidget(self.tabs, 1)

    def _card_resumen(self, titulo: str, valor: str, color: str) -> QLabel:
        card = QFrame()
        card.setObjectName("card_widget")
        card.setMinimumWidth(140)
        cl = QVBoxLayout(card)
        cl.setSpacing(4)
        cl.setContentsMargins(14, 10, 14, 10)
        lbl_t = QLabel(titulo)
        lbl_t.setObjectName("card_titulo")
        lbl_v = QLabel(valor)
        lbl_v.setStyleSheet(f"font-size:18pt; font-weight:800; color:{color};")
        cl.addWidget(lbl_t)
        cl.addWidget(lbl_v)
        self._resumen_row.addWidget(card)
        return lbl_v

    def cargar(self):
        self._todos_los_clientes = [dict(c) for c in db.obtener_clientes()]
        self._saldos = {c["id"]: db.saldo_cliente(c["id"])
                        for c in self._todos_los_clientes}
        self._rebuild_resumen()
        self._mostrar_clientes(self._todos_los_clientes)
        self._cargar_tab_deuda()

    def _rebuild_resumen(self):
        while self._resumen_row.count():
            item = self._resumen_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total_clientes = len(self._todos_los_clientes)
        con_deuda      = sum(1 for s in self._saldos.values() if s > 0)
        deuda_total    = sum(s for s in self._saldos.values() if s > 0)

        self._card_resumen("CLIENTES",    str(total_clientes), "#C9A84C")
        self._card_resumen("CON DEUDA",   str(con_deuda),      "#F44336")
        self._card_resumen("DEUDA TOTAL", f"$ {deuda_total:,.2f}", "#FF9800")
        self._resumen_row.addStretch()

    def _filtrar(self, texto: str):
        texto = texto.strip().lower()
        if not texto:
            filtrados = self._todos_los_clientes
        else:
            filtrados = [
                c for c in self._todos_los_clientes
                if texto in (c.get("nombre") or "").lower()
                or texto in (c.get("apellido") or "").lower()
                or texto in (c.get("telefono") or "").lower()
            ]
        self._mostrar_clientes(filtrados)

    def _mostrar_clientes(self, clientes: list):
        self.tabla_clientes.setRowCount(len(clientes))
        for i, c in enumerate(clientes):
            saldo = self._saldos.get(c["id"], 0)

            def _it(txt, color=None, bold=False, align=Qt.AlignmentFlag.AlignLeft):
                item = QTableWidgetItem(str(txt) if txt else "—")
                item.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if color:
                    item.setForeground(QColor(color))
                if bold:
                    f = QFont(); f.setBold(True); item.setFont(f)
                item.setData(Qt.ItemDataRole.UserRole, c["id"])
                return item

            self.tabla_clientes.setItem(i, 0, _it(c.get("nombre"), bold=True))
            self.tabla_clientes.setItem(i, 1, _it(c.get("apellido")))
            self.tabla_clientes.setItem(i, 2, _it(c.get("telefono")))
            self.tabla_clientes.setItem(i, 3, _it(
                c.get("edad") or "—", align=Qt.AlignmentFlag.AlignCenter))

            saldo_color = "#F44336" if saldo > 0.01 else "#4CAF50"
            saldo_txt   = f"$ {saldo:,.2f}" if saldo > 0.01 else "✅ Sin deuda"
            it_saldo = QTableWidgetItem(saldo_txt)
            it_saldo.setForeground(QColor(saldo_color))
            it_saldo.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            it_saldo.setData(Qt.ItemDataRole.UserRole, c["id"])
            if saldo > 0.01:
                f = QFont(); f.setBold(True); it_saldo.setFont(f)
            self.tabla_clientes.setItem(i, 4, it_saldo)

            # Botones de acción
            cdict = dict(c)
            acc = QWidget()
            acc_lay = QHBoxLayout(acc)
            acc_lay.setContentsMargins(4, 2, 4, 2)
            acc_lay.setSpacing(4)

            btn_ver = QPushButton("👁 Ver")
            btn_ver.setFixedHeight(28)
            btn_ver.setStyleSheet(
                "QPushButton{background:#1565C0;color:white;border-radius:5px;"
                "font-size:9pt;padding:0 8px;}"
                "QPushButton:hover{background:#1976D2;}")
            btn_ver.clicked.connect(lambda _, cd=cdict: self._abrir_detalle(cd["id"]))
            acc_lay.addWidget(btn_ver)

            btn_edit = QPushButton("✏ Editar")
            btn_edit.setFixedHeight(28)
            btn_edit.setStyleSheet(
                "QPushButton{background:#2C2C2C;border:1px solid #555;border-radius:5px;"
                "color:#F5F5F5;font-size:9pt;padding:0 8px;}"
                "QPushButton:hover{background:#3C3C3C;}")
            btn_edit.clicked.connect(lambda _, cd=cdict: self._editar_cliente(cd))
            acc_lay.addWidget(btn_edit)

            btn_del = QPushButton("🗑")
            btn_del.setFixedHeight(28)
            btn_del.setFixedWidth(36)
            btn_del.setStyleSheet(
                "QPushButton{background:#7F0000;color:white;border-radius:5px;"
                "font-size:9pt;}"
                "QPushButton:hover{background:#B71C1C;}")
            btn_del.clicked.connect(lambda _, cd=cdict: self._eliminar_cliente(cd))
            acc_lay.addWidget(btn_del)

            self.tabla_clientes.setCellWidget(i, 5, acc)
            self.tabla_clientes.setRowHeight(i, 42)

    def _cargar_tab_deuda(self):
        con_deuda = [c for c in self._todos_los_clientes
                     if self._saldos.get(c["id"], 0) > 0.01]
        con_deuda.sort(key=lambda c: self._saldos.get(c["id"], 0), reverse=True)

        self.tabs.setTabText(1, f"💳  Con deuda ({len(con_deuda)})" if con_deuda
                             else "💳  Con deuda")
        self.tabla_deuda.setRowCount(len(con_deuda))
        for i, c in enumerate(con_deuda):
            saldo = self._saldos.get(c["id"], 0)
            cdict = dict(c)

            def _it(txt, color=None, bold=False, align=Qt.AlignmentFlag.AlignLeft):
                item = QTableWidgetItem(str(txt) if txt else "—")
                item.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if color:
                    item.setForeground(QColor(color))
                if bold:
                    f = QFont(); f.setBold(True); item.setFont(f)
                item.setData(Qt.ItemDataRole.UserRole, cdict)
                return item

            self.tabla_deuda.setItem(i, 0, _it(c.get("nombre"), bold=True))
            self.tabla_deuda.setItem(i, 1, _it(c.get("apellido")))
            self.tabla_deuda.setItem(i, 2, _it(c.get("telefono")))
            self.tabla_deuda.setItem(i, 3, _it(
                f"$ {saldo:,.2f}", "#F44336", bold=True,
                align=Qt.AlignmentFlag.AlignRight))

            acc = QWidget()
            acc_lay = QHBoxLayout(acc)
            acc_lay.setContentsMargins(4, 2, 4, 2)
            acc_lay.setSpacing(4)

            btn_ver = QPushButton("👁 Ver cuenta")
            btn_ver.setFixedHeight(28)
            btn_ver.setStyleSheet(
                "QPushButton{background:#1565C0;color:white;border-radius:5px;"
                "font-size:9pt;padding:0 8px;}"
                "QPushButton:hover{background:#1976D2;}")
            btn_ver.clicked.connect(lambda _, cd=cdict: self._abrir_detalle(cd["id"]))
            acc_lay.addWidget(btn_ver)

            self.tabla_deuda.setCellWidget(i, 4, acc)
            self.tabla_deuda.setRowHeight(i, 42)

    def _tab_changed(self, idx):
        if idx in (0, 1):
            self.cargar()

    def _doble_click(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(data, dict):
            cliente_id = data.get("id")
        elif isinstance(data, int):
            cliente_id = data
        else:
            return
        if cliente_id:
            self._abrir_detalle(cliente_id)

    def _abrir_detalle(self, cliente_id: int):
        c = db.obtener_cliente(cliente_id)
        if c:
            dlg = DialogoDetalleCliente(dict(c), self)
            dlg.exec()
            self.cargar()

    def _nuevo_cliente(self):
        dlg = DialogoCliente(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.cargar()

    def _editar_cliente(self, cliente: dict):
        dlg = DialogoCliente(self, cliente=cliente)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.cargar()

    def _eliminar_cliente(self, cliente: dict):
        nombre = f"{cliente['nombre']} {cliente.get('apellido') or ''}".strip()
        saldo  = self._saldos.get(cliente["id"], 0)
        if saldo > 0.01:
            QMessageBox.warning(
                self, "No se puede eliminar",
                f"{nombre} tiene una deuda pendiente de ${saldo:,.2f}.\n"
                "Cancelá la deuda antes de eliminar el cliente.")
            return
        resp = QMessageBox.question(
            self, "Eliminar cliente",
            f"¿Eliminar a {nombre}?\nSe borrará su historial de movimientos.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp == QMessageBox.StandardButton.Yes:
            db.eliminar_cliente(cliente["id"])
            self.cargar()


# ─────────────────────────────────────────────────────────────
#  Mini-popup para buscar y asignar un cliente desde el POS
# ─────────────────────────────────────────────────────────────

class BuscadorClientes(QDialog):
    """Popup compacto para asignar un cliente a la venta actual."""
    cliente_seleccionado = pyqtSignal(dict)   # emite dict del cliente

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Asignar cliente")
        self.setMinimumWidth(440)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(20, 16, 20, 16)

        titulo = QLabel("👤  Asignar cliente a la venta")
        titulo.setObjectName("titulo_seccion")
        lay.addWidget(titulo)

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Escribí el nombre o apellido…")
        self.txt_buscar.textChanged.connect(self._buscar)
        lay.addWidget(self.txt_buscar)

        self.lista = QListWidget()
        self.lista.setAlternatingRowColors(True)
        self.lista.setMinimumHeight(200)
        self.lista.itemDoubleClicked.connect(self._seleccionar)
        lay.addWidget(self.lista)

        btn_row = QHBoxLayout()
        btn_sel = QPushButton("✔  Asignar")
        btn_sel.clicked.connect(self._seleccionar)
        btn_row.addWidget(btn_sel)

        btn_nuevo = QPushButton("➕  Nuevo cliente")
        btn_nuevo.setObjectName("btn_secundario")
        btn_nuevo.clicked.connect(self._nuevo_cliente)
        btn_row.addWidget(btn_nuevo)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("btn_secundario")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        lay.addLayout(btn_row)

        self._buscar("")
        self.txt_buscar.setFocus()

    def _buscar(self, texto: str):
        self.lista.clear()
        clientes = db.obtener_clientes(texto.strip())
        for c in clientes:
            saldo = db.saldo_cliente(c["id"])
            nombre_completo = f"{c['nombre']} {c.get('apellido') or ''}".strip()
            tel = c.get("telefono") or ""
            deuda_txt = f"  |  💳 Debe: ${saldo:,.2f}" if saldo > 0.01 else ""
            label = f"{nombre_completo}{('  |  📞 ' + tel) if tel else ''}{deuda_txt}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, dict(c))
            if saldo > 0.01:
                item.setForeground(QColor("#FF9800"))
            self.lista.addItem(item)

    def _seleccionar(self, *_):
        current = self.lista.currentItem()
        if current:
            self.cliente_seleccionado.emit(current.data(Qt.ItemDataRole.UserRole))
            self.accept()

    def _nuevo_cliente(self):
        dlg = DialogoCliente(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._buscar(self.txt_buscar.text())
