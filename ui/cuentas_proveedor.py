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
            f"<b>Total factura:</b>  $ {self.factura['monto_total']:,.2f}<br>"
            f"<b>Ya pagado:</b>  $ {self.factura['monto_pagado']:,.2f}<br>"
            f"<b style='color:#FF9800'>Saldo pendiente:  $ {saldo:,.2f}</b>"
        ))

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#444;")
        lay.addWidget(sep)

        form = QFormLayout()

        self.spin_pago = QDoubleSpinBox()
        self.spin_pago.setRange(0, 9_999_999)
        self.spin_pago.setDecimals(2)
        self.spin_pago.setSingleStep(100)
        self.spin_pago.setPrefix("$ ")
        self.spin_pago.setValue(round(saldo, 2))
        form.addRow("Monto a pagar ahora:", self.spin_pago)

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

    def _pagar(self):
        nuevo_pagado = round(
            self.factura["monto_pagado"] + self.spin_pago.value(), 2)
        nota = self.txt_notas.text().strip()
        notas_actuales = self.factura.get("notas") or ""
        if nota:
            from datetime import date as _d
            notas_actuales = (notas_actuales + "\n" if notas_actuales else "") + \
                f"[{_d.today():%d/%m/%Y}] Pago: ${self.spin_pago.value():,.2f} — {nota}"
        db.actualizar_factura_proveedor(self.factura["id"], {
            "monto_pagado": nuevo_pagado,
            "notas": notas_actuales,
        })
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

        # ── Alertas de vencimiento ────────────────────────────
        self.lbl_alerta = QLabel("")
        self.lbl_alerta.setWordWrap(True)
        self.lbl_alerta.setStyleSheet(
            "color:#F44336; font-weight:700; font-size:11pt; "
            "background:#2A0000; border-radius:6px; padding:8px 12px;"
        )
        self.lbl_alerta.setVisible(False)
        lay.addWidget(self.lbl_alerta)

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

        # Tab 2: Resumen por proveedor
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

        # Tab 3: Análisis de compras
        tab_analisis = self._build_tab_analisis()
        self.tabs.addTab(tab_analisis, "📈  Análisis de compras")

        self.tabs.currentChanged.connect(self._tab_changed)
        lay.addWidget(self.tabs, 1)

    def _crear_tabla_facturas(self) -> QTableWidget:
        tabla = QTableWidget(0, 8)
        tabla.setHorizontalHeaderLabels([
            "Proveedor", "N° Factura", "Descripción",
            "Total", "Pagado", "Saldo", "Vencimiento", "Acciones"
        ])
        tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        tabla.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        tabla.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        tabla.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        tabla.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        tabla.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
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
        if por_vencer:
            msgs = []
            for f in por_vencer[:5]:
                dias = (date.fromisoformat(str(f["fecha_vencimiento"])[:10]) - date.today()).days
                avisar_en = f["dias_alerta"] if "dias_alerta" in f.keys() else 7
                msgs.append(
                    f"• {f['proveedor_nombre'] or 'Proveedor'} — "
                    f"Factura {f['numero_factura'] or 'S/N'} — "
                    f"Saldo $ {f['saldo']:,.2f} — "
                    f"Vence en {dias} día(s)  [⏰ alerta a {avisar_en}d]"
                )
            self.lbl_alerta.setText(
                "⚠️  FACTURAS POR VENCER:\n" + "\n".join(msgs))
            self.lbl_alerta.setVisible(True)
        else:
            self.lbl_alerta.setVisible(False)

    def _filtrar_facturas(self):
        estado     = self.cmb_filtro_estado.currentData()
        prov_id    = self.cmb_filtro_prov.currentData()
        facturas   = db.obtener_facturas_proveedor(
            proveedor_id=prov_id, estado=estado)
        self._mostrar_facturas(facturas)

    def _mostrar_facturas(self, facturas: list):
        self.tabla_facturas.setRowCount(len(facturas))
        hoy = date.today()
        for i, f in enumerate(facturas):
            self.tabla_facturas.setItem(i, 0, QTableWidgetItem(
                f["proveedor_nombre"] or "Sin proveedor"))
            self.tabla_facturas.setItem(i, 1, QTableWidgetItem(
                f["numero_factura"] or "—"))
            self.tabla_facturas.setItem(i, 2, QTableWidgetItem(
                f["descripcion"] or ""))

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

            self.tabla_facturas.setItem(i, 3, _c(f"$ {f['monto_total']:,.2f}"))
            self.tabla_facturas.setItem(i, 4, _c(f"$ {f['monto_pagado']:,.2f}", "#4CAF50"))

            saldo = f["saldo"]
            saldo_color = (ESTADO_COLOR.get(f["estado"], "#FFFFFF")
                           if f["estado"] != "pagada" else "#4CAF50")
            self.tabla_facturas.setItem(i, 5, _c(f"$ {saldo:,.2f}", saldo_color, bold=True))

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

            self.tabla_facturas.setItem(i, 6, _c(venc_txt, venc_color))

            # ── Botones de acción ─────────────────────────────
            acc = QWidget()
            acc_lay = QHBoxLayout(acc)
            acc_lay.setContentsMargins(4, 2, 4, 2)
            acc_lay.setSpacing(4)

            fdict = dict(f)

            if f["estado"] in ("pendiente", "vencida"):
                btn_pagar = QPushButton("💳 Pagar")
                btn_pagar.setFixedHeight(30)
                btn_pagar.setStyleSheet(
                    "QPushButton{background:#2E7D32;color:white;border-radius:4px;"
                    "font-size:10pt;padding:0 8px;}"
                    "QPushButton:hover{background:#388E3C;}"
                )
                btn_pagar.clicked.connect(
                    lambda _, fd=fdict: self._pagar_factura(fd))
                acc_lay.addWidget(btn_pagar)

            btn_edit = QPushButton("✏️")
            btn_edit.setFixedSize(30, 30)
            btn_edit.setStyleSheet(
                "QPushButton{background:#2C2C2C;border:1px solid #555;border-radius:4px;}"
                "QPushButton:hover{background:#3C3C3C;}"
            )
            btn_edit.clicked.connect(lambda _, fd=fdict: self._editar_factura(fd))
            acc_lay.addWidget(btn_edit)

            btn_del = QPushButton("🗑")
            btn_del.setFixedSize(30, 30)
            btn_del.setStyleSheet(
                "QPushButton{background:#B71C1C;color:white;border-radius:4px;}"
                "QPushButton:hover{background:#C62828;}"
            )
            btn_del.clicked.connect(lambda _, fd=fdict: self._eliminar_factura(fd))
            acc_lay.addWidget(btn_del)

            self.tabla_facturas.setCellWidget(i, 7, acc)
            self.tabla_facturas.setRowHeight(i, 44)

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
            self._cargar_resumen()
        elif idx == 2:
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
        self.an_tabla.setMaximumWidth(420)
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

        # Construir meses completos del rango
        todos_meses = sorted(set(
            [r["mes"] for r in por_mes] + [r["mes"] for r in ventas_mes]))
        if not todos_meses:
            return

        # Compras por proveedor por mes (para barras apiladas)
        proveedores = list({r["proveedor_nombre"] or "Sin nombre" for r in por_mes})
        colores_prov = ["#FF9800", "#E91E63", "#9C27B0", "#3F51B5",
                        "#00BCD4", "#8BC34A", "#FF5722", "#607D8B"]

        self.an_canvas.fig.clear()
        ax = self.an_canvas.fig.add_subplot(111)
        ax.set_facecolor("#1A1A1A")
        self.an_canvas.fig.patch.set_facecolor("#1A1A1A")

        xs = np.arange(len(todos_meses))
        bottoms = np.zeros(len(todos_meses))

        for idx_p, (prov, color) in enumerate(zip(proveedores, colores_prov)):
            vals = []
            for mes in todos_meses:
                row = next((r for r in por_mes
                            if r["mes"] == mes and (r["proveedor_nombre"] or "Sin nombre") == prov), None)
                vals.append(row["compras_total"] if row else 0)
            vals = np.array(vals, dtype=float)
            ax.bar(xs, vals, 0.55, bottom=bottoms,
                   color=color, alpha=0.88, label=prov)
            bottoms += vals

        # Línea de ventas superpuesta
        ventas_vals = np.array(
            [next((r["ventas_total"] for r in ventas_mes if r["mes"] == m), 0)
             for m in todos_meses], dtype=float)
        ax2 = ax.twinx()
        ax2.plot(xs, ventas_vals, color="#4CAF50", linewidth=2,
                 marker="o", markersize=5, label="Ventas", zorder=5)
        ax2.tick_params(axis="y", colors="#4CAF50")
        ax2.set_ylabel("Ventas ($)", color="#4CAF50", fontsize=8)
        ax2.spines[:].set_color("#333")

        ax.set_xticks(xs)
        ax.set_xticklabels(todos_meses, rotation=45, color="#AAAAAA", fontsize=8)
        ax.tick_params(axis="y", colors="#AAAAAA")
        ax.set_ylabel("Compras ($)", color="#AAAAAA", fontsize=8)
        ax.set_title("Compras por proveedor vs. Ventas — por mes",
                     color="#F5F5F5", fontsize=10)
        ax.spines[:].set_color("#333")

        # Leyenda combinada
        handles1, labels1 = ax.get_legend_handles_labels()
        handles2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(handles1 + handles2, labels1 + labels2,
                  loc="upper left", fontsize=7, facecolor="#2A2A2A",
                  edgecolor="#444", labelcolor="#F5F5F5", framealpha=0.85,
                  ncol=min(len(proveedores) + 1, 4))

        self.an_canvas.fig.tight_layout()
        self.an_canvas.draw()

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
