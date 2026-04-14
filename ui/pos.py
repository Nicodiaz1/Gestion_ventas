# ─────────────────────────────────────────────────────────────
#  ui/pos.py  –  Punto de Venta (POS) con multi-carrito
# ─────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QGridLayout, QScrollArea, QFrame,
    QButtonGroup, QSpinBox, QDoubleSpinBox, QAbstractItemView,
    QListWidget, QListWidgetItem, QSplitter, QSizePolicy,
    QTabWidget, QTabBar, QInputDialog, QStackedWidget, QCompleter
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize, QStringListModel, QLocale
from PyQt6.QtGui import QFont, QKeySequence, QShortcut, QColor, QDoubleValidator
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import database as db


# ─────────────────────────────────────────────────────────────
#  Widget de búsqueda rápida por nombre (para sin código)
# ─────────────────────────────────────────────────────────────

class BuscadorProductos(QDialog):
    producto_seleccionado = pyqtSignal(dict)

    def __init__(self, parent=None, texto_inicial: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Buscar Producto")
        self.setMinimumSize(560, 440)
        self.setModal(True)
        self._texto_inicial = texto_inicial
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

        if self._texto_inicial:
            self.txt_buscar.setText(self._texto_inicial)
        else:
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
#  Helpers
# ─────────────────────────────────────────────────────────────

def _safe_float(text: str) -> float:
    """Parsea un número aceptando tanto punto como coma como separador decimal.
    Punto del teclado numérico = decimal. Coma de thousands se descarta."""
    try:
        t = (text or "").strip()
        if not t:
            return 0.0
        # Si tiene coma Y punto: el último es el decimal
        if "," in t and "." in t:
            if t.rfind(",") > t.rfind("."):
                # "10.000,50"  → 10000.50
                t = t.replace(".", "").replace(",", ".")
            else:
                # "10,000.50"  → 10000.50
                t = t.replace(",", "")
        elif "," in t:
            # Solo coma: decimal si hay 1-2 dígitos despues, miles si hay 3
            parts = t.split(",")
            if len(parts) == 2 and len(parts[1]) == 3 and parts[0].replace(".", "").isdigit() and parts[1].isdigit():
                t = t.replace(",", "")  # separador de miles
            else:
                t = t.replace(",", ".")  # separador decimal
        # Solo punto: Python float lo toma siempre como decimal
        return float(t)
    except (ValueError, AttributeError):
        return 0.0


# ─────────────────────────────────────────────────────────────
#  Fila del carrito
# ─────────────────────────────────────────────────────────────

class ItemCarrito:
    def __init__(self, producto: dict, cantidad: int = 1,
                 lote_id: int = None, cosecha: int = None):
        self.producto_id      = producto["id"]
        self.nombre           = producto["nombre"]
        self.precio_unit      = float(producto["precio_venta"])
        self.precio_costo     = float(producto.get("precio_costo") or 0)
        self.cantidad         = cantidad
        self.stock_actual     = producto["stock_actual"]
        self.lote_id          = lote_id    # None = FIFO automático
        self.cosecha          = cosecha    # para mostrar en carrito
        self.subtotal_override: float | None = None  # precio promo manual

    @property
    def subtotal(self) -> float:
        if self.subtotal_override is not None:
            return self.subtotal_override
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
        ("🤝 Fiado",         "fiado",         "mp_fiado"),
    ]

    def __init__(self, nombre_cliente: str = "Cliente 1", parent=None):
        super().__init__(parent)
        self.nombre_cliente     = nombre_cliente
        self.carrito: list[ItemCarrito] = []
        self.medio_pago_actual  = "efectivo"
        self._ajustando_total   = False
        self._completando       = False
        self._sugerencias_cache: dict[str, dict] = {}
        self._cliente_id: int | None = None
        self._cliente_saldo: float   = 0.0
        self._cliente_nombre: str    = ""
        self._manually_edited: set   = set()   # métodos cuyo monto escribió el usuario
        self._build_ui()
        self._setup_completer()
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
            "📷  Escanear código  |  o escribí el nombre del producto…")
        self.scan_input.returnPressed.connect(self._procesar_escaneo)
        scan_row.addWidget(self.scan_input, 1)

        btn_buscar = QPushButton("🔍  Buscar")
        btn_buscar.setToolTip("Buscar por nombre (F2)")
        btn_buscar.clicked.connect(self._abrir_buscador)
        btn_buscar.setMinimumWidth(110)
        scan_row.addWidget(btn_buscar)
        lay_izq.addLayout(scan_row)

        # ── Fila de cliente asignado ──────────────────────────
        cliente_row = QHBoxLayout()
        self.lbl_cliente = QLabel("👤  Sin cliente asignado")
        self.lbl_cliente.setStyleSheet("color:#555; font-size:9pt; padding:2px 0;")
        cliente_row.addWidget(self.lbl_cliente, 1)
        self.btn_asignar_cliente = QPushButton("+ Asignar")
        self.btn_asignar_cliente.setFixedHeight(24)
        self.btn_asignar_cliente.setFixedWidth(90)
        self.btn_asignar_cliente.setStyleSheet(
            "QPushButton{background:#2C2C2C;border:1px solid #555;border-radius:4px;"
            "color:#C9A84C;font-size:8pt;}"
            "QPushButton:hover{background:#3C3C3C;}")
        self.btn_asignar_cliente.clicked.connect(self._asignar_cliente)
        cliente_row.addWidget(self.btn_asignar_cliente)
        lay_izq.addLayout(cliente_row)

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
        self.spin_porcentaje.valueChanged.connect(self._actualizar_total)
        porc_lay.addWidget(lbl_porc)
        porc_lay.addWidget(self.spin_porcentaje)
        totales_row.addLayout(porc_lay)

        # Total manual (escribir el monto final directamente)
        monto_lay = QVBoxLayout()
        lbl_monto = QLabel("Total a cobrar $:")
        lbl_monto.setStyleSheet("color:#AAAAAA; font-size:10pt;")
        self.spin_total_final = QDoubleSpinBox()
        self.spin_total_final.setRange(0, 99999999)
        self.spin_total_final.setDecimals(2)
        self.spin_total_final.setSingleStep(100)
        self.spin_total_final.setPrefix("$ ")
        self.spin_total_final.setMinimumWidth(140)
        self.spin_total_final.setToolTip(
            "Escribí el monto exacto a cobrar.\n"
            "El % de descuento/recargo se ajusta automáticamente.")
        self.spin_total_final.valueChanged.connect(self._on_total_manual_changed)
        monto_lay.addWidget(lbl_monto)
        monto_lay.addWidget(self.spin_total_final)
        totales_row.addLayout(monto_lay)
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
        lay_der.setSpacing(6)
        lay_der.setContentsMargins(8, 12, 16, 16)

        lbl_mp = QLabel("Medio de Pago / Montos")
        lbl_mp.setStyleSheet(
            "font-weight:700; color:#C9A84C; font-size:12pt;")
        lay_der.addWidget(lbl_mp)

        # ── Panel de montos por método ────────────────────────
        # Cada fila: [botón método]  [campo monto]
        # Un campo distinto por medio de pago, sumable (pago mixto)
        self._montos: dict[str, QLineEdit] = {}
        _locale_c = QLocale(QLocale.Language.C)   # punto = decimal siempre
        validator = QDoubleValidator(0, 99999999, 2)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        validator.setLocale(_locale_c)

        for texto, valor, obj_name in self.MEDIOS_PAGO:
            fila = QHBoxLayout()
            fila.setSpacing(6)

            btn = QPushButton(texto)
            btn.setObjectName(obj_name)
            btn.setMinimumHeight(36)
            btn.setCheckable(True)
            # Al clickear el botón: focus + selecciona el campo
            txt = QLineEdit("0")
            txt.setFixedWidth(105)
            txt.setAlignment(Qt.AlignmentFlag.AlignRight)
            txt.setValidator(validator)
            txt.setStyleSheet(
                "QLineEdit{background:#2C2C2C;border:1px solid #444;"
                "border-radius:5px;padding:4px 8px;font-size:11pt;"
                "color:#F5F5F5;}"
                "QLineEdit:focus{border:2px solid #C9A84C;}"
            )
            txt.textEdited.connect(
                lambda text, t=txt, v=valor: self._on_monto_editado(t, v))

            btn.clicked.connect(
                lambda checked, t=txt, v=valor: self._toggle_metodo(t, v, checked))

            self._montos[valor] = txt
            fila.addWidget(btn, 1)
            fila.addWidget(txt)
            lay_der.addLayout(fila)

        # Indicador de pendiente
        self.lbl_pendiente = QLabel("")
        self.lbl_pendiente.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_pendiente.setStyleSheet("font-size:10pt; font-weight:700; padding:2px 0;")
        lay_der.addWidget(self.lbl_pendiente)

        btn_extraccion = QPushButton("📦  Extracción al costo")
        btn_extraccion.setMinimumHeight(34)
        btn_extraccion.setStyleSheet(
            "QPushButton{background:#4A3728;color:#FFCC80;font-weight:700;"
            "border-radius:6px;font-size:9pt;border:1px solid #7D5A45;}"
            "QPushButton:hover{background:#5D4037;}"
            "QPushButton:pressed{background:#3E2723;}"
        )
        btn_extraccion.setToolTip(
            "Sacar mercandría al precio de costo\n"
            "(sin cobro, solo descuenta stock)")
        btn_extraccion.clicked.connect(self._confirmar_extraccion)
        lay_der.addWidget(btn_extraccion)

        lay_der.addSpacing(4)
        linea = QFrame()
        linea.setFrameShape(QFrame.Shape.HLine)
        linea.setStyleSheet("color: #333;")
        lay_der.addWidget(linea)

        btn_cobrar = QPushButton("✅  COBRAR  (F12)")
        btn_cobrar.setMinimumHeight(52)
        btn_cobrar.setStyleSheet(
            "QPushButton { background-color: #2E7D32; font-size:15pt;"
            " font-weight:900; border-radius:10px; color:white; }"
            "QPushButton:hover { background-color: #388E3C; }"
            "QPushButton:pressed { background-color: #1B5E20; }"
        )
        btn_cobrar.clicked.connect(self._confirmar_venta)
        lay_der.addWidget(btn_cobrar)
        self.btn_cobrar = btn_cobrar

        btn_vaciar = QPushButton("🗑  Vaciar carrito")
        btn_vaciar.setObjectName("btn_secundario")
        btn_vaciar.clicked.connect(self._vaciar_carrito)
        lay_der.addWidget(btn_vaciar)

        lay_der.addSpacing(4)
        lbl_ult = QLabel("Últimas ventas del día")
        lbl_ult.setStyleSheet("color:#888; font-size:9pt; font-weight:700;")
        lay_der.addWidget(lbl_ult)

        self.lista_ultimas = QListWidget()
        self.lista_ultimas.setMaximumHeight(130)
        self.lista_ultimas.setStyleSheet("font-size:9pt;")
        self.lista_ultimas.setToolTip("Doble clic para ver el detalle de la venta")
        self.lista_ultimas.itemDoubleClicked.connect(self._ver_detalle_venta)
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

    # ── Cliente asignado ──────────────────────────────────────

    def _asignar_cliente(self):
        from ui.clientes import BuscadorClientes
        dlg = BuscadorClientes(self)
        dlg.cliente_seleccionado.connect(self._on_cliente_seleccionado)
        dlg.exec()

    def _on_cliente_seleccionado(self, cliente: dict):
        self._cliente_id     = cliente["id"]
        self._cliente_saldo  = db.saldo_cliente(cliente["id"])
        nombre_completo = f"{cliente['nombre']} {cliente.get('apellido') or ''}".strip()
        self._cliente_nombre = nombre_completo
        saldo_txt = (f"  —  💳 Debe: ${self._cliente_saldo:,.2f}"
                     if self._cliente_saldo > 0.01 else "  ✅ Sin deuda")
        color = "#FF9800" if self._cliente_saldo > 0.01 else "#4CAF50"
        self.lbl_cliente.setText(f"👤  {nombre_completo}{saldo_txt}")
        self.lbl_cliente.setStyleSheet(f"color:{color}; font-size:9pt; padding:2px 0;")
        self.btn_asignar_cliente.setText("✕ Quitar")
        self.btn_asignar_cliente.setStyleSheet(
            "QPushButton{background:#2C2C2C;border:1px solid #555;border-radius:4px;"
            "color:#F44336;font-size:8pt;}"
            "QPushButton:hover{background:#3C3C3C;}")
        self.btn_asignar_cliente.clicked.disconnect()
        self.btn_asignar_cliente.clicked.connect(self._quitar_cliente)

    def _quitar_cliente(self):
        self._cliente_id    = None
        self._cliente_saldo = 0.0
        self._cliente_nombre = ""
        self.lbl_cliente.setText("👤  Sin cliente asignado")
        self.lbl_cliente.setStyleSheet("color:#555; font-size:9pt; padding:2px 0;")
        self.btn_asignar_cliente.setText("+ Asignar")
        self.btn_asignar_cliente.setStyleSheet(
            "QPushButton{background:#2C2C2C;border:1px solid #555;border-radius:4px;"
            "color:#C9A84C;font-size:8pt;}"
            "QPushButton:hover{background:#3C3C3C;}")
        self.btn_asignar_cliente.clicked.disconnect()
        self.btn_asignar_cliente.clicked.connect(self._asignar_cliente)
        # Limpiar campo fiado
        if "fiado" in self._montos:
            self._montos["fiado"].setText("0")
        self._actualizar_pendiente()

    # ── Escaneo ───────────────────────────────────────────────

    def _setup_completer(self):
        """QCompleter con búsqueda por substring sobre nombres de productos."""
        self._completer_model = QStringListModel()
        completer = QCompleter(self._completer_model, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        # MatchContains = buscar en cualquier parte del nombre
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setMaxVisibleItems(10)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.scan_input.setCompleter(completer)
        self.scan_input.textChanged.connect(self._actualizar_sugerencias)
        completer.activated.connect(self._sugerencia_elegida)
        self._completer = completer

    def _actualizar_sugerencias(self, texto: str):
        """Actualiza el modelo del completer solo cuando hay letras.
        Si el texto es puramente numérico y coincide con un código de barras,
        agrega el producto al instante sin necesidad de Enter."""
        texto = texto.strip()
        # Si es todo numérico: buscar coincidencia exacta de código de barras
        if texto.isdigit() and len(texto) >= 3:
            producto = db.buscar_por_codigo(texto)
            if producto:
                self._completando = True
                self._agregar_al_carrito(dict(producto))
                self.scan_input.clear()
                QTimer.singleShot(0, lambda: setattr(self, "_completando", False))
                return
        # Si es numérico sin coincidencia, o muy corto: no mostrar sugerencias de nombre
        if not texto or texto.isdigit() or len(texto) < 2:
            self._completer_model.setStringList([])
            return
        resultados = db.buscar_por_nombre(texto)
        self._sugerencias_cache = {
            p["nombre"]: dict(p) for p in resultados
        }
        etiquetas = [
            f"{p['nombre']}  |  ${p['precio_venta']:.2f}  |  Stock: {p['stock_actual']}"
            for p in resultados
        ]
        self._completer_model.setStringList(etiquetas)

    def _sugerencia_elegida(self, texto: str):
        """El usuario eligió una sugerencia del dropdown."""
        nombre = texto.split("  |  ")[0].strip()
        producto = self._sugerencias_cache.get(nombre)
        if producto:
            self._completando = True
            self._agregar_al_carrito(producto)
            self.scan_input.clear()
            QTimer.singleShot(0, lambda: setattr(self, "_completando", False))

    def _procesar_escaneo(self):
        if self._completando:
            return
        codigo = self.scan_input.text().strip()
        if not codigo:
            return
        self.scan_input.clear()
        # 1) Intentar código de barras
        producto = db.buscar_por_codigo(codigo)
        if producto:
            self._agregar_al_carrito(dict(producto))
            return
        # 2) Si hay exactamente 1 coincidencia por nombre, agregar directo
        if not codigo.isdigit():
            resultados = db.buscar_por_nombre(codigo)
            if len(resultados) == 1:
                self._agregar_al_carrito(dict(resultados[0]))
                return
            if len(resultados) > 1:
                # Hay varias coincidencias: abrir el buscador con el texto prefiltrado
                dlg = BuscadorProductos(self, texto_inicial=codigo)
                dlg.producto_seleccionado.connect(self._agregar_al_carrito)
                dlg.exec()
                QTimer.singleShot(100, self.scan_input.setFocus)
                return
        QMessageBox.warning(
            self, "Código no encontrado",
            f"No se encontró: {codigo}\n"
            "Escribí el nombre para ver sugerencias.")

    def _abrir_buscador(self):
        dlg = BuscadorProductos(self)
        dlg.producto_seleccionado.connect(self._agregar_al_carrito)
        dlg.exec()
        QTimer.singleShot(100, self.scan_input.setFocus)

    # ── Carrito ───────────────────────────────────────────────

    def _agregar_al_carrito(self, producto: dict):
        # Si ya está en el carrito, solo sumar cantidad
        for item in self.carrito:
            if item.producto_id == producto["id"] and item.lote_id is None:
                item.cantidad += 1
                self._refrescar_tabla()
                return

        # Verificar si tiene múltiples lotes distintos
        lotes = db.obtener_lotes_producto(producto["id"])

        lote_id = None
        cosecha = None

        if len(lotes) > 1:
            # Mostrar selector de lote
            opciones = []
            for l in lotes:
                venc = l["fecha_vencimiento"]
                SENTINEL = "2000-01-01"
                venc_txt = f"  —  vence {venc[:10]}" if (venc and venc[:10] != SENTINEL) else ""
                if l["cosecha"]:
                    opciones.append(f"Cosecha {l['cosecha']}  ({l['cantidad']} en stock{venc_txt})")
                else:
                    opciones.append(f"Sin cosecha especificada  ({l['cantidad']} en stock{venc_txt})")

            dlg = QDialog(self)
            dlg.setWindowTitle(f"Seleccionar lote — {producto['nombre']}")
            dlg.setMinimumWidth(400)
            dlg.setModal(True)
            lay_dlg = QVBoxLayout(dlg)
            lay_dlg.setSpacing(10)
            lay_dlg.setContentsMargins(20, 16, 20, 16)

            lbl = QLabel(f"<b>{producto['nombre']}</b> tiene varios lotes disponibles.\n"
                         "¿Cuál vas a vender?")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("font-size:11pt; color:#F5F5F5;")
            lay_dlg.addWidget(lbl)

            from PyQt6.QtWidgets import QListWidget as _QListWidget
            lista_sel = _QListWidget()
            lista_sel.addItems(opciones)
            lista_sel.setCurrentRow(0)
            lista_sel.setStyleSheet("font-size:10pt;")
            lay_dlg.addWidget(lista_sel)

            btn_row = QHBoxLayout()
            btn_ok = QPushButton("✅  Seleccionar")
            btn_ok.setStyleSheet(
                "QPushButton{background:#722F37;color:white;font-weight:700;"
                "border-radius:6px;padding:6px 16px;}"
                "QPushButton:hover{background:#8B3A44;}")
            btn_cancel = QPushButton("Cancelar")
            btn_cancel.setObjectName("btn_secundario")
            btn_ok.clicked.connect(dlg.accept)
            btn_cancel.clicked.connect(dlg.reject)
            btn_row.addWidget(btn_ok)
            btn_row.addWidget(btn_cancel)
            lay_dlg.addLayout(btn_row)
            lista_sel.itemDoubleClicked.connect(lambda _: dlg.accept())

            if dlg.exec() != QDialog.DialogCode.Accepted:
                return

            idx = lista_sel.currentRow()
            lote_sel = lotes[idx]
            lote_id = lote_sel["id"]
            cosecha = lote_sel["cosecha"]

        # Verificar si ya hay un item con ese lote_id
        for item in self.carrito:
            if item.producto_id == producto["id"] and item.lote_id == lote_id:
                item.cantidad += 1
                self._refrescar_tabla()
                return

        self.carrito.append(ItemCarrito(producto, lote_id=lote_id, cosecha=cosecha))
        self._refrescar_tabla()

    def _refrescar_tabla(self):
        self.tabla.setRowCount(len(self.carrito))
        for i, item in enumerate(self.carrito):
            sin_stock = item.cantidad > item.stock_actual
            nombre_txt = item.nombre
            if sin_stock:
                nombre_txt = f"⚠️ {item.nombre}  (stock: {item.stock_actual}, pedido: {item.cantidad})"
            nombre_it = QTableWidgetItem(nombre_txt)
            if sin_stock:
                nombre_it.setForeground(QColor("#FF9800"))
                nombre_it.setToolTip(
                    f"Stock disponible: {item.stock_actual} — "
                    "Podés confirmar la venta igual si el stock no está actualizado.")
            self.tabla.setItem(i, 0, nombre_it)
            self.tabla.setItem(i, 1, QTableWidgetItem(
                f"${item.precio_unit:.2f}"))
            spin = QSpinBox()
            spin.setRange(1, 9999)
            spin.setValue(item.cantidad)
            spin.valueChanged.connect(
                lambda val, idx=i: self._cambiar_cantidad(idx, val))
            self.tabla.setCellWidget(i, 2, spin)
            # Col 3: subtotal editable (promo manual)
            spin_sub = QDoubleSpinBox()
            spin_sub.setRange(0, 99999999)
            spin_sub.setDecimals(2)
            spin_sub.setPrefix("$ ")
            spin_sub.setSingleStep(100)
            spin_sub.setValue(item.subtotal)
            spin_sub.setStyleSheet(
                "QDoubleSpinBox{background:#1E1E1E;color:#F5F5F5;"
                "border:1px solid #444;border-radius:4px;padding:2px 4px;}"
                "QDoubleSpinBox:focus{border:1px solid #C9A84C;color:#FFD700;}"
            )
            if item.subtotal_override is not None:
                spin_sub.setStyleSheet(
                    "QDoubleSpinBox{background:#2A1E00;color:#FFD700;"
                    "border:1px solid #C9A84C;border-radius:4px;padding:2px 4px;}"
                )
            spin_sub.setToolTip(
                "Editá el subtotal para aplicar un precio promo.\n"
                "Si cambiás la cantidad, vuelve al precio normal.")
            spin_sub.valueChanged.connect(
                lambda val, idx=i: self._cambiar_subtotal(idx, val))
            self.tabla.setCellWidget(i, 3, spin_sub)
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
            item = self.carrito[idx]
            item.cantidad = valor
            item.subtotal_override = None   # reset promo al cambiar cantidad
            # Actualizar celda nombre
            sin_stock = item.cantidad > item.stock_actual
            nombre_base = item.nombre
            if item.cosecha:
                nombre_base = f"{item.nombre}  [{item.cosecha}]"
            nombre_txt = nombre_base
            if sin_stock:
                nombre_txt = f"⚠️ {nombre_base}  (stock: {item.stock_actual}, pedido: {item.cantidad})"
            nombre_it = QTableWidgetItem(nombre_txt)
            if sin_stock:
                nombre_it.setForeground(QColor("#FF9800"))
                nombre_it.setToolTip(
                    f"Stock disponible: {item.stock_actual} — "
                    "Podés confirmar la venta igual si el stock no está actualizado.")
            self.tabla.setItem(idx, 0, nombre_it)
            # Refrescar el spin de subtotal
            spin_sub = self.tabla.cellWidget(idx, 3)
            if spin_sub:
                spin_sub.blockSignals(True)
                spin_sub.setValue(item.subtotal)
                spin_sub.setStyleSheet(
                    "QDoubleSpinBox{background:#1E1E1E;color:#F5F5F5;"
                    "border:1px solid #444;border-radius:4px;padding:2px 4px;}"
                    "QDoubleSpinBox:focus{border:1px solid #C9A84C;color:#FFD700;}"
                )
                spin_sub.blockSignals(False)
            self._actualizar_total()

    def _cambiar_subtotal(self, idx: int, valor: float):
        if idx < len(self.carrito):
            item = self.carrito[idx]
            normal = item.precio_unit * item.cantidad
            if abs(valor - normal) < 0.01:
                item.subtotal_override = None
            else:
                item.subtotal_override = round(valor, 2)
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
                self.spin_total_final.setValue(0)
                for metodo, txt in self._montos.items():
                    txt.setText("0")
                self._manually_edited.clear()
                self._refrescar_tabla()
        self.scan_input.setFocus()

    def _actualizar_total(self):
        subtotal   = sum(i.subtotal for i in self.carrito)
        porcentaje = self.spin_porcentaje.value()
        total      = round(subtotal * (1 + porcentaje / 100), 2)
        self.lbl_total.setText(f"${total:,.2f}")
        if not self._ajustando_total:
            self._ajustando_total = True
            self.spin_total_final.setValue(total)
            self._ajustando_total = False
        self._actualizar_lbl_total(porcentaje)
        self._actualizar_pendiente()

    def _actualizar_lbl_total(self, porcentaje: float):
        if porcentaje > 0:
            self.lbl_tit_total.setText(f"TOTAL  (+{porcentaje:.1f}% recargo)")
            self.lbl_tit_total.setStyleSheet(
                "color:#EF5350; font-size:10pt; font-weight:600;")
        elif porcentaje < 0:
            self.lbl_tit_total.setText(f"TOTAL  ({porcentaje:.1f}% desc.)")
            self.lbl_tit_total.setStyleSheet(
                "color:#66BB6A; font-size:10pt; font-weight:600;")
        else:
            self.lbl_tit_total.setText("TOTAL A COBRAR")
            self.lbl_tit_total.setStyleSheet(
                "color:#AAAAAA; font-size:10pt; font-weight:600;")

    def _on_total_manual_changed(self, total: float):
        """Cuando el usuario escribe el monto final: back-calcula el %."""
        if self._ajustando_total:
            return
        subtotal = sum(i.subtotal for i in self.carrito)
        self._ajustando_total = True
        if subtotal > 0:
            porcentaje = round((total / subtotal - 1) * 100, 1)
            self.spin_porcentaje.setValue(porcentaje)
            self._actualizar_lbl_total(porcentaje)
        self.lbl_total.setText(f"${total:,.2f}")
        self._ajustando_total = False
        self._actualizar_pendiente()

    def _set_medio_pago(self, valor: str):
        # Compatibilidad retroactiva (no se usa en nuevo UI)
        self.medio_pago_actual = valor

    def _toggle_metodo(self, txt: QLineEdit, valor: str, checked: bool = True):
        """Al clickear un botón de método: si se deselecciona limpia el campo;
        si se selecciona completa con el monto restante si el campo estaba en 0."""
        # Fiado requiere cliente asignado
        if valor == "fiado" and checked and not self._cliente_id:
            QMessageBox.warning(
                self, "Sin cliente",
                "Para usar Fiado primero asigná un cliente con el botón '+ Asignar'.")
            txt.setText("0")
            self._actualizar_pendiente()
            return
        if not checked:
            txt.setText("0")
            self._manually_edited.discard(valor)
            self._actualizar_pendiente()
            return
        val_actual = _safe_float(txt.text())
        if val_actual <= 0.005:
            total = self._total_actual()
            otros = sum(_safe_float(t.text()) for m, t in self._montos.items() if m != valor)
            restante = max(0.0, total - otros)
            if restante > 0.005:
                txt.setText(f"{restante:.2f}")
        txt.setFocus()
        txt.selectAll()
        self._actualizar_pendiente()

    def _on_monto_editado(self, txt_editado: QLineEdit = None, valor_editado: str = None):
        """Recalcula el pendiente. Si el usuario está editando un campo
        y hay exactamente UN campo activo no-manual en otros métodos,
        lo ajusta automáticamente para que la suma dé el total."""
        if valor_editado is not None:
            self._manually_edited.add(valor_editado)
        if txt_editado is not None and valor_editado is not None:
            valor_nuevo = _safe_float(txt_editado.text())
            total = self._total_actual()
            # Solo auto-ajustar campos que NO fueron escritos manualmente
            otros_ajustables = [
                (m, t) for m, t in self._montos.items()
                if m != valor_editado
                and _safe_float(t.text()) > 0.005
                and m not in self._manually_edited
            ]
            if len(otros_ajustables) == 1:
                _, t_otro = otros_ajustables[0]
                restante = max(0.0, total - valor_nuevo)
                t_otro.blockSignals(True)
                t_otro.setText(f"{restante:.2f}")
                t_otro.blockSignals(False)
        self._actualizar_pendiente()

    def _total_actual(self) -> float:
        subtotal   = sum(i.subtotal for i in self.carrito)
        porcentaje = self.spin_porcentaje.value()
        return subtotal * (1 + porcentaje / 100)

    def _get_pagos(self) -> list:
        """Devuelve lista de pagos activos (monto > 0)."""
        pagos = []
        for metodo, txt in self._montos.items():
            monto = _safe_float(txt.text())
            if monto > 0.005:
                pagos.append({"metodo": metodo, "monto": round(monto, 2)})
        return pagos

    def _actualizar_pendiente(self):
        total = self._total_actual()
        # Fiado sin cliente → ignorar ese monto
        asignado = 0.0
        for metodo, txt in self._montos.items():
            monto = _safe_float(txt.text())
            if metodo == "fiado" and not self._cliente_id:
                monto = 0.0
            if monto > 0.005:
                asignado += monto
        pendiente = total - asignado
        # Actualizar estado de botones de método
        for metodo, txt in self._montos.items():
            monto = _safe_float(txt.text())
            txt.setStyleSheet(
                "QLineEdit{background:#1A2A1A;border:1px solid #2E7D32;"
                "border-radius:5px;padding:4px 8px;font-size:11pt;color:#81C784;}"
                "QLineEdit:focus{border:2px solid #C9A84C;}"
                if monto > 0.005 else
                "QLineEdit{background:#2C2C2C;border:1px solid #444;"
                "border-radius:5px;padding:4px 8px;font-size:11pt;color:#F5F5F5;}"
                "QLineEdit:focus{border:2px solid #C9A84C;}"
            )
        if total <= 0:
            self.lbl_pendiente.setText("")
            self.btn_cobrar.setEnabled(True)
            return
        if abs(pendiente) < 0.5:
            self.lbl_pendiente.setText("✅  Monto completo")
            self.lbl_pendiente.setStyleSheet(
                "color:#66BB6A; font-size:10pt; font-weight:700; padding:2px 0;")
            self.btn_cobrar.setEnabled(True)
        elif pendiente > 0:
            self.lbl_pendiente.setText(f"Faltan: ${pendiente:,.2f}")
            self.lbl_pendiente.setStyleSheet(
                "color:#FF9800; font-size:10pt; font-weight:700; padding:2px 0;")
            self.btn_cobrar.setEnabled(False)
        else:
            # Exceso: si hay cliente, el exceso cancela deuda → OK
            exceso = -pendiente
            if self._cliente_id and self._cliente_saldo > 0.01:
                cancela = min(exceso, self._cliente_saldo)
                self.lbl_pendiente.setText(
                    f"↘ Cancela deuda: ${cancela:,.2f}")
                self.lbl_pendiente.setStyleSheet(
                    "color:#4CAF50; font-size:10pt; font-weight:700; padding:2px 0;")
                self.btn_cobrar.setEnabled(True)
            else:
                self.lbl_pendiente.setText(f"Exceso: ${exceso:,.2f}")
                self.lbl_pendiente.setStyleSheet(
                    "color:#EF5350; font-size:10pt; font-weight:700; padding:2px 0;")
                self.btn_cobrar.setEnabled(False)

    # ── Confirmar venta ───────────────────────────────────────

    def _confirmar_venta(self):
        if not self.carrito:
            QMessageBox.information(self, "Carrito vacío",
                "Agregá al menos un producto antes de cobrar.")
            return

        # Verificar productos con stock insuficiente
        sin_stock = [(i.nombre, i.stock_actual, i.cantidad)
                     for i in self.carrito if i.cantidad > i.stock_actual]
        if sin_stock:
            detalle = "\n".join(
                f"  • {nom}: stock {st}, pedido {ped}"
                for nom, st, ped in sin_stock)
            resp = QMessageBox.question(
                self, "⚠️  Stock insuficiente",
                f"Los siguientes productos tienen stock insuficiente:\n\n{detalle}\n\n"
                "Podés confirmar igual (por ej. si el stock no está cargado aún).\n"
                "¿Confirmar la venta de todas formas?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if resp == QMessageBox.StandardButton.No:
                return

        subtotal   = sum(i.subtotal for i in self.carrito)
        porcentaje = self.spin_porcentaje.value()
        total      = round(self.spin_total_final.value(), 2)

        pagos = self._get_pagos()
        if not pagos:
            QMessageBox.warning(self, "Sin monto", "Ingresá el monto a cobrar.")
            return

        medio_display = pagos[0]["metodo"] if len(pagos) == 1 else "mixto"

        dlg = ConfirmacionVenta(
            self, carrito=self.carrito,
            subtotal=subtotal, descuento=0,
            porcentaje=porcentaje,
            total=total, medio_pago=medio_display,
            nombre_cliente=self.nombre_cliente,
            pagos=pagos,
            cliente_nombre=self._cliente_nombre,
            cliente_saldo=self._cliente_saldo)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            items_db = [
                {"producto_id": i.producto_id,
                 "cantidad":    i.cantidad,
                 "precio_unit": i.precio_unit,
                 "lote_id":     i.lote_id}
                for i in self.carrito
            ]
            try:
                # Calcular lo que va a fiado (si aplica)
                monto_fiado = 0.0
                monto_excess = 0.0
                if self._cliente_id:
                    pagos_sin_fiado = [p for p in pagos if p["metodo"] != "fiado"]
                    pagado_real = sum(p["monto"] for p in pagos_sin_fiado)
                    fiado_explicito = next(
                        (p["monto"] for p in pagos if p["metodo"] == "fiado"), 0.0)
                    monto_fiado = fiado_explicito
                    # Exceso por encima del total → cancela deuda
                    exceso = round(pagado_real - total, 2)
                    if exceso > 0.01 and self._cliente_saldo > 0.01:
                        monto_excess = min(exceso, self._cliente_saldo)
                    # Ajustar pagos enviados a DB (excluir "fiado" como método)
                    pagos_db = pagos_sin_fiado if pagos_sin_fiado else None
                    medio_db = (pagos_db[0]["metodo"] if pagos_db and len(pagos_db) == 1
                                else ("mixto" if pagos_db and len(pagos_db) > 1
                                      else "fiado"))
                else:
                    pagos_db = pagos
                    medio_db = medio_display

                venta_id = db.registrar_venta(
                    items_db, medio_db,
                    descuento=0, recargo_pct=porcentaje,
                    pagos=pagos_db,
                    cliente_id=self._cliente_id)

                # Registrar movimientos de fiado
                if self._cliente_id:
                    if monto_fiado > 0.01:
                        db.registrar_movimiento_fiado(
                            self._cliente_id, "cargo", monto_fiado,
                            f"Venta fiada #{venta_id}", venta_id)
                    if monto_excess > 0.01:
                        db.registrar_movimiento_fiado(
                            self._cliente_id, "abono", monto_excess,
                            f"Abono en venta #{venta_id}", venta_id)

                self.carrito.clear()
                self.spin_porcentaje.setValue(0)
                self.spin_total_final.setValue(0)
                for txt in self._montos.values():
                    txt.setText("0")
                self._manually_edited.clear()
                self._refrescar_tabla()
                self._cargar_ultimas_ventas()
                self.venta_realizada.emit(venta_id)
                self.scan_input.setFocus()

                msg = f"Venta #{venta_id} registrada.\nTotal cobrado: ${total:,.2f}"
                if self._cliente_id and monto_fiado > 0.01:
                    nuevo_saldo = db.saldo_cliente(self._cliente_id)
                    msg += f"\n💳 Fiado: ${monto_fiado:,.2f}  |  Deuda total: ${nuevo_saldo:,.2f}"
                if self._cliente_id and monto_excess > 0.01:
                    msg += f"\n✅ Abonó ${monto_excess:,.2f} de deuda anterior."

                # Limpiar cliente asignado para la próxima venta
                if self._cliente_id is not None:
                    self._quitar_cliente()

                QMessageBox.information(self, "✅  Venta registrada", msg)
            except Exception as e:
                QMessageBox.critical(self, "Error al registrar", str(e))

    # ── Extracción de mercadería ───────────────────────────────

    def _confirmar_extraccion(self):
        """Registrar salida de mercadería al precio de costo (sin cobro en caja)."""
        if not self.carrito:
            QMessageBox.information(
                self, "Carrito vacío",
                "Agregá productos antes de procesar una extracción.")
            return
        total_costo = sum(i.precio_costo * i.cantidad for i in self.carrito)
        detalle = "\n".join(
            f"  {i.cantidad}x {i.nombre}  →  ${i.precio_costo * i.cantidad:,.2f}"
            for i in self.carrito)
        resp = QMessageBox.question(
            self, "📦  Extracción de mercadería",
            f"Se registrará la salida al precio de costo:\n\n{detalle}\n\n"
            f"Total al costo: ${total_costo:,.2f}\n\n"
            "El stock se descuenta. No se registra cobro en caja.\n"
            "¿Confirmar extracción?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp != QMessageBox.StandardButton.Yes:
            return
        items_db = [
            {"producto_id": i.producto_id,
             "cantidad":    i.cantidad,
             "precio_unit": i.precio_costo,
             "lote_id":     i.lote_id}
            for i in self.carrito
        ]
        try:
            venta_id = db.registrar_venta(
                items_db, "extraccion", descuento=0, recargo_pct=0,
                cliente_id=self._cliente_id)

            # Registrar en la cuenta del cliente si hay uno asignado
            if self._cliente_id:
                detalle_txt = ", ".join(
                    f"{i.cantidad}x {i.nombre}" for i in self.carrito)
                db.registrar_movimiento_fiado(
                    self._cliente_id, "cargo", total_costo,
                    f"Extracción #{venta_id}: {detalle_txt}", venta_id)

            self.carrito.clear()
            self.spin_porcentaje.setValue(0)
            self.spin_total_final.setValue(0)
            for txt in self._montos.values():
                txt.setText("0")
            self._manually_edited.clear()
            self._refrescar_tabla()
            self._cargar_ultimas_ventas()
            self.venta_realizada.emit(venta_id)

            # Limpiar cliente asignado
            if self._cliente_id is not None:
                self._quitar_cliente()

            self.scan_input.setFocus()
            QMessageBox.information(
                self, "✅  Extracción registrada",
                f"Extracción #{venta_id} registrada.\n"
                f"Total al costo: ${total_costo:,.2f}")
        except Exception as e:
            QMessageBox.critical(self, "Error al registrar extracción", str(e))

    # ── Últimas ventas ─────────────────────────────────────────

    def _cargar_ultimas_ventas(self):
        self.lista_ultimas.clear()
        icons = {"efectivo": "💵", "debito": "💳", "credito": "🏦",
                 "transferencia": "📲", "qr": "🔲",
                 "mixto": "💰", "extraccion": "📦"}
        for v in db.ventas_del_dia()[:15]:
            ic = icons.get(v["medio_pago"], "💰")
            item = QListWidgetItem(
                f"#{v['id']}  {ic}  ${v['total']:,.2f}  –  {v['hora'][:5]}")
            item.setData(Qt.ItemDataRole.UserRole, v["id"])
            self.lista_ultimas.addItem(item)

    def _ver_detalle_venta(self, item):
        venta_id = item.data(Qt.ItemDataRole.UserRole)
        if venta_id is None:
            return
        datos = db.detalle_venta(venta_id)
        v = datos["venta"]
        items = datos["items"]

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Detalle venta #{venta_id}")
        dlg.setMinimumWidth(520)
        dlg.setModal(True)
        lay = QVBoxLayout(dlg)
        lay.setSpacing(10)
        lay.setContentsMargins(20, 18, 20, 18)

        icons = {"efectivo": "💵", "debito": "💳", "credito": "🏦",
                 "transferencia": "📲", "qr": "🔲"}
        medio = icons.get(v["medio_pago"], "💰") + "  " + v["medio_pago"].capitalize()
        titulo = QLabel(f"📝  Venta #{venta_id}   —   {v['fecha']}  {v['hora'][:5]}")
        titulo.setObjectName("titulo_seccion")
        lay.addWidget(titulo)

        info = QLabel(f"Medio de pago: {medio}   •   Total: $ {v['total']:,.2f}")
        info.setStyleSheet("color:#C9A84C; font-weight:700; font-size:11pt;")
        lay.addWidget(info)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#333;")
        lay.addWidget(sep)

        tabla = QTableWidget(len(items), 4)
        tabla.setHorizontalHeaderLabels(["Producto", "Cosecha", "Cant.", "Subtotal"])
        tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        tabla.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        tabla.verticalHeader().setVisible(False)
        tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tabla.setAlternatingRowColors(True)
        tabla.setMaximumHeight(min(44 * len(items) + 36, 300))
        for i, d in enumerate(items):
            tabla.setItem(i, 0, QTableWidgetItem(d["nombre"]))
            cosecha = d["cosecha"]
            cosecha_txt = str(cosecha) if cosecha else "—"
            tabla.setItem(i, 1, QTableWidgetItem(cosecha_txt))
            cant_it = QTableWidgetItem(str(d["cantidad"]))
            cant_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tabla.setItem(i, 2, cant_it)
            sub_it = QTableWidgetItem(f"$ {d['subtotal']:,.2f}")
            sub_it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            tabla.setItem(i, 3, sub_it)
            tabla.setRowHeight(i, 40)
        lay.addWidget(tabla)

        btn = QPushButton("Cerrar")
        btn.setObjectName("btn_secundario")
        btn.clicked.connect(dlg.accept)
        lay.addWidget(btn)
        dlg.exec()

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
                 nombre_cliente="", porcentaje=0, pagos=None,
                 cliente_nombre="", cliente_saldo=0.0):
        super().__init__(parent)
        titulo = f"Confirmar Venta — {nombre_cliente}" if nombre_cliente else "Confirmar Venta"
        self.setWindowTitle(titulo)
        self.setMinimumWidth(420)
        self.setModal(True)
        self._build(carrito, subtotal, descuento, total, medio_pago, porcentaje,
                    pagos, cliente_nombre, cliente_saldo)

    def _build(self, carrito, subtotal, descuento, total, medio_pago,
               porcentaje=0, pagos=None, cliente_nombre="", cliente_saldo=0.0):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(24, 20, 24, 20)

        # Cliente asignado (si hay)
        if cliente_nombre:
            lbl_cli = QLabel(f"👤  {cliente_nombre}")
            lbl_cli.setStyleSheet("font-size:11pt; font-weight:700; color:#C9A84C;")
            lay.addWidget(lbl_cli)
            if cliente_saldo > 0.01:
                lbl_deuda = QLabel(f"💳  Deuda previa: ${cliente_saldo:,.2f}")
                lbl_deuda.setStyleSheet("color:#FF9800; font-size:10pt;")
                lay.addWidget(lbl_deuda)

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

        # Desglose de pagos
        mp_labels = {"efectivo": "💵 Efectivo", "debito": "💳 Débito",
                     "credito": "🏦 Crédito", "transferencia": "📲 Transferencia",
                     "qr": "🔲 QR", "mixto": "🔀 Pago mixto", "fiado": "🤝 Fiado"}
        if pagos and len(pagos) > 1:
            lbl_mp = QLabel("🔀  Pago mixto:")
            lbl_mp.setStyleSheet("font-weight:700; color:#C9A84C; font-size:12pt;")
            lay.addWidget(lbl_mp)
            for p in pagos:
                nombre_metodo = mp_labels.get(p["metodo"], p["metodo"].capitalize())
                lbl_p = QLabel(f"     {nombre_metodo}:   ${p['monto']:,.2f}")
                lbl_p.setStyleSheet("color:#DDDDDD; font-size:11pt;")
                lay.addWidget(lbl_p)
        else:
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
