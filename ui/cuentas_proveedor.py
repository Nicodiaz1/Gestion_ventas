# ─────────────────────────────────────────────────────────────
#  ui/cuentas_proveedor.py  –  Cuentas corrientes de proveedores
# ─────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QLineEdit, QDoubleSpinBox, QSpinBox, QDateEdit,
    QComboBox, QTextEdit, QMessageBox, QAbstractItemView,
    QFrame, QTabWidget, QSplitter, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QToolTip
from PyQt6.QtGui import QCursor
import sys, os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import database as db

try:
    import matplotlib
    matplotlib.use("QtAgg")
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class _GraficoMini(FigureCanvas if HAS_MATPLOTLIB else QWidget):
    def __init__(self, parent=None, width=6, height=3.5):
        if HAS_MATPLOTLIB:
            self.fig = Figure(figsize=(width, height), facecolor="#1A1A1A")
            super().__init__(self.fig)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        else:
            super().__init__(parent)


# ─────────────────────────────────────────────────────────────
#  Helpers de color por estado
# ─────────────────────────────────────────────────────────────
ESTADO_COLOR = {
    "pendiente":   "#FF9800",
    "vencida":     "#F44336",
    "pagada":      "#4CAF50",
    "saldo_favor": "#2196F3",
}
ESTADO_LABEL = {
    "pendiente":   "⏳ Pendiente",
    "vencida":     "🔴 Vencida",
    "pagada":      "✅ Pagada",
    "saldo_favor": "💙 Saldo a favor",
}


# ─────────────────────────────────────────────────────────────
#  Diálogo: nueva / editar factura
# ─────────────────────────────────────────────────────────────

class DialogoFactura(QDialog):
    def __init__(self, parent=None, factura: dict = None):
        super().__init__(parent)
        self.factura = factura
        es_nueva = factura is None
        self.setWindowTitle("Nueva factura" if es_nueva else "Editar factura")
        self.setMinimumWidth(480)
        self.setModal(True)
        self._build_ui()
        if not es_nueva:
            self._cargar_datos()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(24, 20, 24, 20)

        titulo = QLabel("🧾  " + self.windowTitle())
        titulo.setObjectName("titulo_seccion")
        lay.addWidget(titulo)

        form = QFormLayout()
        form.setSpacing(10)

        # Proveedor
        self.cmb_proveedor = QComboBox()
        self._cargar_proveedores()
        form.addRow("Proveedor *:", self.cmb_proveedor)

        # Número de factura
        self.txt_numero = QLineEdit()
        self.txt_numero.setPlaceholderText("Ej: 0001-00012345")
        form.addRow("N° factura:", self.txt_numero)

        # Descripción
        self.txt_desc = QLineEdit()
        self.txt_desc.setPlaceholderText("Ej: Vinos Malbec reserva – 3 cajas")
        form.addRow("Descripción:", self.txt_desc)

        # Monto total
        self.spin_total = QDoubleSpinBox()
        self.spin_total.setRange(0, 9_999_999)
        self.spin_total.setDecimals(2)
        self.spin_total.setSingleStep(100)
        self.spin_total.setPrefix("$ ")
        self.spin_total.valueChanged.connect(self._actualizar_saldo)
        form.addRow("Monto total *:", self.spin_total)

        # Monto pagado
        self.spin_pagado = QDoubleSpinBox()
        self.spin_pagado.setRange(0, 9_999_999)
        self.spin_pagado.setDecimals(2)
        self.spin_pagado.setSingleStep(100)
        self.spin_pagado.setPrefix("$ ")
        self.spin_pagado.valueChanged.connect(self._actualizar_saldo)
        form.addRow("Monto pagado:", self.spin_pagado)

        # Saldo (readonly, calculado)
        self.lbl_saldo = QLabel("$ 0.00")
        self.lbl_saldo.setStyleSheet("font-weight:700; font-size:14pt; color:#FF9800;")
        form.addRow("Saldo pendiente:", self.lbl_saldo)

        # Fecha emisión
        self.date_emision = QDateEdit(QDate.currentDate())
        self.date_emision.setCalendarPopup(True)
        self.date_emision.setDisplayFormat("dd/MM/yyyy")
        form.addRow("Fecha emisión *:", self.date_emision)

        # Fecha vencimiento
        self.date_venc = QDateEdit(QDate.currentDate().addDays(30))
        self.date_venc.setCalendarPopup(True)
        self.date_venc.setDisplayFormat("dd/MM/yyyy")
        form.addRow("Fecha vencimiento *:", self.date_venc)

        # Días de alerta
        self.spin_dias_alerta = QSpinBox()
        self.spin_dias_alerta.setRange(1, 365)
        self.spin_dias_alerta.setValue(7)
        self.spin_dias_alerta.setSuffix(" días antes")
        self.spin_dias_alerta.setToolTip(
            "El sistema te avisará cuando falten esta cantidad de días para el vencimiento")
        form.addRow("⏰ Avisar con:", self.spin_dias_alerta)

        # Notas
        self.txt_notas = QTextEdit()
        self.txt_notas.setMaximumHeight(70)
        self.txt_notas.setPlaceholderText("Notas opcionales…")
        form.addRow("Notas:", self.txt_notas)

        lay.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("btn_secundario")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_ok = QPushButton("💾  Guardar")
        btn_ok.clicked.connect(self._guardar)
        btn_row.addWidget(btn_ok)
        lay.addLayout(btn_row)

    def _cargar_proveedores(self):
        self.cmb_proveedor.clear()
        self.cmb_proveedor.addItem("— Sin proveedor —", None)
        for p in db.obtener_proveedores():
            self.cmb_proveedor.addItem(p["nombre"], p["id"])

    def _cargar_datos(self):
        f = self.factura
        # Buscar proveedor en combo
        idx = self.cmb_proveedor.findData(f.get("proveedor_id"))
        if idx >= 0:
            self.cmb_proveedor.setCurrentIndex(idx)
        self.txt_numero.setText(f.get("numero_factura") or "")
        self.txt_desc.setText(f.get("descripcion") or "")
        self.spin_total.setValue(f.get("monto_total") or 0)
        self.spin_pagado.setValue(f.get("monto_pagado") or 0)
        if f.get("fecha_emision"):
            self.date_emision.setDate(QDate.fromString(str(f["fecha_emision"])[:10], "yyyy-MM-dd"))
        if f.get("fecha_vencimiento"):
            self.date_venc.setDate(QDate.fromString(str(f["fecha_vencimiento"])[:10], "yyyy-MM-dd"))
        self.spin_dias_alerta.setValue(f.get("dias_alerta") or 7)
        self.txt_notas.setPlainText(f.get("notas") or "")

    def _actualizar_saldo(self):
        saldo = self.spin_total.value() - self.spin_pagado.value()
        if saldo > 0:
            color = "#FF9800"
            texto = f"$ {saldo:,.2f}"
        elif saldo < 0:
            color = "#2196F3"
            texto = f"💙 Saldo a favor  $ {abs(saldo):,.2f}"
        else:
            color = "#4CAF50"
            texto = "✅  Pagada"
        self.lbl_saldo.setStyleSheet(f"font-weight:700; font-size:14pt; color:{color};")
        self.lbl_saldo.setText(texto)

    def _guardar(self):
        if self.spin_total.value() == 0:
            QMessageBox.warning(self, "Monto requerido",
                                "Ingresá el monto total de la factura.")
            return
        datos = {
            "proveedor_id":      self.cmb_proveedor.currentData(),
            "numero_factura":    self.txt_numero.text().strip(),
            "descripcion":       self.txt_desc.text().strip(),
            "monto_total":       self.spin_total.value(),
            "monto_pagado":      self.spin_pagado.value(),
            "fecha_emision":     self.date_emision.date().toString("yyyy-MM-dd"),
            "fecha_vencimiento": self.date_venc.date().toString("yyyy-MM-dd"),
            "dias_alerta":       self.spin_dias_alerta.value(),
            "notas":             self.txt_notas.toPlainText().strip(),
        }
        try:
            if self.factura:
                db.actualizar_factura_proveedor(self.factura["id"], datos)
            else:
                db.crear_factura_proveedor(datos)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def resultado(self):
        return True


