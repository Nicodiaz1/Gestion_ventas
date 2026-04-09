# ─────────────────────────────────────────────────────────────
#  ui/pos.py  –  Punto de Venta (POS) con multi-carrito
# ─────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QGridLayout, QScrollArea, QFrame,
    QButtonGroup, QSpinBox, QDoubleSpinBox, QAbstractItemView,
    QListWidget, QListWidgetItem, QSplitter, QSizePolicy,
    QTabWidget, QTabBar, QInputDialog, QStackedWidget
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
#  Panel de un carrito individual
# ─────────────────────────────────────────────────────────────

class CarritoWidget(QWidget):
    """Un carrito completo para un cliente. PosWidget instancia varios."""
    venta_realizada = pyqtSignal(int)   # emite venta_id

    MEDIOS_PAGO = [
        ("💵 Efectivo",      "efectivo",      "mp_efectivo"),
        ("💳 Débito",         "debito",        "mp_debito"),
        ("🏦 Crédito",       "credito",       "mp_credito"),
        ("📲 Transferencia", "transferencia", "mp_transferencia"),
        ("🔲 QR",            "qr",            "mp_qr"),
    ]

    def __init__(self, nombre_cliente: str = "Cliente 1", parent=None):
        super().__init__(parent)
        self.nombre_cliente     = nombre_cliente
        self.carrito: list[ItemCarrito] = []
        self.medio_pago_actual  = "efectivo"
        self._build_ui()
        QTimer.singleShot(100, self.scan_input.setFocus)

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # ── Panel izquierdo ───────────────────────────────────
        izq = QWidget()
        izq.setMinimumWidth(520)
        lay_izq = QVBoxLayout(izq)
        lay_izq.setSpacing(10)
        lay_izq.setContentsMargins(16, 12, 8, 16)

        scan_row = QHBoxLayout()
        self.scan_input = QLineEdit()
        self.scan_input.setObjectName("scan_input")
        self.scan_input.setPlaceholderText(
            "📷  Escaneá o escribí el código y presioná Enter…")
        self.scan_input.returnPressed.connect(self._procesar_escaneo)
        scan_row.addWidget(self.scan_input, 1)

        btn_buscar = QPushButton("🔍  Buscar")
        btn_buscar.setToolTip("Buscar por nombre (F2)")
        btn_buscar.clicked.connect(self._abrir_buscador)
        btn_buscar.setMinimumWidth(110)
        scan_row.addWidget(btn_buscar)
        lay_izq.addLayout(scan_row)

        lbl_hint = QLabel("F2 buscar por nombre  |  F12 cobrar  |  Esc vaciar carrito")
        lbl_hint.setStyleSheet("color: #666; font-size: 9pt;")
        lay_izq.addWidget(lbl_hint)

        # Tabla del carrito
        self.tabla = QTableWidget(0, 5)
        self.tabla.setHorizontalHeaderLabels(
            ["Producto", "Precio unit.", "Cant.", "Subtotal", ""])
        self.tabla.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        for c in (1, 2, 3, 4):
            self.tabla.horizontalHeader().setSectionResizeMode(
                c, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setMinimumHeight(300)
        lay_izq.addWidget(self.tabla, 1)

        # Total row
        totales_row = QHBoxLayout()

        # % Recargo (+) o Descuento (-)
        porc_lay = QVBoxLayout()
        lbl_porc = QLabel("% Recargo (+) / Desc. (−):")
        lbl_porc.setStyleSheet("color:#AAAAAA; font-size:10pt;")
        self.spin_porcentaje = QDoubleSpinBox()
        self.spin_porcentaje.setRange(-50, 100)
        self.spin_porcentaje.setDecimals(1)
        self.spin_porcentaje.setSingleStep(5)
        self.spin_porcentaje.setSuffix(" %")
        self.spin_porcentaje.setValue(0)
        self.spin_porcentaje.setToolTip(
            "Positivo = recargo (ej: tarjeta crédito)\n"
            "Negativo = descuento porcentual")
        self.spin_porcentaje.setStyleSheet(
            "QDoubleSpinBox { color: #F5F5F5; background:#2C2C2C; }")
        self.spin_porcentaje.valueChanged.connect(self._actualizar_total)
        porc_lay.addWidget(lbl_porc)
        porc_lay.addWidget(self.spin_porcentaje)
        totales_row.addLayout(porc_lay)
        totales_row.addStretch()

        total_lay = QVBoxLayout()
        self.lbl_tit_total = QLabel("TOTAL A COBRAR")
        self.lbl_tit_total.setStyleSheet(
            "color:#AAAAAA; font-size:10pt; font-weight:600;")
        self.lbl_tit_total.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_total = QLabel("$0.00")
        self.lbl_total.setObjectName("precio_total")
        self.lbl_total.setAlignment(Qt.AlignmentFlag.AlignRight)
        total_lay.addWidget(self.lbl_tit_total)
        total_lay.addWidget(self.lbl_total)
        totales_row.addLayout(total_lay)
        lay_izq.addLayout(totales_row)

        splitter.addWidget(izq)

        # ── Panel derecho ─────────────────────────────────────
        der = QWidget()
        der.setMaximumWidth(340)
        der.setMinimumWidth(280)
        lay_der = QVBoxLayout(der)
        lay_der.setSpacing(10)
        lay_der.setContentsMargins(8, 12, 16, 16)

        lbl_mp = QLabel("Medio de Pago")
        lbl_mp.setStyleSheet(
            "font-weight:700; color:#C9A84C; font-size:12pt;")
        lay_der.addWidget(lbl_mp)

        self.btn_group_mp = QButtonGroup(self)
        self.btn_group_mp.setExclusive(True)
        for texto, valor, obj_name in self.MEDIOS_PAGO:
            btn = QPushButton(texto)
            btn.setObjectName(obj_name)
            btn.setCheckable(True)
            btn.setMinimumHeight(44)
            btn.clicked.connect(
                lambda checked, v=valor: self._set_medio_pago(v))
            self.btn_group_mp.addButton(btn)
            lay_der.addWidget(btn)
            if valor == "efectivo":
                btn.setChecked(True)

        lay_der.addSpacing(8)
        linea = QFrame()
        linea.setFrameShape(QFrame.Shape.HLine)
        linea.setStyleSheet("color: #333;")
        lay_der.addWidget(linea)

        btn_cobrar = QPushButton("✅  COBRAR  (F12)")
        btn_cobrar.setMinimumHeight(64)
        btn_cobrar.setStyleSheet(
            "QPushButton { background-color: #2E7D32; font-size:15pt;"
            " font-weight:900; border-radius:10px; color:white; }"
            "QPushButton:hover { background-color: #388E3C; }"
            "QPushButton:pressed { background-color: #1B5E20; }"
        )
        btn_cobrar.clicked.connect(self._confirmar_venta)
        lay_der.addWidget(btn_cobrar)

        btn_vaciar = QPushButton("🗑  Vaciar carrito")
        btn_vaciar.setObjectName("btn_secundario")
        btn_vaciar.clicked.connect(self._vaciar_carrito)
        lay_der.addWidget(btn_vaciar)

        lay_der.addSpacing(8)
        lbl_ult = QLabel("Últimas ventas del día")
        lbl_ult.setStyleSheet("color:#888; font-size:9pt; font-weight:700;")
        lay_der.addWidget(lbl_ult)

        self.lista_ultimas = QListWidget()
        self.lista_ultimas.setMaximumHeight(180)
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

    # ── Escaneo ───────────────────────────────────────────────

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
                f"No se encontró: {codigo}\n"
                "Buscalo por nombre con 🔍 Buscar (F2)")

    def _abrir_buscador(self):
        dlg = BuscadorProductos(self)
        dlg.producto_seleccionado.connect(self._agregar_al_carrito)
        dlg.exec()
        QTimer.singleShot(100, self.scan_input.setFocus)

    # ── Carrito ───────────────────────────────────────────────

    def _agregar_al_carrito(self, producto: dict):
        for item in self.carrito:
            if item.producto_id == producto["id"]:
                if item.cantidad >= item.stock_actual:
                    QMessageBox.warning(self, "Sin stock",
                        f"No hay más stock de '{item.nombre}'.\n"
                        f"Disponible: {item.stock_actual}")
                    return
                item.cantidad += 1
                self._refrescar_tabla()
                return

        if producto["stock_actual"] <= 0:
            resp = QMessageBox.question(
                self, "Sin stock",
                f"'{producto['nombre']}' no tiene stock.\n¿Agregar igual?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if resp == QMessageBox.StandardButton.No:
                return

        self.carrito.append(ItemCarrito(producto))
        self._refrescar_tabla()

    def _refrescar_tabla(self):
        self.tabla.setRowCount(len(self.carrito))
        for i, item in enumerate(self.carrito):
            self.tabla.setItem(i, 0, QTableWidgetItem(item.nombre))
            self.tabla.setItem(i, 1, QTableWidgetItem(
                f"${item.precio_unit:.2f}"))
            spin = QSpinBox()
            spin.setRange(1, max(item.stock_actual, 999))
            spin.setValue(item.cantidad)
            spin.valueChanged.connect(
                lambda val, idx=i: self._cambiar_cantidad(idx, val))
            spin.setStyleSheet(
                "background:#2C2C2C; color:#F5F5F5;"
                " border:1px solid #444; padding:2px;")
            self.tabla.setCellWidget(i, 2, spin)
            self.tabla.setItem(i, 3, QTableWidgetItem(
                f"${item.subtotal:.2f}"))
            btn_del = QPushButton("✕")
            btn_del.setFixedSize(30, 30)
            btn_del.setStyleSheet(
                "QPushButton{background:#B71C1C;color:white;"
                "border-radius:4px;font-weight:700;}"
                "QPushButton:hover{background:#C62828;}")
            btn_del.clicked.connect(
                lambda _, idx=i: self._quitar_item(idx))
            self.tabla.setCellWidget(i, 4, btn_del)
            self.tabla.setRowHeight(i, 44)
        self._actualizar_total()

    def _cambiar_cantidad(self, idx: int, valor: int):
        if idx < len(self.carrito):
            self.carrito[idx].cantidad = valor
            self.tabla.setItem(
                idx, 3,
                QTableWidgetItem(f"${self.carrito[idx].subtotal:.2f}"))
            self._actualizar_total()

    def _quitar_item(self, idx: int):
        if idx < len(self.carrito):
            self.carrito.pop(idx)
            self._refrescar_tabla()

    def _vaciar_carrito(self):
        if self.carrito:
            resp = QMessageBox.question(
                self, "Vaciar carrito",
                "¿Vaciar el carrito?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if resp == QMessageBox.StandardButton.Yes:
                self.carrito.clear()
                self.spin_porcentaje.setValue(0)
                self._refrescar_tabla()
        self.scan_input.setFocus()

    def _actualizar_total(self):
        subtotal   = sum(i.subtotal for i in self.carrito)
        porcentaje = self.spin_porcentaje.value()
        total      = subtotal * (1 + porcentaje / 100)
        self.lbl_total.setText(f"${total:,.2f}")
        if porcentaje > 0:
            self.lbl_tit_total.setText(f"TOTAL  (+{porcentaje:.0f}% recargo)")
            self.lbl_tit_total.setStyleSheet(
                "color:#EF5350; font-size:10pt; font-weight:600;")
        elif porcentaje < 0:
            self.lbl_tit_total.setText(f"TOTAL  ({porcentaje:.0f}% desc.)")
            self.lbl_tit_total.setStyleSheet(
                "color:#66BB6A; font-size:10pt; font-weight:600;")
        else:
            self.lbl_tit_total.setText("TOTAL A COBRAR")
            self.lbl_tit_total.setStyleSheet(
                "color:#AAAAAA; font-size:10pt; font-weight:600;")

    def _set_medio_pago(self, valor: str):
        self.medio_pago_actual = valor

    # ── Confirmar venta ───────────────────────────────────────

    def _confirmar_venta(self):
        if not self.carrito:
            QMessageBox.information(self, "Carrito vacío",
                "Agregá al menos un producto antes de cobrar.")
            return
        subtotal   = sum(i.subtotal for i in self.carrito)
        porcentaje = self.spin_porcentaje.value()
        total      = subtotal * (1 + porcentaje / 100)

        dlg = ConfirmacionVenta(
            self, carrito=self.carrito,
            subtotal=subtotal, descuento=0,
            porcentaje=porcentaje,
            total=total, medio_pago=self.medio_pago_actual,
            nombre_cliente=self.nombre_cliente)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            items_db = [
                {"producto_id": i.producto_id,
                 "cantidad":    i.cantidad,
                 "precio_unit": i.precio_unit}
                for i in self.carrito
            ]
            try:
                venta_id = db.registrar_venta(
                    items_db, self.medio_pago_actual,
                    descuento=0, recargo_pct=porcentaje)
                self.carrito.clear()
                self.spin_porcentaje.setValue(0)
                self._refrescar_tabla()
                self._cargar_ultimas_ventas()
                self.venta_realizada.emit(venta_id)
                self.scan_input.setFocus()
                QMessageBox.information(
                    self, "✅  Venta registrada",
                    f"Venta #{venta_id} registrada.\n"
                    f"Total cobrado: ${total:,.2f}")
            except Exception as e:
                QMessageBox.critical(self, "Error al registrar", str(e))

    # ── Últimas ventas ─────────────────────────────────────────

    def _cargar_ultimas_ventas(self):
        self.lista_ultimas.clear()
        icons = {"efectivo": "💵", "debito": "💳", "credito": "🏦",
                 "transferencia": "📲", "qr": "🔲"}
        for v in db.ventas_del_dia()[:15]:
            ic = icons.get(v["medio_pago"], "💰")
            item = QListWidgetItem(
                f"#{v['id']}  {ic}  ${v['total']:,.2f}  –  {v['hora'][:5]}")
            item.setData(Qt.ItemDataRole.UserRole, v["id"])
            self.lista_ultimas.addItem(item)

    def _anular_ultima_venta(self):
        item = self.lista_ultimas.currentItem()
        if not item:
            if self.lista_ultimas.count() > 0:
                self.lista_ultimas.setCurrentRow(0)
                item = self.lista_ultimas.currentItem()
            else:
                QMessageBox.information(self, "Sin ventas",
                    "No hay ventas del día para anular.")
                return
        venta_id = item.data(Qt.ItemDataRole.UserRole)
        resp = QMessageBox.question(
            self, "Anular venta",
            f"¿Anulás la venta #{venta_id}?\n"
            "El stock se repone automáticamente.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp == QMessageBox.StandardButton.Yes:
            db.anular_venta(venta_id, "Anulada desde POS")
            self._cargar_ultimas_ventas()
            QMessageBox.information(
                self, "Anulada",
                f"Venta #{venta_id} anulada correctamente.")


# ─────────────────────────────────────────────────────────────
#  POS principal: gestor de múltiples carritos
# ─────────────────────────────────────────────────────────────

class PosWidget(QWidget):
    """
    Contiene uno o más CarritoWidget en pestañas.
    Cada pestaña = un cliente atendiendo en simultaneo.
    """
    venta_realizada = pyqtSignal(int)

    # Colores para identificar cada carrito visualmente
    COLORES_CLIENTE = [
        "#722F37",   # vino      – Cliente 1
        "#1565C0",   # azul      – Cliente 2
        "#2E7D32",   # verde     – Cliente 3
        "#E65100",   # naranja   – Cliente 4
        "#6A1B9A",   # violeta   – Cliente 5
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._carritos: list[CarritoWidget] = []
        self._build_ui()
        self._agregar_carrito("Cliente 1")   # siempre inicia con uno
        self._setup_shortcuts()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)

        # ── Barra superior de clientes ────────────────────────
        barra = QWidget()
        barra.setFixedHeight(54)
        barra.setStyleSheet("background:#111111; border-bottom:2px solid #722F37;")
        barra_lay = QHBoxLayout(barra)
        barra_lay.setContentsMargins(12, 6, 12, 6)
        barra_lay.setSpacing(6)

        titulo = QLabel("🛒  Punto de Venta")
        titulo.setObjectName("titulo_seccion")
        titulo.setStyleSheet(
            "font-size:15pt; font-weight:800; color:#F5F5F5; padding:0;")
        barra_lay.addWidget(titulo)
        barra_lay.addSpacing(16)

        # Botones de clientes
        self._btn_clientes: list[QPushButton] = []
        self._btn_bar = QHBoxLayout()
        self._btn_bar.setSpacing(4)
        barra_lay.addLayout(self._btn_bar)

        # Botón "+" para agregar cliente
        btn_add = QPushButton("➕ Nuevo cliente")
        btn_add.setFixedHeight(38)
        btn_add.setStyleSheet(
            "QPushButton{background:#2C2C2C;color:#C9A84C;"
            "border:1px dashed #C9A84C;border-radius:6px;"
            "font-size:11pt;padding:0 12px;}"
            "QPushButton:hover{background:#3C3C3C;}")
        btn_add.clicked.connect(self._nuevo_cliente)
        barra_lay.addWidget(btn_add)
        barra_lay.addStretch()

        lbl_hint = QLabel("F2 buscar  |  F12 cobrar  |  F3/F4 cambiar cliente")
        lbl_hint.setStyleSheet("color:#555; font-size:9pt;")
        barra_lay.addWidget(lbl_hint)

        lay.addWidget(barra)

        # ── Stack de carritos ─────────────────────────────────
        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("F2"),  self).activated.connect(
            self._fwd_buscador)
        QShortcut(QKeySequence("F12"), self).activated.connect(
            self._fwd_cobrar)
        QShortcut(QKeySequence("Escape"), self).activated.connect(
            self._fwd_vaciar)
        QShortcut(QKeySequence("F3"), self).activated.connect(
            self._cliente_anterior)
        QShortcut(QKeySequence("F4"), self).activated.connect(
            self._cliente_siguiente)

    # ── Gestión de carritos ───────────────────────────────────

    def _agregar_carrito(self, nombre: str):
        idx     = len(self._carritos)
        color   = self.COLORES_CLIENTE[idx % len(self.COLORES_CLIENTE)]
        carrito = CarritoWidget(nombre_cliente=nombre)
        carrito.venta_realizada.connect(self.venta_realizada)
        self._carritos.append(carrito)
        self.stack.addWidget(carrito)

        # Botón en la barra
        btn = QPushButton(f"  {nombre}  ")
        btn.setCheckable(True)
        btn.setFixedHeight(38)
        btn.setProperty("cliente_color", color)
        btn.setStyleSheet(self._estilo_btn_cliente(color, False))
        btn.clicked.connect(lambda _, i=idx: self._seleccionar_cliente(i))
        self._btn_clientes.append(btn)
        self._btn_bar.addWidget(btn)

        self._seleccionar_cliente(idx)

    def _estilo_btn_cliente(self, color: str, activo: bool) -> str:
        if activo:
            return (f"QPushButton{{background:{color};color:white;"
                    f"border:2px solid {color};border-radius:6px;"
                    f"font-size:11pt;font-weight:700;padding:0 14px;}}"
                    f"QPushButton:hover{{background:{color};}}")
        else:
            return (f"QPushButton{{background:#1A1A1A;color:#AAAAAA;"
                    f"border:2px solid #333;border-radius:6px;"
                    f"font-size:11pt;padding:0 14px;}}"
                    f"QPushButton:hover{{background:#2A2A2A;"
                    f"border-color:{color};color:{color};}}")

    def _seleccionar_cliente(self, idx: int):
        self.stack.setCurrentIndex(idx)
        for i, (btn, carrito) in enumerate(
                zip(self._btn_clientes, self._carritos)):
            color = self.COLORES_CLIENTE[i % len(self.COLORES_CLIENTE)]
            activo = (i == idx)
            btn.setChecked(activo)
            # Mostrar cantidad de items en el botón
            n = len(carrito.carrito)
            badge = f"  ({n})  " if n > 0 else ""
            btn.setText(f"  {carrito.nombre_cliente}{badge}  ")
            btn.setStyleSheet(self._estilo_btn_cliente(color, activo))
        # Foco al scan_input del carrito activo
        QTimer.singleShot(50, self._carritos[idx].scan_input.setFocus)

    def _nuevo_cliente(self):
        if len(self._carritos) >= 5:
            QMessageBox.information(
                self, "Límite alcanzado",
                "Máximo 5 clientes simultáneos.")
            return
        nombre, ok = QInputDialog.getText(
            self, "Nuevo cliente",
            "Nombre o número de cliente:",
            text=f"Cliente {len(self._carritos) + 1}")
        if ok and nombre.strip():
            self._agregar_carrito(nombre.strip())

    def _cliente_anterior(self):
        cur = self.stack.currentIndex()
        if cur > 0:
            self._seleccionar_cliente(cur - 1)

    def _cliente_siguiente(self):
        cur = self.stack.currentIndex()
        if cur < len(self._carritos) - 1:
            self._seleccionar_cliente(cur + 1)

    # ── Forwarding de shortcuts al carrito activo ─────────────

    def _carrito_activo(self) -> CarritoWidget:
        return self._carritos[self.stack.currentIndex()]

    def _fwd_buscador(self):
        self._carrito_activo()._abrir_buscador()

    def _fwd_cobrar(self):
        self._carrito_activo()._confirmar_venta()

    def _fwd_vaciar(self):
        self._carrito_activo()._vaciar_carrito()

    # Compatibilidad con MainWindow que accede a scan_input
    @property
    def scan_input(self):
        return self._carrito_activo().scan_input

# ─────────────────────────────────────────────────────────────
#  Diálogo de confirmación antes de cobrar
# ─────────────────────────────────────────────────────────────

class ConfirmacionVenta(QDialog):
    def __init__(self, parent, carrito, subtotal, descuento, total, medio_pago,
                 nombre_cliente="", porcentaje=0):
        super().__init__(parent)
        titulo = f"Confirmar Venta — {nombre_cliente}" if nombre_cliente else "Confirmar Venta"
        self.setWindowTitle(titulo)
        self.setMinimumWidth(420)
        self.setModal(True)
        self._build(carrito, subtotal, descuento, total, medio_pago, porcentaje)

    def _build(self, carrito, subtotal, descuento, total, medio_pago, porcentaje=0):
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
        if porcentaje != 0:
            tipo  = "Recargo" if porcentaje > 0 else "Descuento"
            color = "#EF5350" if porcentaje > 0 else "#66BB6A"
            lbl_pct = QLabel(f"{tipo}: {abs(porcentaje):.1f}%")
            lbl_pct.setStyleSheet(f"font-weight:600; color:{color}; font-size:12pt;")
            lay.addWidget(lbl_pct)

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
