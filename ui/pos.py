# ─────────────────────────────────────────────────────────────
#  ui/pos.py  –  Punto de Venta (POS)
# ─────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QGridLayout, QScrollArea, QFrame,
    QButtonGroup, QSpinBox, QDoubleSpinBox, QAbstractItemView,
    QListWidget, QListWidgetItem, QSplitter, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize
from PyQt6.QtGui import QFont, QKeySequence, QShortcut, QColor
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import database as db


# ─────────────────────────────────────────────────────────────
#  Widget de búsqueda rápida por nombre (para sin código)
# ─────────────────────────────────────────────────────────────

class BuscadorProductos(QDialog):
    producto_seleccionado = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Buscar Producto")
        self.setMinimumSize(560, 440)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("🔍  Buscar por nombre")
        lbl.setObjectName("titulo_seccion")
        lay.addWidget(lbl)

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Escribí el nombre del producto…")
        self.txt_buscar.textChanged.connect(self._buscar)
        lay.addWidget(self.txt_buscar)

        self.lista = QListWidget()
        self.lista.setAlternatingRowColors(True)
        self.lista.itemDoubleClicked.connect(self._seleccionar)
        self.lista.setMinimumHeight(280)
        lay.addWidget(self.lista)

        btn_row = QHBoxLayout()
        btn_sel = QPushButton("✔  Seleccionar")
        btn_sel.clicked.connect(self._seleccionar)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("btn_secundario")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_sel)
        btn_row.addWidget(btn_cancel)
        lay.addLayout(btn_row)

        self._buscar("")

    def _buscar(self, texto: str):
        self.lista.clear()
        resultados = db.buscar_por_nombre(texto) if texto else db.obtener_todos_productos()
        for p in resultados:
            item = QListWidgetItem(
                f"{p['nombre']}  |  ${p['precio_venta']:.2f}  |  Stock: {p['stock_actual']}"
            )
            item.setData(Qt.ItemDataRole.UserRole, dict(p))
            self.lista.addItem(item)

    def _seleccionar(self, *_):
        current = self.lista.currentItem()
        if current:
            self.producto_seleccionado.emit(current.data(Qt.ItemDataRole.UserRole))
            self.accept()


# ─────────────────────────────────────────────────────────────
#  Fila del carrito
# ─────────────────────────────────────────────────────────────

class ItemCarrito:
    def __init__(self, producto: dict, cantidad: int = 1):
        self.producto_id  = producto["id"]
        self.nombre       = producto["nombre"]
        self.precio_unit  = float(producto["precio_venta"])
        self.cantidad     = cantidad
        self.stock_actual = producto["stock_actual"]

    @property
    def subtotal(self) -> float:
        return self.precio_unit * self.cantidad


# ─────────────────────────────────────────────────────────────
#  Panel de POS principal
# ─────────────────────────────────────────────────────────────