# ─────────────────────────────────────────────────────────────
#  Diálogo rápido de pago
# ─────────────────────────────────────────────────────────────

class DialogoPago(QDialog):
    """Registra un pago sobre una factura existente."""
    def __init__(self, factura: dict, parent=None):
        super().__init__(parent)
        self.factura = factura
        self.setWindowTitle("Registrar pago")
        self.setMinimumWidth(400)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(24, 20, 24, 20)

        lay.addWidget(QLabel(
            f"<b>Factura:</b>  {self.factura.get('numero_factura') or 'S/N'}  —  "
            f"{self.factura.get('proveedor_nombre', '')}"
        ))

        saldo = self.factura["monto_total"] - self.factura["monto_pagado"]
        lay.addWidget(QLabel(
            f"<b>Total original:</b>  $ {self.factura['monto_total']:,.2f}<br>"
            f"<b>Ya pagado:</b>  $ {self.factura['monto_pagado']:,.2f}<br>"
            f"<b style='color:#FF9800'>Saldo pendiente:  $ {saldo:,.2f}</b>"
        ))

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#444;")
        lay.addWidget(sep)

        form = QFormLayout()

        # Editar total de factura (si cambió el precio real, descuento, etc.)
        self.spin_total_nuevo = QDoubleSpinBox()
        self.spin_total_nuevo.setRange(0, 9_999_999)
        self.spin_total_nuevo.setDecimals(2)
        self.spin_total_nuevo.setSingleStep(100)
        self.spin_total_nuevo.setPrefix("$ ")
        self.spin_total_nuevo.setValue(round(self.factura["monto_total"], 2))
        self.spin_total_nuevo.setToolTip(
            "Cambiá si el total de la factura es diferente al registrado\n"
            "(ej: descuento, nota de crédito, precio acordado distinto)")
        self.spin_total_nuevo.valueChanged.connect(self._actualizar_saldo_pago)
        form.addRow("✏️ Nuevo total factura:", self.spin_total_nuevo)

        self.spin_pago = QDoubleSpinBox()
        self.spin_pago.setRange(0, 9_999_999)
        self.spin_pago.setDecimals(2)
        self.spin_pago.setSingleStep(100)
        self.spin_pago.setPrefix("$ ")
        self.spin_pago.setValue(round(saldo, 2))
        self.spin_pago.valueChanged.connect(self._actualizar_saldo_pago)
        form.addRow("Monto a pagar ahora:", self.spin_pago)

        self.lbl_saldo_resultado = QLabel()
        self.lbl_saldo_resultado.setStyleSheet("font-weight:700; font-size:11pt;")
        form.addRow("Saldo resultante:", self.lbl_saldo_resultado)
        self._actualizar_saldo_pago()  # primer render

        self.txt_notas = QLineEdit()
        self.txt_notas.setPlaceholderText("Ej: transferencia banc. / efectivo…")
        form.addRow("Nota del pago:", self.txt_notas)

        lay.addLayout(form)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("btn_secundario")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_ok = QPushButton("💳  Registrar pago")
        btn_ok.setObjectName("btn_exito")
        btn_ok.clicked.connect(self._pagar)
        btn_row.addWidget(btn_ok)
        lay.addLayout(btn_row)

    def _actualizar_saldo_pago(self):
        nuevo_total = self.spin_total_nuevo.value()
        ya_pagado   = self.factura["monto_pagado"]
        pago_ahora  = self.spin_pago.value()
        saldo_res   = round(nuevo_total - ya_pagado - pago_ahora, 2)
        if saldo_res < -0.005:
            color = "#2196F3"
            txt = f"$ {abs(saldo_res):,.2f}  💙 Saldo a favor"
        elif saldo_res < 0.005:
            color = "#4CAF50"
            txt = "✅  Pagada completamente"
        else:
            color = "#FF9800"
            txt = f"$ {saldo_res:,.2f}  pendiente"
        self.lbl_saldo_resultado.setStyleSheet(
            f"font-weight:700; font-size:11pt; color:{color};")
        self.lbl_saldo_resultado.setText(txt)

    def _pagar(self):
        nuevo_total  = round(self.spin_total_nuevo.value(), 2)
        nuevo_pagado = round(
            self.factura["monto_pagado"] + self.spin_pago.value(), 2)
        nota = self.txt_notas.text().strip()
        notas_actuales = self.factura.get("notas") or ""
        if nota:
            from datetime import date as _d
            notas_actuales = (notas_actuales + "\n" if notas_actuales else "") + \
                f"[{_d.today():%d/%m/%Y}] Pago: ${self.spin_pago.value():,.2f} — {nota}"
        update = {
            "monto_total":  nuevo_total,
            "monto_pagado": nuevo_pagado,
            "notas":        notas_actuales,
        }
        db.actualizar_factura_proveedor(self.factura["id"], update)
        self.accept()


# ─────────────────────────────────────────────────────────────
#  Widget principal: Cuentas Corrientes
# ─────────────────────────────────────────────────────────────

class CuentasProveedorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.cargar()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(16, 16, 16, 16)

        # ── Encabezado ────────────────────────────────────────
        header = QHBoxLayout()
        titulo = QLabel("🧾  Cuentas Corrientes — Proveedores")
        titulo.setObjectName("titulo_seccion")
        header.addWidget(titulo, 1)

        btn_nueva = QPushButton("➕  Nueva factura")
        btn_nueva.clicked.connect(self._nueva_factura)
        header.addWidget(btn_nueva)
        lay.addLayout(header)

        # ── Tarjetas de resumen ───────────────────────────────
        self.resumen_row = QHBoxLayout()
        lay.addLayout(self.resumen_row)

        # ── Tabs ──────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # Tab 1: Todas las facturas
        tab_todas = QWidget()
        lay_todas = QVBoxLayout(tab_todas)
        lay_todas.setSpacing(6)

        filtro_row = QHBoxLayout()
        self.cmb_filtro_estado = QComboBox()
        self.cmb_filtro_estado.addItem("Todos los estados", None)
        self.cmb_filtro_estado.addItem("⏳ Pendientes",    "pendiente")
        self.cmb_filtro_estado.addItem("🔴 Vencidas",       "vencida")
        self.cmb_filtro_estado.addItem("✅ Pagadas",         "pagada")
        self.cmb_filtro_estado.addItem("💙 Saldo a favor",  "saldo_favor")
        self.cmb_filtro_estado.addItem("📌 Por revisar",    "por_revisar")
        self.cmb_filtro_estado.currentIndexChanged.connect(self._filtrar_facturas)
        filtro_row.addWidget(QLabel("Filtrar:"))
        filtro_row.addWidget(self.cmb_filtro_estado)

        self.cmb_filtro_prov = QComboBox()
        self.cmb_filtro_prov.addItem("Todos los proveedores", None)
        for p in db.obtener_proveedores():
            self.cmb_filtro_prov.addItem(p["nombre"], p["id"])
        self.cmb_filtro_prov.currentIndexChanged.connect(self._filtrar_facturas)
        filtro_row.addWidget(self.cmb_filtro_prov)
        filtro_row.addStretch()
        lay_todas.addLayout(filtro_row)

        self.tabla_facturas = self._crear_tabla_facturas()
        lay_todas.addWidget(self.tabla_facturas, 1)
        tab_todas.setLayout(lay_todas)
        self.tabs.addTab(tab_todas, "📋  Todas las facturas")

        # Tab 2: Por vencer
        tab_vencer = QWidget()
        lay_vencer = QVBoxLayout(tab_vencer)
        lay_vencer.setSpacing(6)
        self.lbl_vencer_header = QLabel("")
        self.lbl_vencer_header.setStyleSheet(
            "color:#FF9800; font-weight:700; font-size:10pt; padding:4px 0;")
        lay_vencer.addWidget(self.lbl_vencer_header)
        self.tabla_por_vencer = self._crear_tabla_facturas()
        lay_vencer.addWidget(self.tabla_por_vencer, 1)
        tab_vencer.setLayout(lay_vencer)
        self.tabs.addTab(tab_vencer, "⏰  Por vencer")

        # Tab 3: Resumen por proveedor
        tab_resumen = QWidget()
        lay_res = QVBoxLayout(tab_resumen)
        self.tabla_resumen = QTableWidget(0, 5)
        self.tabla_resumen.setHorizontalHeaderLabels([
            "Proveedor", "Facturas", "Deuda total", "Deuda vencida", "Saldo a favor"
        ])
        self.tabla_resumen.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        for c in (1, 2, 3, 4):
            self.tabla_resumen.horizontalHeader().setSectionResizeMode(
                c, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla_resumen.setAlternatingRowColors(True)
        self.tabla_resumen.verticalHeader().setVisible(False)
        self.tabla_resumen.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        lay_res.addWidget(self.tabla_resumen, 1)
        tab_resumen.setLayout(lay_res)
        self.tabs.addTab(tab_resumen, "📊  Resumen por proveedor")

        # Tab 4: Análisis de compras
        tab_analisis = self._build_tab_analisis()
        self.tabs.addTab(tab_analisis, "📈  Análisis de compras")

        self.tabs.currentChanged.connect(self._tab_changed)
        lay.addWidget(self.tabs, 1)

    def _crear_tabla_facturas(self) -> QTableWidget:
        tabla = QTableWidget(0, 9)
        tabla.setHorizontalHeaderLabels([
            "☑", "Proveedor", "N° Factura", "Descripción",
            "Total", "Pagado", "Saldo", "Vencimiento", "Acciones"
        ])
        hdr = tabla.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)              # Revisar
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Proveedor
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)            # N° Factura
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)              # Descripción (hidden)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Total
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Pagado
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Saldo
        hdr.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Vencimiento
        hdr.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)              # Acciones
        tabla.setColumnHidden(3, True)    # Descripción oculta
        tabla.setColumnWidth(0, 36)       # Revisar
        tabla.setColumnWidth(8, 230)      # Acciones
        tabla.cellDoubleClicked.connect(
            lambda row, col, t=tabla: self._mostrar_descripcion(t, row, col))
        tabla.itemChanged.connect(self._on_revisar_changed)
        tabla.setAlternatingRowColors(True)
        tabla.verticalHeader().setVisible(False)
        tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        return tabla

    # ── Carga de datos ────────────────────────────────────────

    def cargar(self):
        self._actualizar_alertas()
        self._filtrar_facturas()
        self._cargar_resumen()
        self._rebuild_tarjetas()

    def _rebuild_tarjetas(self):
        # Limpiar tarjetas anteriores
        while self.resumen_row.count():
            item = self.resumen_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        facturas = db.obtener_facturas_proveedor()
        deuda_total   = sum(f["saldo"] for f in facturas if f["estado"] in ("pendiente", "vencida"))
        deuda_vencida = sum(f["saldo"] for f in facturas if f["estado"] == "vencida")
        saldo_favor   = sum(f["monto_pagado"] - f["monto_total"]
                           for f in facturas if f["estado"] == "saldo_favor")
        pendientes    = sum(1 for f in facturas if f["estado"] == "pendiente")
        vencidas      = sum(1 for f in facturas if f["estado"] == "vencida")

        tarjetas = [
            ("DEUDA TOTAL",     f"$ {deuda_total:,.2f}",   "#FF9800"),
            ("DEUDA VENCIDA",   f"$ {deuda_vencida:,.2f}", "#F44336"),
            ("SALDO A FAVOR",   f"$ {saldo_favor:,.2f}",   "#2196F3"),
            ("FACTURAS PEND.",  str(pendientes),            "#C9A84C"),
            ("VENCIDAS",         str(vencidas),              "#F44336"),
        ]
        for titulo, valor, color in tarjetas:
            card = QFrame()
            card.setObjectName("card_widget")
            card.setMinimumWidth(140)
            card_lay = QVBoxLayout(card)
            card_lay.setSpacing(4)
            card_lay.setContentsMargins(14, 10, 14, 10)
            lbl_t = QLabel(titulo)
            lbl_t.setObjectName("card_titulo")
            lbl_v = QLabel(valor)
            lbl_v.setStyleSheet(f"font-size:18pt; font-weight:800; color:{color};")
            card_lay.addWidget(lbl_t)
            card_lay.addWidget(lbl_v)
            self.resumen_row.addWidget(card)
        self.resumen_row.addStretch()

    def _actualizar_alertas(self):
        por_vencer = db.facturas_por_vencer()
        # Ordenar por fecha de vencimiento ascendente (más próxima primero)
        por_vencer = sorted(por_vencer, key=lambda f: str(f["fecha_vencimiento"] or ""))

        # Actualizar ícono de la tab
        idx_tab = 1
        if por_vencer:
            self.tabs.setTabText(idx_tab, f"⏰  Por vencer ({len(por_vencer)})")
        else:
            self.tabs.setTabText(idx_tab, "⏰  Por vencer")

        # Llenar tabla
        self.tabla_por_vencer.setRowCount(len(por_vencer))
        for i, f in enumerate(por_vencer):
            dias = (date.fromisoformat(str(f["fecha_vencimiento"])[:10]) - date.today()).days
            avisar_en = f["dias_alerta"] if "dias_alerta" in f.keys() else 7

            color = "#FF4444" if dias <= 1 else ("#FF9800" if dias <= 3 else "#C9A84C")

            def cell(txt, bold=False):
                it = QTableWidgetItem(txt)
                if bold:
                    it.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                it.setForeground(QColor(color))
                return it

            # Col 0: checkbox revisar (nativo)
            chk_it_v = QTableWidgetItem()
            chk_it_v.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk_it_v.setCheckState(
                Qt.CheckState.Checked
                if (f["por_revisar"] if "por_revisar" in f.keys() else 0)
                else Qt.CheckState.Unchecked)
            chk_it_v.setData(Qt.ItemDataRole.UserRole, f["id"])
            chk_it_v.setToolTip("Marcar para revisar después")
            self.tabla_por_vencer.setItem(i, 0, chk_it_v)

            self.tabla_por_vencer.setItem(i, 1, cell(f["proveedor_nombre"] or "—", bold=True))
            nro_item_v = cell(f["numero_factura"] or "S/N")
            desc_v = f["descripcion"] or ""
            nro_item_v.setData(Qt.ItemDataRole.UserRole, desc_v)
            nro_item_v.setData(Qt.ItemDataRole.UserRole + 1, dict(f))
            nro_item_v.setToolTip("Doble clic para ver detalle")
            self.tabla_por_vencer.setItem(i, 2, nro_item_v)
            self.tabla_por_vencer.setItem(i, 3, cell(desc_v))
            self.tabla_por_vencer.setItem(i, 4, cell(f"$ {f['monto_total']:,.2f}"))
            self.tabla_por_vencer.setItem(i, 5, cell(f"$ {f['monto_pagado']:,.2f}"))
            self.tabla_por_vencer.setItem(i, 6, cell(f"$ {f['saldo']:,.2f}", bold=True))
            venc_txt = f"{f['fecha_vencimiento'][:10]}  "
            if dias < 0:
                venc_txt += f"🔴 vencida hace {abs(dias)}d"
            elif dias == 0:
                venc_txt += "🔴 vence HOY"
            else:
                venc_txt += f"⏰ en {dias}d  (alerta a {avisar_en}d)"
            self.tabla_por_vencer.setItem(i, 7, cell(venc_txt, bold=(dias <= 1)))

            # Botones de acción — igual que en la tabla principal
            fdict_v = dict(f)
            acc_v = QWidget()
            acc_lay_v = QHBoxLayout(acc_v)
            acc_lay_v.setContentsMargins(6, 3, 6, 3)
            acc_lay_v.setSpacing(5)

            if f["estado"] in ("pendiente", "vencida"):
                btn_pagar_v = QPushButton("= Pagar")
                btn_pagar_v.setFixedHeight(28)
                btn_pagar_v.setStyleSheet(
                    "QPushButton{background:#2E7D32;color:white;border-radius:5px;"
                    "font-size:9pt;padding:0 10px;}"
                    "QPushButton:hover{background:#388E3C;}"
                )
                btn_pagar_v.clicked.connect(
                    lambda _, fd=fdict_v: self._pagar_factura(fd))
                acc_lay_v.addWidget(btn_pagar_v)

            btn_edit_v = QPushButton("✏ Editar")
            btn_edit_v.setFixedHeight(28)
            btn_edit_v.setStyleSheet(
                "QPushButton{background:#2C2C2C;border:1px solid #555;border-radius:5px;"
                "color:#F5F5F5;font-size:9pt;padding:0 8px;}"
                "QPushButton:hover{background:#3C3C3C;}"
            )
            btn_edit_v.clicked.connect(lambda _, fd=fdict_v: self._editar_factura(fd))
            acc_lay_v.addWidget(btn_edit_v)

            btn_del_v = QPushButton("🗑 Borrar")
            btn_del_v.setFixedHeight(28)
            btn_del_v.setStyleSheet(
                "QPushButton{background:#7F0000;color:white;border-radius:5px;"
                "font-size:9pt;padding:0 8px;}"
                "QPushButton:hover{background:#B71C1C;}"
            )
            btn_del_v.clicked.connect(lambda _, fd=fdict_v: self._eliminar_factura(fd))
            acc_lay_v.addWidget(btn_del_v)

            self.tabla_por_vencer.setCellWidget(i, 8, acc_v)
            self.tabla_por_vencer.setRowHeight(i, 42)

        n = len(por_vencer)
        if n:
            self.lbl_vencer_header.setText(
                f"{n} factura(s) próximas a vencer — ordenadas de más urgente a menos urgente")
        else:
            self.lbl_vencer_header.setText("✅  No hay facturas próximas a vencer")
            self.lbl_vencer_header.setStyleSheet(
                "color:#4CAF50; font-weight:700; font-size:10pt; padding:4px 0;")

    def _filtrar_facturas(self):
        estado     = self.cmb_filtro_estado.currentData()
        prov_id    = self.cmb_filtro_prov.currentData()
        if estado == "por_revisar":
            facturas = db.obtener_facturas_proveedor(
                proveedor_id=prov_id, por_revisar=True)
        else:
            facturas = db.obtener_facturas_proveedor(
                proveedor_id=prov_id, estado=estado)
        self._mostrar_facturas(facturas)

    def _mostrar_descripcion(self, tabla, row, col):
        if col != 2:
            return
        item = tabla.item(row, 2)
        if not item:
            return
        fdict = item.data(Qt.ItemDataRole.UserRole + 1)
        if not fdict:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Detalle de factura")
        dlg.setMinimumWidth(420)
        lay = QVBoxLayout(dlg)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 20, 20, 20)

        def _fila(etiqueta, valor, color=None, bold=False):
            row_w = QWidget()
            row_h = QHBoxLayout(row_w)
            row_h.setContentsMargins(0, 0, 0, 0)
            lbl_e = QLabel(etiqueta)
            lbl_e.setStyleSheet("color:#888;font-size:9pt;min-width:140px;")
            lbl_v = QLabel(str(valor) if valor else "—")
            style = "font-size:10pt;"
            if color:
                style += f"color:{color};"
            if bold:
                style += "font-weight:700;"
            lbl_v.setStyleSheet(style)
            row_h.addWidget(lbl_e)
            row_h.addWidget(lbl_v, 1)
            lay.addWidget(row_w)

        # Separador superior
        prov = fdict.get("proveedor_nombre") or "—"
        nro = fdict.get("numero_factura") or "S/N"
        titulo = QLabel(f"{prov}  ·  Factura {nro}")
        titulo.setStyleSheet("font-size:13pt;font-weight:700;color:#C9A84C;")
        lay.addWidget(titulo)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#444;")
        lay.addWidget(sep)

        _fila("Descripción:",       fdict.get("descripcion"))
        _fila("Fecha emisión:",     fdict.get("fecha_emision", "")[:10] if fdict.get("fecha_emision") else None)
        _fila("Fecha vencimiento:", fdict.get("fecha_vencimiento", "")[:10] if fdict.get("fecha_vencimiento") else None)
        _fila("Estado:",            (fdict.get("estado") or "").capitalize())

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color:#444;")
        lay.addWidget(sep2)

        total = fdict.get("monto_total") or 0
        pagado = fdict.get("monto_pagado") or 0
        saldo = fdict.get("saldo") or (total - pagado)
        saldo_color = "#4CAF50" if saldo <= 0 else ("#F44336" if saldo == total else "#FF9800")

        _fila("Total factura:",     f"$ {total:,.2f}")
        _fila("Monto pagado:",      f"$ {pagado:,.2f}", color="#4CAF50")
        _fila("Saldo pendiente:",   f"$ {saldo:,.2f}", color=saldo_color, bold=True)

        lay.addSpacing(8)
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setFixedHeight(34)
        btn_cerrar.setStyleSheet(
            "QPushButton{background:#2C2C2C;border:1px solid #555;border-radius:6px;"
            "color:#F5F5F5;font-size:10pt;padding:0 20px;}"
            "QPushButton:hover{background:#3C3C3C;}"
        )
        btn_cerrar.clicked.connect(dlg.accept)
        lay.addWidget(btn_cerrar, alignment=Qt.AlignmentFlag.AlignRight)
        dlg.exec()

    def _mostrar_facturas(self, facturas: list):
        self.tabla_facturas.setRowCount(len(facturas))
        hoy = date.today()
        for i, f in enumerate(facturas):
            # Col 0: checkbox "por revisar" (nativo)
            chk_it = QTableWidgetItem()
            chk_it.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk_it.setCheckState(
                Qt.CheckState.Checked if f["por_revisar"] else Qt.CheckState.Unchecked)
            chk_it.setData(Qt.ItemDataRole.UserRole, f["id"])
            chk_it.setToolTip("Marcar para revisar después")
            self.tabla_facturas.setItem(i, 0, chk_it)

            self.tabla_facturas.setItem(i, 1, QTableWidgetItem(
                f["proveedor_nombre"] or "Sin proveedor"))
            nro_item = QTableWidgetItem(f["numero_factura"] or "—")
            desc = f["descripcion"] or ""
            nro_item.setData(Qt.ItemDataRole.UserRole, desc)
            nro_item.setData(Qt.ItemDataRole.UserRole + 1, dict(f))
            nro_item.setToolTip("Doble clic para ver detalle")
            self.tabla_facturas.setItem(i, 2, nro_item)
            self.tabla_facturas.setItem(i, 3, QTableWidgetItem(desc))

            def _c(val, color=None, bold=False):
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if color:
                    it.setForeground(QColor(color))
                if bold:
                    font = QFont()
                    font.setBold(True)
                    it.setFont(font)
                return it

            self.tabla_facturas.setItem(i, 4, _c(f"$ {f['monto_total']:,.2f}"))
            self.tabla_facturas.setItem(i, 5, _c(f"$ {f['monto_pagado']:,.2f}", "#4CAF50"))

            saldo = f["saldo"]
            saldo_color = (ESTADO_COLOR.get(f["estado"], "#FFFFFF")
                           if f["estado"] != "pagada" else "#4CAF50")
            self.tabla_facturas.setItem(i, 6, _c(f"$ {saldo:,.2f}", saldo_color, bold=True))

            # Vencimiento con días restantes
            try:
                fv = date.fromisoformat(str(f["fecha_vencimiento"])[:10])
                dias = (fv - hoy).days
                if f["estado"] in ("pendiente", "vencida"):
                    if dias < 0:
                        venc_txt = f"{fv:%d/%m/%Y}  ⚠️ ({abs(dias)}d vencida)"
                        venc_color = "#F44336"
                    elif dias <= 7:
                        venc_txt = f"{fv:%d/%m/%Y}  ⏰ ({dias}d)"
                        venc_color = "#FF9800"
                    else:
                        venc_txt = f"{fv:%d/%m/%Y}  ({dias}d)"
                        venc_color = "#AAAAAA"
                else:
                    venc_txt  = f"{fv:%d/%m/%Y}"
                    venc_color = "#666"
            except Exception:
                venc_txt, venc_color = str(f["fecha_vencimiento"]), "#AAAAAA"

            self.tabla_facturas.setItem(i, 7, _c(venc_txt, venc_color))

            # ── Botones de acción ─────────────────────────────
            acc = QWidget()
            acc_lay = QHBoxLayout(acc)
            acc_lay.setContentsMargins(6, 3, 6, 3)
            acc_lay.setSpacing(5)

            fdict = dict(f)

            if f["estado"] in ("pendiente", "vencida"):
                btn_pagar = QPushButton("= Pagar")
                btn_pagar.setFixedHeight(28)
                btn_pagar.setStyleSheet(
                    "QPushButton{background:#2E7D32;color:white;border-radius:5px;"
                    "font-size:9pt;padding:0 10px;}"
                    "QPushButton:hover{background:#388E3C;}"
                )
                btn_pagar.clicked.connect(
                    lambda _, fd=fdict: self._pagar_factura(fd))
                acc_lay.addWidget(btn_pagar)

            btn_edit = QPushButton("✏ Editar")
            btn_edit.setFixedHeight(28)
            btn_edit.setStyleSheet(
                "QPushButton{background:#2C2C2C;border:1px solid #555;border-radius:5px;"
                "color:#F5F5F5;font-size:9pt;padding:0 8px;}"
                "QPushButton:hover{background:#3C3C3C;}"
            )
            btn_edit.clicked.connect(lambda _, fd=fdict: self._editar_factura(fd))
            acc_lay.addWidget(btn_edit)

            btn_del = QPushButton("🗑 Borrar")
            btn_del.setFixedHeight(28)
            btn_del.setStyleSheet(
                "QPushButton{background:#7F0000;color:white;border-radius:5px;"
                "font-size:9pt;padding:0 8px;}"
                "QPushButton:hover{background:#B71C1C;}"
            )
            btn_del.clicked.connect(lambda _, fd=fdict: self._eliminar_factura(fd))
            acc_lay.addWidget(btn_del)

            self.tabla_facturas.setCellWidget(i, 8, acc)
            self.tabla_facturas.setRowHeight(i, 42)

    def _cargar_resumen(self):
        provs = db.resumen_deuda_proveedores()
        self.tabla_resumen.setRowCount(len(provs))
        for i, p in enumerate(provs):
            self.tabla_resumen.setItem(i, 0, QTableWidgetItem(p["proveedor_nombre"]))

            def _c(val, color=None, bold=False):
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if color:
                    it.setForeground(QColor(color))
                if bold:
                    ft = QFont(); ft.setBold(True); it.setFont(ft)
                return it

            self.tabla_resumen.setItem(i, 1, _c(p["total_facturas"]))
            deuda = p["deuda_total"] or 0
            self.tabla_resumen.setItem(i, 2, _c(
                f"$ {deuda:,.2f}", "#FF9800" if deuda > 0 else "#4CAF50", bold=deuda > 0))
            dvenc = p["deuda_vencida"] or 0
            self.tabla_resumen.setItem(i, 3, _c(
                f"$ {dvenc:,.2f}", "#F44336" if dvenc > 0 else "#666"))
            sfavor = p["saldo_favor"] or 0
            self.tabla_resumen.setItem(i, 4, _c(
                f"$ {sfavor:,.2f}", "#2196F3" if sfavor > 0 else "#666"))
            self.tabla_resumen.setRowHeight(i, 38)

    def _tab_changed(self, idx):
        if idx == 1:
            self._actualizar_alertas()
        elif idx == 2:
            self._cargar_resumen()
        elif idx == 3:
            self._cargar_analisis()

    def _build_tab_analisis(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)
        lay.setContentsMargins(12, 12, 12, 12)

        # ── Controles de filtro ──
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Desde:"))
        self.an_date_desde = QDateEdit(QDate.currentDate().addMonths(-6))
        self.an_date_desde.setCalendarPopup(True)
        self.an_date_desde.setDisplayFormat("dd/MM/yyyy")
        ctrl.addWidget(self.an_date_desde)
        ctrl.addWidget(QLabel("Hasta:"))
        self.an_date_hasta = QDateEdit(QDate.currentDate())
        self.an_date_hasta.setCalendarPopup(True)
        self.an_date_hasta.setDisplayFormat("dd/MM/yyyy")
        ctrl.addWidget(self.an_date_hasta)
        ctrl.addWidget(QLabel("Proveedor:"))
        self.an_cmb_prov = QComboBox()
        self.an_cmb_prov.addItem("Todos los proveedores", None)
        for p in db.obtener_proveedores():
            self.an_cmb_prov.addItem(p["nombre"], p["id"])
        ctrl.addWidget(self.an_cmb_prov)
        btn_ver = QPushButton("📊  Ver")
        btn_ver.setStyleSheet(
            "QPushButton{background:#722F37;color:white;font-weight:700;"
            "border-radius:6px;padding:6px 16px;}"
            "QPushButton:hover{background:#8B3A44;}")
        btn_ver.clicked.connect(self._cargar_analisis)
        ctrl.addWidget(btn_ver)
        ctrl.addStretch()
        lay.addLayout(ctrl)

        # ── Tarjetas de resumen ──
        self.an_cards_row = QHBoxLayout()
        self._an_lbl_compras  = self._an_card("COMPRAS TOTALES",  "$ 0",       "#FF9800")
        self._an_lbl_ventas   = self._an_card("VENTAS PERÍODO",   "$ 0",       "#4CAF50")
        self._an_lbl_ganancia = self._an_card("GANANCIA ESTIMADA","$ 0",       "#C9A84C")
        self._an_lbl_margen   = self._an_card("MARGEN BRUTO",     "0 %",       "#2196F3")
        lay.addLayout(self.an_cards_row)

        # ── Splitter: tabla + gráfico ──
        split = QHBoxLayout()

        # Tabla por proveedor
        self.an_tabla = QTableWidget(0, 4)
        self.an_tabla.setHorizontalHeaderLabels(
            ["Proveedor", "Compras", "Facturas", "Deuda pendiente"])
        self.an_tabla.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        for c in (1, 2, 3):
            self.an_tabla.horizontalHeader().setSectionResizeMode(
                c, QHeaderView.ResizeMode.ResizeToContents)
        self.an_tabla.setAlternatingRowColors(True)
        self.an_tabla.verticalHeader().setVisible(False)
        self.an_tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        split.addWidget(self.an_tabla)

        # Canvas gráfico línea de tiempo
        if HAS_MATPLOTLIB:
            self.an_canvas = _GraficoMini(width=6, height=3.5)
            split.addWidget(self.an_canvas, 1)
        else:
            split.addWidget(QLabel("Instalá matplotlib para ver el gráfico"), 1)

        lay.addLayout(split, 1)
        return w

    def _an_card(self, titulo: str, valor: str, color: str) -> QLabel:
        card = QFrame()
        card.setObjectName("card_widget")
        card.setMinimumWidth(160)
        cl = QVBoxLayout(card)
        cl.setSpacing(4)
        cl.setContentsMargins(14, 10, 14, 10)
        lbl_t = QLabel(titulo)
        lbl_t.setObjectName("card_titulo")
        lbl_v = QLabel(valor)
        lbl_v.setStyleSheet(f"font-size:17pt;font-weight:800;color:{color};")
        cl.addWidget(lbl_t)
        cl.addWidget(lbl_v)
        self.an_cards_row.addWidget(card)
        self.an_cards_row.addStretch()
        return lbl_v

    def _cargar_analisis(self):
        desde     = self.an_date_desde.date().toString("yyyy-MM-dd")
        hasta     = self.an_date_hasta.date().toString("yyyy-MM-dd")
        prov_id   = self.an_cmb_prov.currentData()
        datos     = db.compras_por_periodo(desde, hasta, prov_id)

        por_prov  = datos["por_proveedor"]
        por_mes   = datos["por_mes"]
        ventas_r  = datos["ventas"]
        ventas_mes = datos["ventas_mes"]

        compras_total = sum(r["compras_total"] or 0 for r in por_prov)
        ventas_total  = ventas_r["ventas_total"] or 0 if ventas_r else 0
        ganancia      = ventas_total - compras_total
        margen        = (ganancia / ventas_total * 100) if ventas_total > 0 else 0

        gcolor = "#4CAF50" if ganancia >= 0 else "#F44336"
        self._an_lbl_compras.setText(f"$ {compras_total:,.0f}")
        self._an_lbl_ventas.setText(f"$ {ventas_total:,.0f}")
        self._an_lbl_ganancia.setStyleSheet(
            f"font-size:17pt;font-weight:800;color:{gcolor};")
        self._an_lbl_ganancia.setText(f"$ {ganancia:,.0f}")
        self._an_lbl_margen.setText(f"{margen:.1f} %")

        # Tabla por proveedor
        self.an_tabla.setRowCount(len(por_prov))
        for i, p in enumerate(por_prov):
            self.an_tabla.setItem(i, 0, QTableWidgetItem(p["proveedor_nombre"] or "Sin nombre"))
            it_c = QTableWidgetItem(f"$ {p['compras_total'] or 0:,.2f}")
            it_c.setForeground(QColor("#FF9800"))
            it_c.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.an_tabla.setItem(i, 1, it_c)
            it_f = QTableWidgetItem(str(p["total_facturas"] or 0))
            it_f.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.an_tabla.setItem(i, 2, it_f)
            deuda = p["deuda_total"] or 0
            it_d = QTableWidgetItem(f"$ {deuda:,.2f}")
            it_d.setForeground(QColor("#F44336" if deuda > 0 else "#4CAF50"))
            it_d.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.an_tabla.setItem(i, 3, it_d)
            self.an_tabla.setRowHeight(i, 36)

        # Gráfico
        if not HAS_MATPLOTLIB:
            return

        # Meses únicos ordenados
        todos_meses = sorted(set(
            [r["mes"] for r in por_mes] + [r["mes"] for r in ventas_mes]))
        if not todos_meses:
            self.an_canvas.fig.clear()
            self.an_canvas.draw()
            return

        # Totales de compras por mes (suma de todos los proveedores)
        compras_vals = np.array([
            sum(r["compras_total"] or 0 for r in por_mes if r["mes"] == m)
            for m in todos_meses], dtype=float)
        ventas_vals = np.array(
            [next((r["ventas_total"] or 0 for r in ventas_mes if r["mes"] == m), 0)
             for m in todos_meses], dtype=float)

        # Etiquetas de mes legibles (abrev): "2026-04" → "Abr 26"
        MESES = ["Ene","Feb","Mar","Abr","May","Jun",
                 "Jul","Ago","Sep","Oct","Nov","Dic"]
        def fmt_mes(m):
            try:
                y, mo = m.split("-")
                return f"{MESES[int(mo)-1]} {y[2:]}"
            except Exception:
                return m
        etiquetas = [fmt_mes(m) for m in todos_meses]

        self.an_canvas.fig.clear()
        ax = self.an_canvas.fig.add_subplot(111)
        ax.set_facecolor("#1A1A1A")
        self.an_canvas.fig.patch.set_facecolor("#1A1A1A")

        xs = np.arange(len(todos_meses))
        w = 0.35

        bars_c = ax.bar(xs - w/2, compras_vals, w,
                        color="#FF6B35", alpha=0.9, label="🟠 Compras")
        bars_v = ax.bar(xs + w/2, ventas_vals,  w,
                        color="#4CAF50", alpha=0.9, label="🟢 Ventas")

        # Etiquetas $ encima de cada barra
        max_val = max(np.max(compras_vals), np.max(ventas_vals)) if len(todos_meses) else 1
        for bar in list(bars_c) + list(bars_v):
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h + max_val * 0.01,
                        f"${h:,.0f}", ha="center", va="bottom",
                        color="#DDDDDD", fontsize=7, fontweight="bold")

        ax.set_xticks(xs)
        ax.set_xticklabels(etiquetas, color="#BBBBBB", fontsize=9)
        ax.tick_params(axis="y", colors="#888888")
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
        ax.set_ylim(0, max_val * 1.2 if max_val > 0 else 1)
        ax.set_title("Compras vs. Ventas por mes",
                     color="#F5F5F5", fontsize=11, fontweight="bold", pad=10)
        ax.spines[:].set_color("#333")
        ax.set_axisbelow(True)
        ax.yaxis.grid(True, color="#2E2E2E", linewidth=0.7)

        ax.legend(loc="upper left", fontsize=9, facecolor="#2A2A2A",
                  edgecolor="#444", labelcolor="#F5F5F5", framealpha=0.9)

        self.an_canvas.fig.tight_layout()
        self.an_canvas.draw()

    def _on_revisar_changed(self, item: QTableWidgetItem):
        """Guardado automático al tildar/destildar el checkbox de revisar."""
        if item.column() != 0:
            return
        factura_id = item.data(Qt.ItemDataRole.UserRole)
        if factura_id is not None:
            db.actualizar_factura_proveedor(
                factura_id,
                {"por_revisar": 1 if item.checkState() == Qt.CheckState.Checked else 0})

    def _toggle_revisar(self, factura_id: int, state: int):
        """Guarda el estado de 'por revisar' en la DB sin recargar toda la tabla."""
        db.actualizar_factura_proveedor(factura_id, {"por_revisar": 1 if state else 0})

    # ── Acciones ──────────────────────────────────────────────

    def _nueva_factura(self):
        dlg = DialogoFactura(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.cargar()

    def _editar_factura(self, factura: dict):
        dlg = DialogoFactura(self, factura=factura)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.cargar()

    def _pagar_factura(self, factura: dict):
        dlg = DialogoPago(factura, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.cargar()

    def _eliminar_factura(self, factura: dict):
        resp = QMessageBox.question(
            self, "Eliminar factura",
            f"¿Eliminás la factura {factura.get('numero_factura') or 'S/N'} "
            f"de {factura.get('proveedor_nombre', '')}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            db.eliminar_factura_proveedor(factura["id"])
            self.cargar()