class PosWidget(QWidget):
    venta_realizada = pyqtSignal(int)   # emite venta_id

    MEDIOS_PAGO = [
        ("💵 Efectivo",      "efectivo",      "mp_efectivo"),
        ("💳 Débito",         "debito",        "mp_debito"),
        ("🏦 Crédito",       "credito",       "mp_credito"),
        ("📲 Transferencia", "transferencia", "mp_transferencia"),
        ("🔲 QR",            "qr",            "mp_qr"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.carrito: list[ItemCarrito] = []
        self.medio_pago_actual = "efectivo"
        self._build_ui()
        self._setup_shortcuts()
        # Auto-foco en escaneo al abrir
        QTimer.singleShot(100, self.scan_input.setFocus)

    # ── Construcción de UI ────────────────────────────────────

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # Panel izquierdo: escaneo + carrito
        izq = QWidget()
        izq.setMinimumWidth(520)
        lay_izq = QVBoxLayout(izq)
        lay_izq.setSpacing(10)
        lay_izq.setContentsMargins(16, 16, 8, 16)

        # Título
        titulo = QLabel("🛒  Punto de Venta")
        titulo.setObjectName("titulo_seccion")
        lay_izq.addWidget(titulo)

        # Barra de escaneo
        scan_row = QHBoxLayout()
        self.scan_input = QLineEdit()
        self.scan_input.setObjectName("scan_input")
        self.scan_input.setPlaceholderText("📷  Escaneá o escribí el código de barras y presioná Enter…")
        self.scan_input.returnPressed.connect(self._procesar_escaneo)
        scan_row.addWidget(self.scan_input, 1)

        btn_buscar = QPushButton("🔍  Buscar")
        btn_buscar.setToolTip("Buscar producto por nombre (F2)")
        btn_buscar.clicked.connect(self._abrir_buscador)
        btn_buscar.setMinimumWidth(110)
        scan_row.addWidget(btn_buscar)
        lay_izq.addLayout(scan_row)

        lbl_hint = QLabel("Tip: presioná F2 para buscar por nombre  |  F12 para cobrar")
        lbl_hint.setStyleSheet("color: #666; font-size: 9pt;")
        lay_izq.addWidget(lbl_hint)

        # Tabla del carrito
        self.tabla = QTableWidget(0, 5)
        self.tabla.setHorizontalHeaderLabels(["Producto", "Precio unit.", "Cant.", "Subtotal", ""])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setMinimumHeight(300)
        lay_izq.addWidget(self.tabla, 1)

        # Total y descuento
        totales_row = QHBoxLayout()
        desc_lay = QVBoxLayout()
        lbl_desc = QLabel("Descuento ($):")
        lbl_desc.setStyleSheet("color:#AAAAAA; font-size:10pt;")
        self.spin_descuento = QDoubleSpinBox()
        self.spin_descuento.setRange(0, 999999)
        self.spin_descuento.setDecimals(2)
        self.spin_descuento.setSingleStep(50)
        self.spin_descuento.valueChanged.connect(self._actualizar_total)
        desc_lay.addWidget(lbl_desc)
        desc_lay.addWidget(self.spin_descuento)
        totales_row.addLayout(desc_lay)
        totales_row.addStretch()

        total_lay = QVBoxLayout()
        lbl_tit_total = QLabel("TOTAL A COBRAR")
        lbl_tit_total.setStyleSheet("color:#AAAAAA; font-size:10pt; font-weight:600;")
        lbl_tit_total.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_total = QLabel("$0.00")
        self.lbl_total.setObjectName("precio_total")
        self.lbl_total.setAlignment(Qt.AlignmentFlag.AlignRight)
        total_lay.addWidget(lbl_tit_total)
        total_lay.addWidget(self.lbl_total)
        totales_row.addLayout(total_lay)
        lay_izq.addLayout(totales_row)

        splitter.addWidget(izq)

        # Panel derecho: medios de pago + cobrar + últimas ventas
        der = QWidget()
        der.setMaximumWidth(340)
        der.setMinimumWidth(280)
        lay_der = QVBoxLayout(der)
        lay_der.setSpacing(10)
        lay_der.setContentsMargins(8, 16, 16, 16)

        lbl_mp = QLabel("Medio de Pago")
        lbl_mp.setStyleSheet("font-weight:700; color:#C9A84C; font-size:12pt;")
        lay_der.addWidget(lbl_mp)

        self.btn_group_mp = QButtonGroup(self)
        self.btn_group_mp.setExclusive(True)
        for texto, valor, obj_name in self.MEDIOS_PAGO:
            btn = QPushButton(texto)
            btn.setObjectName(obj_name)
            btn.setCheckable(True)
            btn.setMinimumHeight(48)
            btn.clicked.connect(lambda checked, v=valor: self._set_medio_pago(v))
            self.btn_group_mp.addButton(btn)
            lay_der.addWidget(btn)
            if valor == "efectivo":
                btn.setChecked(True)

        lay_der.addSpacing(10)

        # Línea separadora
        linea = QFrame()
        linea.setFrameShape(QFrame.Shape.HLine)
        linea.setStyleSheet("color: #333;")
        lay_der.addWidget(linea)

        btn_cobrar = QPushButton("✅  COBRAR  (F12)")
        btn_cobrar.setObjectName("btn_exito")
        btn_cobrar.setObjectName("btn_grande")
        btn_cobrar.setMinimumHeight(64)
        btn_cobrar.setStyleSheet(
            "QPushButton { background-color: #2E7D32; font-size:15pt; font-weight:900;"
            " border-radius:10px; color:white; }"
            "QPushButton:hover { background-color: #388E3C; }"
            "QPushButton:pressed { background-color: #1B5E20; }"
        )
        btn_cobrar.clicked.connect(self._confirmar_venta)
        lay_der.addWidget(btn_cobrar)

        btn_vaciar = QPushButton("🗑  Vaciar carrito")
        btn_vaciar.setObjectName("btn_secundario")
        btn_vaciar.clicked.connect(self._vaciar_carrito)
        lay_der.addWidget(btn_vaciar)

        lay_der.addSpacing(10)

        lbl_ult = QLabel("Últimas ventas del día")
        lbl_ult.setStyleSheet("color:#888; font-size:9pt; font-weight:700;")
        lay_der.addWidget(lbl_ult)

        self.lista_ultimas = QListWidget()
        self.lista_ultimas.setMaximumHeight(200)
        self.lista_ultimas.setStyleSheet("font-size:9pt;")
        lay_der.addWidget(self.lista_ultimas)

        btn_anular = QPushButton("↩  Anular última venta")
        btn_anular.setObjectName("btn_advertencia")
        btn_anular.clicked.connect(self._anular_ultima_venta)
        lay_der.addWidget(btn_anular)

        lay_der.addStretch()
        splitter.addWidget(der)
        splitter.setSizes([620, 300])
        root.addWidget(splitter)

        self._cargar_ultimas_ventas()

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("F2"),  self).activated.connect(self._abrir_buscador)
        QShortcut(QKeySequence("F12"), self).activated.connect(self._confirmar_venta)
        QShortcut(QKeySequence("Escape"), self).activated.connect(self._vaciar_carrito)

    # ── Lógica de escaneo ─────────────────────────────────────

    def _procesar_escaneo(self):
        codigo = self.scan_input.text().strip()
        if not codigo:
            return
        self.scan_input.clear()
        producto = db.buscar_por_codigo(codigo)
        if producto:
            self._agregar_al_carrito(dict(producto))
        else:
            QMessageBox.warning(
                self, "Código no encontrado",
                f"No se encontró el código: {codigo}\n\n"
                "Podés buscarlo por nombre con el botón 🔍 Buscar (F2)"
            )

    def _abrir_buscador(self):
        dlg = BuscadorProductos(self)
        dlg.producto_seleccionado.connect(self._agregar_al_carrito)
        dlg.exec()
        QTimer.singleShot(100, self.scan_input.setFocus)

    # ── Carrito ───────────────────────────────────────────────

    def _agregar_al_carrito(self, producto: dict):
        # Si ya está en el carrito, aumentar cantidad
        for item in self.carrito:
            if item.producto_id == producto["id"]:
                if item.cantidad >= item.stock_actual:
                    QMessageBox.warning(self, "Sin stock",
                                        f"No hay más stock de '{item.nombre}'.\n"
                                        f"Stock disponible: {item.stock_actual}")
                    return
                item.cantidad += 1
                self._refrescar_tabla()
                return

        # Producto nuevo en carrito
        if producto["stock_actual"] <= 0:
            resp = QMessageBox.question(
                self, "Sin stock",
                f"'{producto['nombre']}' no tiene stock disponible.\n¿Agregar igual?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if resp == QMessageBox.StandardButton.No:
                return

        self.carrito.append(ItemCarrito(producto))
        self._refrescar_tabla()

    def _refrescar_tabla(self):
        self.tabla.setRowCount(len(self.carrito))
        for i, item in enumerate(self.carrito):
            self.tabla.setItem(i, 0, QTableWidgetItem(item.nombre))
            self.tabla.setItem(i, 1, QTableWidgetItem(f"${item.precio_unit:.2f}"))

            # Spinner de cantidad inline
            spin = QSpinBox()
            spin.setRange(1, max(item.stock_actual, 999))
            spin.setValue(item.cantidad)
            spin.valueChanged.connect(lambda val, idx=i: self._cambiar_cantidad(idx, val))
            spin.setStyleSheet("background:#2C2C2C; color:#F5F5F5; border:1px solid #444; padding:2px;")
            self.tabla.setCellWidget(i, 2, spin)

            self.tabla.setItem(i, 3, QTableWidgetItem(f"${item.subtotal:.2f}"))

            btn_del = QPushButton("✕")
            btn_del.setFixedSize(30, 30)
            btn_del.setStyleSheet(
                "QPushButton{background:#B71C1C;color:white;border-radius:4px;font-weight:700;}"
                "QPushButton:hover{background:#C62828;}"
            )
            btn_del.clicked.connect(lambda _, idx=i: self._quitar_item(idx))
            self.tabla.setCellWidget(i, 4, btn_del)
            self.tabla.setRowHeight(i, 44)

        self._actualizar_total()

    def _cambiar_cantidad(self, idx: int, valor: int):
        if idx < len(self.carrito):
            self.carrito[idx].cantidad = valor
            self.tabla.setItem(idx, 3, QTableWidgetItem(f"${self.carrito[idx].subtotal:.2f}"))
            self._actualizar_total()

    def _quitar_item(self, idx: int):
        if idx < len(self.carrito):
            self.carrito.pop(idx)
            self._refrescar_tabla()

    def _vaciar_carrito(self):
        if self.carrito:
            resp = QMessageBox.question(
                self, "Vaciar carrito",
                "¿Confirmás que querés vaciar el carrito?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if resp == QMessageBox.StandardButton.Yes:
                self.carrito.clear()
                self.spin_descuento.setValue(0)
                self._refrescar_tabla()
        self.scan_input.setFocus()

    def _actualizar_total(self):
        subtotal = sum(i.subtotal for i in self.carrito)
        descuento = self.spin_descuento.value()
        total = max(0, subtotal - descuento)
        self.lbl_total.setText(f"${total:,.2f}")

    def _set_medio_pago(self, valor: str):
        self.medio_pago_actual = valor

    # ── Confirmar venta ───────────────────────────────────────

    def _confirmar_venta(self):
        if not self.carrito:
            QMessageBox.information(self, "Carrito vacío",
                                    "Agregá al menos un producto antes de cobrar.")
            return

        subtotal = sum(i.subtotal for i in self.carrito)
        descuento = self.spin_descuento.value()
        total = max(0, subtotal - descuento)

        dlg = ConfirmacionVenta(
            self,
            carrito=self.carrito,
            subtotal=subtotal,
            descuento=descuento,
            total=total,
            medio_pago=self.medio_pago_actual
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            items_db = [
                {"producto_id": i.producto_id,
                 "cantidad": i.cantidad,
                 "precio_unit": i.precio_unit}
                for i in self.carrito
            ]
            try:
                venta_id = db.registrar_venta(
                    items_db,
                    self.medio_pago_actual,
                    descuento=descuento
                )
                self.carrito.clear()
                self.spin_descuento.setValue(0)
                self._refrescar_tabla()
                self._cargar_ultimas_ventas()
                self.venta_realizada.emit(venta_id)
                self.scan_input.setFocus()

                QMessageBox.information(
                    self, "✅  Venta registrada",
                    f"Venta #{venta_id} registrada correctamente.\nTotal cobrado: ${total:,.2f}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Error al registrar", str(e))

    # ── Últimas ventas ─────────────────────────────────────────

    def _cargar_ultimas_ventas(self):
        self.lista_ultimas.clear()
        ventas = db.ventas_del_dia()
        icons = {"efectivo": "💵", "debito": "💳", "credito": "🏦",
                 "transferencia": "📲", "qr": "🔲"}
        for v in ventas[:15]:
            ic = icons.get(v["medio_pago"], "💰")
            item = QListWidgetItem(
                f"#{v['id']}  {ic}  ${v['total']:,.2f}  –  {v['hora'][:5]}"
            )
            item.setData(Qt.ItemDataRole.UserRole, v["id"])
            self.lista_ultimas.addItem(item)

    def _anular_ultima_venta(self):
        item = self.lista_ultimas.currentItem()
        if not item:
            if self.lista_ultimas.count() > 0:
                self.lista_ultimas.setCurrentRow(0)
                item = self.lista_ultimas.currentItem()
            else:
                QMessageBox.information(self, "Sin ventas", "No hay ventas del día para anular.")
                return

        venta_id = item.data(Qt.ItemDataRole.UserRole)
        resp = QMessageBox.question(
            self, "Anular venta",
            f"¿Confirmás la anulación de la venta #{venta_id}?\n"
            "El stock se repondrá automáticamente.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            db.anular_venta(venta_id, "Anulada desde POS")
            self._cargar_ultimas_ventas()
            QMessageBox.information(self, "Anulada", f"Venta #{venta_id} anulada correctamente.")


# ─────────────────────────────────────────────────────────────
#  Diálogo de confirmación antes de cobrar
# ─────────────────────────────────────────────────────────────

class ConfirmacionVenta(QDialog):
    def __init__(self, parent, carrito, subtotal, descuento, total, medio_pago):
        super().__init__(parent)
        self.setWindowTitle("Confirmar Venta")
        self.setMinimumWidth(420)
        self.setModal(True)
        self._build(carrito, subtotal, descuento, total, medio_pago)

    def _build(self, carrito, subtotal, descuento, total, medio_pago):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(24, 20, 24, 20)

        lbl = QLabel("Resumen de la venta")
        lbl.setObjectName("titulo_seccion")
        lay.addWidget(lbl)

        for item in carrito:
            row = QLabel(f"  {item.cantidad}x  {item.nombre}   →  ${item.subtotal:,.2f}")
            row.setStyleSheet("color:#CCCCCC; font-size:10pt;")
            lay.addWidget(row)

        linea = QFrame()
        linea.setFrameShape(QFrame.Shape.HLine)
        linea.setStyleSheet("color:#444;")
        lay.addWidget(linea)

        if descuento > 0:
            lay.addWidget(QLabel(f"Subtotal: ${subtotal:,.2f}"))
            lay.addWidget(QLabel(f"Descuento: -${descuento:,.2f}"))

        mp_labels = {"efectivo": "💵 Efectivo", "debito": "💳 Débito",
                     "credito": "🏦 Crédito", "transferencia": "📲 Transferencia",
                     "qr": "🔲 QR"}
        lbl_mp = QLabel(f"Medio de pago: {mp_labels.get(medio_pago, medio_pago)}")
        lbl_mp.setStyleSheet("font-weight:600; color:#C9A84C; font-size:12pt;")
        lay.addWidget(lbl_mp)

        lbl_total = QLabel(f"TOTAL: ${total:,.2f}")
        lbl_total.setStyleSheet("font-size:22pt; font-weight:900; color:#C9A84C;")
        lay.addWidget(lbl_total)

        btn_row = QHBoxLayout()
        btn_ok = QPushButton("✅  Confirmar cobro")
        btn_ok.setMinimumHeight(50)
        btn_ok.setStyleSheet(
            "QPushButton{background:#2E7D32;font-size:13pt;font-weight:700;color:white;border-radius:8px;}"
            "QPushButton:hover{background:#388E3C;}"
        )
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("btn_secundario")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_ok, 2)
        btn_row.addWidget(btn_cancel, 1)
        lay.addLayout(btn_row)
