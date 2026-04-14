# ─────────────────────────────────────────────────────────────
#  ui/reportes.py  –  Reportes y métricas
# ─────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QTabWidget, QDateEdit, QMessageBox, QSizePolicy, QFrame,
    QScrollArea, QGridLayout, QAbstractItemView, QDialog,
    QSpinBox, QDoubleSpinBox, QLineEdit, QDialogButtonBox, QFormLayout,
    QCheckBox
)
from PyQt6.QtCore import Qt, QDate, QTimer
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
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# ─────────────────────────────────────────────────────────────
#  Canvas de gráfico reutilizable
# ─────────────────────────────────────────────────────────────

class GraficoCanvas(FigureCanvas if HAS_MATPLOTLIB else QWidget):
    def __init__(self, parent=None, width=6, height=4):
        if HAS_MATPLOTLIB:
            self.fig = Figure(figsize=(width, height), facecolor="#1E1E1E")
            super().__init__(self.fig)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        else:
            super().__init__(parent)

    def limpiar(self):
        if HAS_MATPLOTLIB:
            self.fig.clear()
            self.draw()


# ─────────────────────────────────────────────────────────────
#  Tarjeta de métrica
# ─────────────────────────────────────────────────────────────

class TarjetaMetrica(QFrame):
    # Explicaciones por clave (titulo, icono, descrip, formula)
    EXPLICACIONES = {
        "ingresos": (
            "Ingresos totales",
            "💰",
            "Es el dinero total que entró por todas las ventas del período. "
            "Incluye todo lo cobrado: efectivo, débito, crédito, transferencia y QR.",
            "Suma de todos los totales de ventas del período",
        ),
        "costo": (
            "Costo de lo vendido",
            "📦",
            "Es cuanto te cost\u00f3 a vos lo que vendiste. Se calcula usando el precio de costo "
            "cargado en cada producto. No incluye gastos fijos como alquiler o sueldos.",
            "Suma de (precio costo \u00d7 cantidad) de cada producto vendido",
        ),
        "margen_bruto": (
            "Margen bruto",
            "📈",
            "Es lo que te queda despu\u00e9s de restarle a los ingresos el costo de los productos. "
            "Es una ganancia \u2018antes de gastos\u2019: todav\u00eda no descont\u00f3 alquiler, servicios, sueldos, etc.",
            "Ingresos \u2212 Costo de lo vendido",
        ),
        "gastos": (
            "Gastos operativos",
            "💸",
            "Son los gastos fijos o variables del negocio que registraste manualmente en este per\u00edodo: "
            "alquiler, servicios, sueldos, transporte, etc. Se cargan desde el bot\u00f3n \u2018Registrar gasto\u2019.",
            "Suma de todos los gastos registrados en el per\u00edodo",
        ),
        "margen_neto": (
            "Margen neto",
            "✨",
            "Es la ganancia real del período: lo que te quedó en el bolsillo después de pagar productos "
            "y todos los gastos del negocio. Si es negativo, el negocio tuvo pérdida en ese período.",
            "Margen bruto − Gastos operativos",
        ),
        "stock_costo": (
            "Stock al costo",
            "📦",
            "Es cuánto vale hoy todo el inventario que tenés en stock, calculado al precio que "
            "pagaste por cada producto. Te dice cuánta plata tenés inmovilizada en mercadería.",
            "Suma de (precio_costo × stock_actual) de todos los productos activos con stock > 0",
        ),
        "stock_venta": (
            "Stock a precio de venta",
            "🏷️",
            "Es cuánto podrías facturar si vendieras todo el stock que tenés hoy, "
            "al precio de venta actual. Sirve para estimar el potencial de ingresos del inventario.",
            "Suma de (precio_venta × stock_actual) de todos los productos activos con stock > 0",
        ),
        "sueldo_total": (
            "Pozo a repartir",
            "💵",
            "Es el monto total disponible para repartir entre las personas que trabajan en el negocio. "
            "Si el checkbox 'Descontar gastos' está activo, se descuentan los gastos operativos primero. "
            "Si no está activo, se toma directo el margen bruto (ganancia antes de gastos).",
            "Con gastos: Margen neto  |  Sin gastos: Margen bruto",
        ),
        "sueldo_individual": (
            "Sueldo por persona",
            "👥",
            "Es lo que le corresponde a cada una de las 2 personas que trabajan, "
            "dividiendo el pozo a repartir en partes iguales.",
            "Pozo a repartir ÷ 2 personas",
        ),
    }

    def __init__(self, titulo: str, valor: str, subtitulo: str = "", color: str = "#722F37", key: str = ""):
        super().__init__()
        self.setObjectName("card_widget")
        self.setMinimumSize(160, 100)
        self.setMaximumHeight(130)
        self._key = key
        self._raw_valor = valor
        self.titulo_color = color

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(4)

        lbl_tit = QLabel(titulo)
        lbl_tit.setObjectName("card_titulo")

        lbl_val = QLabel(valor)
        lbl_val.setObjectName("card_valor")
        lbl_val.setStyleSheet(f"color: {color}; font-size: 22pt; font-weight: 800;")

        lbl_sub = QLabel(subtitulo)
        lbl_sub.setObjectName("card_subtitulo")

        lay.addWidget(lbl_tit)
        lay.addWidget(lbl_val)
        lay.addWidget(lbl_sub)

        # Hint doble click — solo si la card tiene explicación disponible
        if key and key in self.EXPLICACIONES:
            lbl_hint = QLabel("doble clic para explicación")
            lbl_hint.setStyleSheet("color:#555; font-size:7pt; font-style:italic;")
            lay.addWidget(lbl_hint)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip("Doble clic para ver qué significa esta métrica")

        lay.addStretch()

        self.lbl_val = lbl_val
        self.lbl_sub = lbl_sub

    def actualizar(self, valor: str, subtitulo: str = ""):
        self._raw_valor = valor
        self.lbl_val.setText(valor)
        if subtitulo:
            self.lbl_sub.setText(subtitulo)

    def mouseDoubleClickEvent(self, event):
        info = self.EXPLICACIONES.get(self._key)
        if not info:
            return
        titulo, icono, descrip, formula = info
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
        dlg = QDialog(self.window())
        dlg.setWindowTitle(f"{icono}  {titulo}")
        dlg.setMinimumWidth(420)
        dlg_lay = QVBoxLayout(dlg)
        dlg_lay.setSpacing(12)
        dlg_lay.setContentsMargins(24, 20, 24, 20)

        lbl_icon = QLabel(f"{icono}")
        lbl_icon.setStyleSheet("font-size:36pt;")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dlg_lay.addWidget(lbl_icon)

        lbl_tit = QLabel(titulo)
        lbl_tit.setStyleSheet("font-size:15pt; font-weight:800; color:#C9A84C;")
        lbl_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dlg_lay.addWidget(lbl_tit)

        lbl_val = QLabel(self._raw_valor)
        lbl_val.setStyleSheet(
            f"font-size:26pt; font-weight:900; color:{self.titulo_color}; "
            "background:#1A1A1A; border-radius:8px; padding:10px 0;")
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dlg_lay.addWidget(lbl_val)

        from PyQt6.QtWidgets import QFrame
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#333;")
        dlg_lay.addWidget(sep)

        lbl_que = QLabel("¿Qué es?")
        lbl_que.setStyleSheet("font-weight:700; color:#AAAAAA; font-size:10pt;")
        dlg_lay.addWidget(lbl_que)

        lbl_desc = QLabel(descrip)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color:#E0E0E0; font-size:10pt; line-height:150%;")
        dlg_lay.addWidget(lbl_desc)

        lbl_como = QLabel("¿Cómo se calcula?")
        lbl_como.setStyleSheet("font-weight:700; color:#AAAAAA; font-size:10pt; margin-top:6px;")
        dlg_lay.addWidget(lbl_como)

        lbl_form = QLabel(formula)
        lbl_form.setStyleSheet(
            "color:#C9A84C; font-size:10pt; font-style:italic; "
            "background:#1A1A1A; border-radius:6px; padding:6px 12px;")
        lbl_form.setWordWrap(True)
        dlg_lay.addWidget(lbl_form)

        btn_ok = QPushButton("Entendido")
        btn_ok.clicked.connect(dlg.accept)
        btn_ok.setFixedWidth(120)
        dlg_lay.addWidget(btn_ok, alignment=Qt.AlignmentFlag.AlignCenter)

        dlg.exec()


# ─────────────────────────────────────────────────────────────
#  Widget principal de Reportes
# ─────────────────────────────────────────────────────────────

class ReportesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._actualizar_resumen_hoy()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(16, 16, 16, 16)

        # Título
        header = QHBoxLayout()
        titulo = QLabel("📊  Reportes y Métricas")
        titulo.setObjectName("titulo_seccion")
        header.addWidget(titulo)
        header.addStretch()

        btn_exportar = QPushButton("📤  Exportar a Excel")
        btn_exportar.clicked.connect(self._exportar_excel)
        header.addWidget(btn_exportar)
        lay.addLayout(header)

        # Tabs
        tabs = QTabWidget()

        # ── Tab: Resumen del día ────────────────────────────
        tabs.addTab(self._build_tab_hoy(), "📅  Hoy")

        # ── Tab: Período personalizado ──────────────────────
        tabs.addTab(self._build_tab_periodo(), "📆  Por período")

        # ── Tab: Productos más vendidos ─────────────────────
        tabs.addTab(self._build_tab_top_productos(), "🏆  Top Productos")

        # ── Tab: Ingresos mensuales ─────────────────────────
        tabs.addTab(self._build_tab_mensuales(), "📈  Mensual / Anual")

        # ── Tab: Finanzas / KPIs ────────────────────────────
        tabs.addTab(self._build_tab_finanzas(), "💰  Finanzas")

        # ── Tab: Ventas detalladas ──────────────────────────
        tabs.addTab(self._build_tab_historial_ventas(), "🧾  Historial de Ventas")

        tabs.currentChanged.connect(self._tab_changed)
        lay.addWidget(tabs, 1)
        self.tabs = tabs

    # ── Tab: HOY ──────────────────────────────────────────────

    def _build_tab_hoy(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        # Tarjetas de métricas — fila única, tamaño compacto para que entren las 8
        self.cards_hoy = {}
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(4)
        for key, titulo, val, color in [
            ("total_dia",    "Total del día",    "$0", "#C9A84C"),
            ("ventas_dia",   "Ventas realizadas","0",  "#4CAF50"),
            ("ticket_prom",  "Ticket promedio",  "$0", "#2196F3"),
            ("efectivo",     "💵 Efectivo",       "$0", "#4CAF50"),
            ("debito",       "💳 Débito",         "$0", "#1565C0"),
            ("credito",      "🏦 Crédito",        "$0", "#7B1FA2"),
            ("transferencia","📲 Transferencia",  "$0", "#E65100"),
            ("qr",           "🔲 QR",             "$0", "#00695C"),
        ]:
            card = TarjetaMetrica(titulo, val, "", color)
            # Eliminar el stretch interno → el fondo ya no queda vacío abajo
            card.layout().takeAt(card.layout().count() - 1)
            card.setMinimumWidth(80)
            card.setFixedHeight(64)
            card.setStyleSheet(
                "#card_widget {"
                "  background:#2C2C2C;"
                "  border:1px solid #3C3C3C;"
                "  border-radius:6px;"
                "}")
            card.layout().setContentsMargins(8, 5, 8, 5)
            card.layout().setSpacing(2)
            card.lbl_val.setStyleSheet(
                f"color:{color}; font-size:13pt; font-weight:800;")
            self.cards_hoy[key] = card
            cards_layout.addWidget(card)
        lay.addLayout(cards_layout)

        # Tabla de ventas del día
        lbl = QLabel("Ventas registradas hoy")
        lbl.setStyleSheet("font-weight:700; color:#AAAAAA;")
        lay.addWidget(lbl)

        self.tabla_hoy = QTableWidget(0, 6)
        self.tabla_hoy.setHorizontalHeaderLabels([
            "#", "Hora", "Productos", "Medio de pago", "Descuento", "Total"
        ])
        self.tabla_hoy.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tabla_hoy.setAlternatingRowColors(True)
        self.tabla_hoy.verticalHeader().setVisible(False)
        lay.addWidget(self.tabla_hoy, 1)

        btn_refrescar = QPushButton("🔄  Refrescar")
        btn_refrescar.setObjectName("btn_secundario")

        def _refrescar_con_flash():
            self._actualizar_resumen_hoy()
            btn_refrescar.setObjectName("btn_exito")
            btn_refrescar.style().unpolish(btn_refrescar)
            btn_refrescar.style().polish(btn_refrescar)
            QTimer.singleShot(600, lambda: (
                btn_refrescar.setObjectName("btn_secundario"),
                btn_refrescar.style().unpolish(btn_refrescar),
                btn_refrescar.style().polish(btn_refrescar),
            ))

        btn_refrescar.clicked.connect(_refrescar_con_flash)
        lay.addWidget(btn_refrescar)
        return w

    def _actualizar_resumen_hoy(self):
        hoy = date.today().isoformat()
        rep = db.reporte_ventas_por_periodo(hoy, hoy)
        t = rep["totales"]

        if t["cantidad_ventas"]:
            self.cards_hoy["total_dia"].actualizar(f"${t['total_ventas']:,.2f}")
            self.cards_hoy["ventas_dia"].actualizar(str(t["cantidad_ventas"]))
            tp = t["total_ventas"] / t["cantidad_ventas"] if t["cantidad_ventas"] else 0
            self.cards_hoy["ticket_prom"].actualizar(f"${tp:,.2f}")
            self.cards_hoy["efectivo"].actualizar(f"${t['efectivo'] or 0:,.2f}")
            self.cards_hoy["debito"].actualizar(f"${t['debito'] or 0:,.2f}")
            self.cards_hoy["credito"].actualizar(f"${t['credito'] or 0:,.2f}")
            self.cards_hoy["transferencia"].actualizar(f"${t['transferencia'] or 0:,.2f}")
            self.cards_hoy["qr"].actualizar(f"${t['qr'] or 0:,.2f}")

        ventas = db.ventas_del_dia(hoy)
        self.tabla_hoy.setRowCount(len(ventas))
        mp_labels = {"efectivo": "💵 Efectivo", "debito": "💳 Débito",
                     "credito": "🏦 Crédito", "transferencia": "📲 Transf.",
                     "qr": "🔲 QR"}
        for i, v in enumerate(ventas):
            self.tabla_hoy.setItem(i, 0, QTableWidgetItem(str(v["id"])))
            self.tabla_hoy.setItem(i, 1, QTableWidgetItem(v["hora"][:5]))
            detalle = db.detalle_venta(v["id"])
            nombres = ", ".join(f"{d['cantidad']}x {d['nombre']}" for d in detalle["items"])
            self.tabla_hoy.setItem(i, 2, QTableWidgetItem(nombres))
            self.tabla_hoy.setItem(i, 3, QTableWidgetItem(mp_labels.get(v["medio_pago"], v["medio_pago"])))
            self.tabla_hoy.setItem(i, 4, QTableWidgetItem(f"${v['descuento']:,.2f}"))
            self.tabla_hoy.setItem(i, 5, QTableWidgetItem(f"${v['total']:,.2f}"))
            self.tabla_hoy.setRowHeight(i, 40)

    # ── Tab: PERÍODO ──────────────────────────────────────────

    def _build_tab_periodo(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        # Controles de rango
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Desde:"))
        self.date_desde = QDateEdit()
        self.date_desde.setCalendarPopup(True)
        self.date_desde.setDate(QDate.currentDate().addDays(-30))
        ctrl.addWidget(self.date_desde)
        ctrl.addWidget(QLabel("Hasta:"))
        self.date_hasta = QDateEdit()
        self.date_hasta.setCalendarPopup(True)
        self.date_hasta.setDate(QDate.currentDate())
        ctrl.addWidget(self.date_hasta)

        # Accesos rápidos
        self._btns_periodo = []
        for idx, (lbl, dias) in enumerate([("Hoy", 0), ("7 días", 6), ("30 días", 29),
                           ("Este mes", -1), ("Este año", -2)]):
            btn = QPushButton(lbl)
            btn.setObjectName("btn_secundario_compacto")
            btn.clicked.connect(lambda _, d=dias, i=idx: self._set_rango(d, i))
            ctrl.addWidget(btn)
            self._btns_periodo.append(btn)

        ctrl.addStretch()
        btn_ver = QPushButton("Ver reporte")
        btn_ver.clicked.connect(self._cargar_reporte_periodo)
        ctrl.addWidget(btn_ver)
        lay.addLayout(ctrl)

        # Tarjetas resumen
        self.cards_periodo = {}
        cards_layout = QHBoxLayout()
        for key, titulo, color in [
            ("total", "Total del período", "#C9A84C"),
            ("ventas", "N° de ventas", "#4CAF50"),
            ("ticket", "Ticket promedio", "#2196F3"),
            ("mejor_dia", "Mejor día", "#FF9800"),
        ]:
            card = TarjetaMetrica(titulo, "—", "", color)
            self.cards_periodo[key] = card
            cards_layout.addWidget(card)
        lay.addLayout(cards_layout)

        # Gráfico de ventas por día + tabla por medio de pago
        split = QHBoxLayout()

        if HAS_MATPLOTLIB:
            self.canvas_periodo = GraficoCanvas(width=7, height=3)
            split.addWidget(self.canvas_periodo, 3)

        # Tabla medios de pago
        self.tabla_medios = QTableWidget(5, 2)
        self.tabla_medios.setHorizontalHeaderLabels(["Medio de pago", "Total"])
        self.tabla_medios.setMaximumWidth(280)
        self.tabla_medios.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tabla_medios.verticalHeader().setVisible(False)
        self.tabla_medios.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        for i, mp in enumerate(["💵 Efectivo", "💳 Débito", "🏦 Crédito",
                                  "📲 Transferencia", "🔲 QR"]):
            self.tabla_medios.setItem(i, 0, QTableWidgetItem(mp))
            self.tabla_medios.setItem(i, 1, QTableWidgetItem("$0"))
        split.addWidget(self.tabla_medios, 1)
        lay.addLayout(split)
        return w

    def _set_rango(self, dias: int, btn_idx: int = -1):
        # Marcar botón activo y desactivar los demás
        for i, b in enumerate(self._btns_periodo):
            activo = (i == btn_idx)
            b.setObjectName("btn_periodo_activo" if activo else "btn_secundario_compacto")
            b.style().unpolish(b)
            b.style().polish(b)

        hoy = QDate.currentDate()
        if dias == -1:  # este mes
            self.date_desde.setDate(QDate(hoy.year(), hoy.month(), 1))
            self.date_hasta.setDate(hoy)
        elif dias == -2:  # este año
            self.date_desde.setDate(QDate(hoy.year(), 1, 1))
            self.date_hasta.setDate(hoy)
        else:
            self.date_desde.setDate(hoy.addDays(-dias))
            self.date_hasta.setDate(hoy)

    def _cargar_reporte_periodo(self):
        desde = self.date_desde.date().toString("yyyy-MM-dd")
        hasta = self.date_hasta.date().toString("yyyy-MM-dd")
        rep = db.reporte_ventas_por_periodo(desde, hasta)
        t = rep["totales"]

        if not t["cantidad_ventas"]:
            QMessageBox.information(self, "Sin datos", "No hay ventas en el período seleccionado.")
            return

        total = t["total_ventas"] or 0
        ventas = t["cantidad_ventas"] or 0
        ticket = total / ventas if ventas else 0

        self.cards_periodo["total"].actualizar(f"${total:,.2f}")
        self.cards_periodo["ventas"].actualizar(str(ventas))
        self.cards_periodo["ticket"].actualizar(f"${ticket:,.2f}")

        # Mejor día
        por_dia = rep["por_dia"]
        if por_dia:
            mejor = max(por_dia, key=lambda x: x["total"])
            self.cards_periodo["mejor_dia"].actualizar(
                f"${mejor['total']:,.2f}", mejor["fecha"])

        # Medios de pago
        vals = [t["efectivo"] or 0, t["debito"] or 0,
                t["credito"] or 0, t["transferencia"] or 0, t["qr"] or 0]
        for i, v in enumerate(vals):
            self.tabla_medios.setItem(i, 1, QTableWidgetItem(f"${v:,.2f}"))

        # Gráfico
        if HAS_MATPLOTLIB and por_dia:
            import numpy as np
            fechas = [r["fecha"] for r in por_dia]
            n_dias = len(fechas)

            mp_keys   = ["efectivo", "debito", "credito", "transferencia", "qr"]
            mp_labels = ["Efectivo", "Débito", "Crédito", "Transferencia", "QR"]
            mp_colors = ["#4CAF50", "#2196F3", "#FF9800", "#9C27B0", "#00BCD4"]

            # Solo mostrar medios de pago con al menos un valor > 0
            activos = [(k, l, c) for k, l, c in zip(mp_keys, mp_labels, mp_colors)
                       if any((r[k] or 0) > 0 for r in por_dia)]
            n_mp = len(activos) or 1

            self.canvas_periodo.fig.clear()
            ax = self.canvas_periodo.fig.add_subplot(111)
            ax.set_facecolor("#1A1A1A")
            self.canvas_periodo.fig.patch.set_facecolor("#1A1A1A")

            xs = np.arange(n_dias)
            bar_width = min(0.7 / n_mp, 0.25)   # barras más angostas si hay muchos medios
            offsets = np.linspace(-(n_mp - 1) / 2, (n_mp - 1) / 2, n_mp) * bar_width

            all_max = 0
            for (key, label, color), offset in zip(activos, offsets):
                vals = [r[key] or 0 for r in por_dia]
                bars = ax.bar(xs + offset, vals, bar_width,
                              color=color, alpha=0.90, label=label,
                              edgecolor="#111", linewidth=0.4)
                # Total encima de cada barra individual
                for rect, v in zip(bars, vals):
                    if v > 0:
                        ax.text(rect.get_x() + rect.get_width() / 2,
                                rect.get_height() + max(vals) * 0.015 if max(vals) else 1,
                                f"${v:,.0f}",
                                ha="center", va="bottom",
                                color=color, fontsize=6.8, fontweight="bold")
                        all_max = max(all_max, v)

            ax.set_xticks(xs)
            ax.set_xticklabels([f[-5:] for f in fechas],
                               rotation=45 if n_dias > 5 else 0,
                               color="#AAAAAA", fontsize=8)
            ax.tick_params(axis="y", colors="#AAAAAA")
            ax.set_ylabel("Total ($)", color="#AAAAAA")
            ax.set_title("Ventas por día — por medio de pago", color="#F5F5F5", fontsize=10)
            ax.spines[:].set_color("#333")
            ax.set_ylim(0, all_max * 1.18 if all_max else 1)
            ax.legend(loc="upper left", fontsize=7.5,
                      facecolor="#2A2A2A", edgecolor="#444",
                      labelcolor="#F5F5F5", framealpha=0.85, ncol=min(n_mp, 3))
            self.canvas_periodo.fig.tight_layout()
            self.canvas_periodo.draw()

    # ── Tab: TOP PRODUCTOS ────────────────────────────────────

    def _build_tab_top_productos(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        ctrl = QHBoxLayout()
        self.cmb_top_periodo = QComboBox()
        for t, d in [("Últimos 30 días", 30), ("Últimos 90 días", 90),
                     ("Este año", 365), ("Todo el tiempo", 0)]:
            self.cmb_top_periodo.addItem(t, d)
        ctrl.addWidget(QLabel("Período:"))
        ctrl.addWidget(self.cmb_top_periodo)
        self.spin_top_limite = QComboBox()
        for n in ["10", "20", "50"]:
            self.spin_top_limite.addItem(f"Top {n}", int(n))
        ctrl.addWidget(self.spin_top_limite)
        btn = QPushButton("Ver")
        btn.clicked.connect(self._cargar_top_productos)
        ctrl.addWidget(btn)
        ctrl.addStretch()
        lay.addLayout(ctrl)

        split = QHBoxLayout()

        self.tabla_top = QTableWidget(0, 5)
        self.tabla_top.setHorizontalHeaderLabels([
            "Posición", "Producto", "Categoría", "Unidades", "Ingresos"
        ])
        hh = self.tabla_top.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla_top.setAlternatingRowColors(True)
        self.tabla_top.verticalHeader().setVisible(False)
        self.tabla_top.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_top.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tabla_top.setToolTip("Doble clic para ver detalles del producto")
        self.tabla_top.cellDoubleClicked.connect(self._ver_detalle_producto)
        split.addWidget(self.tabla_top, 1)

        if HAS_MATPLOTLIB:
            self.canvas_top = GraficoCanvas(width=5, height=5)
            split.addWidget(self.canvas_top, 1)

        lay.addLayout(split)
        self._cargar_top_productos()
        return w

    def _cargar_top_productos(self):
        dias = self.cmb_top_periodo.currentData()
        limite = self.spin_top_limite.currentData()
        desde, hasta = None, None
        if dias:
            hasta = date.today().isoformat()
            desde = (date.today() - timedelta(days=dias)).isoformat()

        productos = db.reporte_productos_mas_vendidos(desde, hasta, limite)
        self.tabla_top.setRowCount(len(productos))
        for i, p in enumerate(productos):
            pos_item = QTableWidgetItem(f"#{i+1}")
            if i == 0:
                pos_item.setForeground(QColor("#C9A84C"))
                pos_item.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            self.tabla_top.setItem(i, 0, pos_item)
            nombre_item = QTableWidgetItem(p["nombre"])
            nombre_item.setData(Qt.ItemDataRole.UserRole, p["id"])
            nombre_item.setData(Qt.ItemDataRole.UserRole + 1, {
                "unidades": p["unidades_vendidas"],
                "ingresos": p["ingresos_total"],
                "periodo": self.cmb_top_periodo.currentText(),
            })
            self.tabla_top.setItem(i, 1, nombre_item)
            self.tabla_top.setItem(i, 2, QTableWidgetItem(p["categoria"] or "—"))
            self.tabla_top.setItem(i, 3, QTableWidgetItem(str(p["unidades_vendidas"])))
            self.tabla_top.setItem(i, 4, QTableWidgetItem(f"${p['ingresos_total']:,.2f}"))

        # Gráfico torta
        if HAS_MATPLOTLIB and productos:
            COLORES_30 = [
                "#722F37", "#C9A84C", "#4A90D9", "#5CB85C", "#9B59B6",
                "#E67E22", "#1ABC9C", "#E74C3C", "#3498DB", "#F39C12",
                "#8E44AD", "#27AE60", "#D35400", "#16A085", "#C0392B",
                "#2980B9", "#8B6914", "#6C3483", "#117A65", "#922B21",
                "#1F618D", "#7D6608", "#4A235A", "#0E6655", "#784212",
                "#D4AC0D", "#A04000", "#1A5276", "#6E2FBF", "#2ECC71",
            ]
            MAX_SLICES = 15
            if len(productos) > MAX_SLICES:
                pie_prods = productos[:MAX_SLICES]
                otros_u = sum(p["unidades_vendidas"] for p in productos[MAX_SLICES:])
                n_otros = len(productos) - MAX_SLICES
                nombres = [p["nombre"][:22] for p in pie_prods] + [f"Otros ({n_otros})"]
                unidades = [p["unidades_vendidas"] for p in pie_prods] + [otros_u]
                colores_uso = COLORES_30[:MAX_SLICES] + ["#555555"]
            else:
                nombres = [p["nombre"][:22] for p in productos]
                unidades = [p["unidades_vendidas"] for p in productos]
                colores_uso = COLORES_30[:len(productos)]

            total = sum(unidades)
            pct = [u / total * 100 if total else 0 for u in unidades]
            etiquetas = [f"{n}  {v:.1f}%" for n, v in zip(nombres, pct)]

            self.canvas_top.fig.clear()
            ax = self.canvas_top.fig.add_subplot(111)
            ax.set_facecolor("#1E1E1E")
            wedges, _ = ax.pie(
                unidades, labels=None, colors=colores_uso, startangle=90,
            )
            ncols = 2 if len(nombres) > 10 else 1
            ax.legend(
                wedges, etiquetas,
                loc="center left", bbox_to_anchor=(1.02, 0.5),
                fontsize=7, framealpha=0.3,
                labelcolor="#F5F5F5", facecolor="#2C2C2C",
                ncols=ncols, borderpad=0.8,
            )
            ax.set_title("Participación de ventas", color="#F5F5F5", fontsize=10, pad=10)
            self.canvas_top.fig.tight_layout()
            self.canvas_top.draw()

    # ── Tab: MENSUAL/ANUAL ────────────────────────────────────

    def _build_tab_mensuales(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        ctrl = QHBoxLayout()
        self.cmb_anio = QComboBox()
        anio_actual = date.today().year
        for a in range(anio_actual, anio_actual - 5, -1):
            self.cmb_anio.addItem(str(a), a)
        ctrl.addWidget(QLabel("Año:"))
        ctrl.addWidget(self.cmb_anio)
        btn = QPushButton("Ver")
        btn.clicked.connect(self._cargar_mensuales)
        ctrl.addWidget(btn)
        ctrl.addStretch()
        lay.addLayout(ctrl)

        if HAS_MATPLOTLIB:
            self.canvas_mensual = GraficoCanvas(width=8, height=4)
            lay.addWidget(self.canvas_mensual)

        self.tabla_mensual = QTableWidget(0, 4)
        self.tabla_mensual.setHorizontalHeaderLabels([
            "Mes", "Total facturado", "N° ventas", "Ticket promedio"
        ])
        self.tabla_mensual.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tabla_mensual.setAlternatingRowColors(True)
        self.tabla_mensual.verticalHeader().setVisible(False)
        lay.addWidget(self.tabla_mensual)
        self._cargar_mensuales()
        return w

    def _ver_detalle_producto(self, row: int, _col: int):
        item = self.tabla_top.item(row, 1)
        if not item:
            return
        pid = item.data(Qt.ItemDataRole.UserRole)
        ventas = item.data(Qt.ItemDataRole.UserRole + 1)
        if pid is None:
            return
        p = db.obtener_producto(pid)
        if not p:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Detalle — {p['nombre']}")
        dlg.setMinimumWidth(360)
        dlg.setModal(True)
        lay = QVBoxLayout(dlg)
        lay.setSpacing(12)
        lay.setContentsMargins(24, 20, 24, 20)

        titulo = QLabel(f"📦  {p['nombre']}")
        titulo.setObjectName("titulo_seccion")
        titulo.setWordWrap(True)
        lay.addWidget(titulo)

        def fila(etiqueta, valor, color=None):
            row_lay = QHBoxLayout()
            lbl_e = QLabel(etiqueta)
            lbl_e.setStyleSheet("color:#888; min-width:150px;")
            lbl_v = QLabel(str(valor))
            if color:
                lbl_v.setStyleSheet(f"font-weight:700; color:{color};")
            else:
                lbl_v.setStyleSheet("font-weight:600; color:#F5F5F5;")
            lbl_v.setWordWrap(True)
            row_lay.addWidget(lbl_e)
            row_lay.addWidget(lbl_v, 1)
            lay.addLayout(row_lay)

        fila("Categoría:",        p["categoria_nombre"] or "—")
        fila("Precio de venta:",  f"$ {p['precio_venta']:,.2f}", "#C9A84C")
        fila("Precio de costo:",  f"$ {p['precio_costo']:,.2f}" if p["precio_costo"] else "—")
        fila("Stock actual:",     p["stock_actual"],
             "#F44336" if (p["stock_actual"] or 0) <= (p["stock_minimo"] or 0) else "#4CAF50")
        fila("Stock mínimo:",     p["stock_minimo"] or 0)

        if ventas:
            sep_v = QFrame()
            sep_v.setFrameShape(QFrame.Shape.HLine)
            sep_v.setStyleSheet("color:#333;")
            lay.addWidget(sep_v)
            periodo_lbl = QLabel(f"📊  Ventas · {ventas['periodo']}")
            periodo_lbl.setStyleSheet("color:#888; font-size:9pt;")
            lay.addWidget(periodo_lbl)
            fila("Unidades vendidas:", ventas["unidades"], "#F5F5F5")
            fila("Ingresos generados:", f"$ {ventas['ingresos']:,.2f}", "#4CAF50")

        fila("Unidad de venta:",  p["unidad"] or "—")
        fila("Código de barras:", p["codigo_barras"] or "Sin código")
        if p["descripcion"]:
            fila("Descripción:", p["descripcion"])

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#333;")
        lay.addWidget(sep)

        btn = QPushButton("Cerrar")
        btn.setObjectName("btn_secundario")
        btn.clicked.connect(dlg.accept)
        lay.addWidget(btn)
        dlg.exec()

    def _cargar_mensuales(self):
        anio = self.cmb_anio.currentData() if self.cmb_anio.count() else date.today().year
        datos = db.reporte_ingresos_mensuales(anio)
        meses_nombres = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

        self.tabla_mensual.setRowCount(len(datos))
        for i, d in enumerate(datos):
            mes_num = int(d["mes"][-2:]) - 1
            self.tabla_mensual.setItem(i, 0, QTableWidgetItem(
                f"{meses_nombres[mes_num]} {d['mes'][:4]}"))
            self.tabla_mensual.setItem(i, 1, QTableWidgetItem(f"${d['total']:,.2f}"))
            self.tabla_mensual.setItem(i, 2, QTableWidgetItem(str(d["ventas"])))
            self.tabla_mensual.setItem(i, 3, QTableWidgetItem(f"${d['ticket_promedio']:,.2f}"))

        if HAS_MATPLOTLIB and datos:
            meses_lbls = [meses_nombres[int(d["mes"][-2:]) - 1] for d in datos]
            totales = [d["total"] for d in datos]
            self.canvas_mensual.fig.clear()
            ax = self.canvas_mensual.fig.add_subplot(111)
            ax.set_facecolor("#1E1E1E")
            bars = ax.bar(meses_lbls, totales, color="#722F37", alpha=0.9)
            # Etiqueta valor encima de cada barra
            for bar, val in zip(bars, totales):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(totales) * 0.01,
                        f"${val:,.0f}", ha="center", va="bottom",
                        color="#C9A84C", fontsize=7)
            ax.tick_params(colors="#AAAAAA")
            ax.set_ylabel("Total ($)", color="#AAAAAA")
            ax.set_title(f"Ingresos mensuales {anio}", color="#F5F5F5")
            ax.spines[:].set_color("#333")
            self.canvas_mensual.fig.tight_layout()
            self.canvas_mensual.draw()

    # ── Tab: FINANZAS / KPIs ──────────────────────────────────

    def _build_tab_finanzas(self):
        outer = QTabWidget()
        outer.addTab(self._build_fin_tab_metricas(), "📊  Métricas")
        outer.addTab(self._build_fin_tab_detalle(),  "📋  Detalle")
        self._fin_cargar()
        self._fin_cargar_detalle()
        return outer

    # ── Sub-tab: MÉTRICAS ─────────────────────────────────────

    def _build_fin_tab_metricas(self):
        outer = QWidget()
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer_lay.addWidget(scroll)

        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(8)
        lay.setContentsMargins(16, 16, 16, 16)
        scroll.setWidget(w)

        CARD_H = 155

        def _sec_label(texto, color):
            lbl = QLabel(f"  {texto}")
            lbl.setStyleSheet(
                f"color:{color}; font-size:10pt; font-weight:700; "
                f"border-left:3px solid {color}; padding:4px 0 4px 8px;")
            lbl.setFixedHeight(28)
            return lbl

        # ── Selector de período ───────────────────────────────
        ctrl = QHBoxLayout()
        ctrl.setSpacing(10)

        ctrl.addWidget(QLabel("Año:"))
        self.fin_spin_anio = QSpinBox()
        self.fin_spin_anio.setRange(2020, 2099)
        self.fin_spin_anio.setValue(date.today().year)
        ctrl.addWidget(self.fin_spin_anio)

        ctrl.addWidget(QLabel("Mes:"))
        self.fin_cmb_mes = QComboBox()
        self.fin_cmb_mes.addItem("Año completo", 0)
        meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                 "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
        for i, m in enumerate(meses, 1):
            self.fin_cmb_mes.addItem(m, i)
        self.fin_cmb_mes.setCurrentIndex(date.today().month)
        ctrl.addWidget(self.fin_cmb_mes)

        btn_cargar = QPushButton("Calcular")
        btn_cargar.setObjectName("btn_secundario_compacto")
        btn_cargar.clicked.connect(self._fin_cargar)
        ctrl.addWidget(btn_cargar)
        ctrl.addStretch()
        lay.addLayout(ctrl)
        lay.addSpacing(8)

        # ── Sección: Resultados del período ──────────────────
        self.fin_cards = {}
        lay.addWidget(_sec_label("Resultados del período", "#C9A84C"))
        lay.addSpacing(4)

        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(10)
        kpi_grid.setColumnStretch(0, 1)
        kpi_grid.setColumnStretch(1, 1)
        kpi_grid.setColumnStretch(2, 1)
        for grid_row, grid_col, key, titulo, color in [
            (0, 0, "ingresos",     "Ingresos totales",    "#C9A84C"),
            (0, 1, "costo",        "Costo de lo vendido", "#888888"),
            (0, 2, "margen_bruto", "Margen bruto",        "#4CAF50"),
            (1, 0, "gastos",       "Gastos operativos",   "#EF5350"),
            (1, 1, "margen_neto",  "Margen neto",         "#2196F3"),
        ]:
            card = TarjetaMetrica(titulo, "—", "", color, key=key)
            card.setMinimumWidth(200)
            card.setFixedHeight(CARD_H)
            self.fin_cards[key] = card
            kpi_grid.addWidget(card, grid_row, grid_col)
        lay.addLayout(kpi_grid)
        lay.addSpacing(12)

        # ── Sección: Inventario actual ────────────────────────
        lay.addWidget(_sec_label("Inventario actual", "#FF9800"))
        lay.addSpacing(4)

        inv_row = QHBoxLayout()
        inv_row.setSpacing(10)
        for key, titulo, color in [
            ("stock_costo", "Stock al costo",           "#FF9800"),
            ("stock_venta", "Stock a precio de venta",  "#26C6DA"),
        ]:
            card = TarjetaMetrica(titulo, "—", "", color, key=key)
            card.setMinimumWidth(200)
            card.setFixedHeight(CARD_H)
            self.fin_cards[key] = card
            inv_row.addWidget(card)
        inv_row.addStretch()
        lay.addLayout(inv_row)
        lay.addSpacing(12)

        # ── Sección: Sueldos del período ──────────────────────
        sueldo_hdr = QHBoxLayout()
        sueldo_hdr.addWidget(_sec_label("Sueldos del período", "#AB47BC"))
        sueldo_hdr.addSpacing(16)
        self.fin_chk_descontar_gastos = QCheckBox("Descontar gastos operativos")
        self.fin_chk_descontar_gastos.setChecked(False)
        self.fin_chk_descontar_gastos.setToolTip(
            "Activado: el sueldo se calcula sobre el margen neto (ya descontados los gastos).\n"
            "Desactivado: el sueldo se calcula sobre el margen bruto (sin descontar gastos).")
        self.fin_chk_descontar_gastos.stateChanged.connect(self._fin_actualizar_sueldos)
        sueldo_hdr.addWidget(self.fin_chk_descontar_gastos)
        sueldo_hdr.addStretch()
        lay.addLayout(sueldo_hdr)
        lay.addSpacing(4)

        sueldo_row = QHBoxLayout()
        sueldo_row.setSpacing(10)
        for key, titulo, color in [
            ("sueldo_total",      "Pozo a repartir",    "#AB47BC"),
            ("sueldo_individual", "Sueldo por persona", "#EC407A"),
        ]:
            card = TarjetaMetrica(titulo, "—", "", color, key=key)
            card.setMinimumWidth(200)
            card.setFixedHeight(CARD_H)
            self.fin_cards[key] = card
            sueldo_row.addWidget(card)
        sueldo_row.addStretch()
        lay.addLayout(sueldo_row)
        lay.addStretch()
        return outer

    # ── Sub-tab: DETALLE ──────────────────────────────────────

    def _build_fin_tab_detalle(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)
        lay.setContentsMargins(16, 12, 16, 16)

        # ── Barra de filtros ──────────────────────────────────
        filt = QHBoxLayout()
        filt.setSpacing(8)

        hoy = QDate.currentDate()

        filt.addWidget(QLabel("Desde:"))
        self.fin_det_desde = QDateEdit(QDate(hoy.year(), hoy.month(), 1))
        self.fin_det_desde.setCalendarPopup(True)
        self.fin_det_desde.setDisplayFormat("dd/MM/yyyy")
        filt.addWidget(self.fin_det_desde)

        filt.addWidget(QLabel("Hasta:"))
        self.fin_det_hasta = QDateEdit(hoy)
        self.fin_det_hasta.setCalendarPopup(True)
        self.fin_det_hasta.setDisplayFormat("dd/MM/yyyy")
        filt.addWidget(self.fin_det_hasta)

        filt.addWidget(QLabel("Categoría:"))
        self.fin_det_cat = QComboBox()
        self.fin_det_cat.addItem("Todas", None)
        for cat in db.CATEGORIAS_GASTO:
            self.fin_det_cat.addItem(cat, cat)
        filt.addWidget(self.fin_det_cat)

        filt.addWidget(QLabel("Buscar:"))
        self.fin_det_buscar = QLineEdit()
        self.fin_det_buscar.setPlaceholderText("Descripción...")
        self.fin_det_buscar.setFixedWidth(160)
        self.fin_det_buscar.returnPressed.connect(self._fin_cargar_detalle)
        filt.addWidget(self.fin_det_buscar)

        btn_buscar = QPushButton("🔍  Aplicar")
        btn_buscar.clicked.connect(self._fin_cargar_detalle)
        filt.addWidget(btn_buscar)
        lay.addLayout(filt)

        # Botón registrar gasto en su propia línea (siempre visible y sin recortes)
        accion_bar = QHBoxLayout()
        accion_bar.addStretch()
        btn_gasto = QPushButton("➕  Registrar gasto")
        btn_gasto.clicked.connect(self._fin_agregar_gasto)
        accion_bar.addWidget(btn_gasto)
        lay.addLayout(accion_bar)

        # ── Tablas: medios de pago (izq) + gastos (der) ──────
        split = QHBoxLayout()
        split.setSpacing(16)

        # Izquierda: ingresos por medio de pago
        izq = QVBoxLayout()
        izq.setSpacing(6)
        lbl_mp = QLabel("Ingresos por medio de pago")
        lbl_mp.setStyleSheet("font-weight:700; font-size:11pt; color:#C9A84C;")
        izq.addWidget(lbl_mp)

        self.fin_tabla_mp = QTableWidget(5, 2)
        self.fin_tabla_mp.setHorizontalHeaderLabels(["Medio", "Total"])
        self.fin_tabla_mp.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.fin_tabla_mp.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.fin_tabla_mp.verticalHeader().setVisible(False)
        self.fin_tabla_mp.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.fin_tabla_mp.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        for i, mp in enumerate(["💵 Efectivo","💳 Débito","🏦 Crédito","📲 Transferencia","🔲 QR"]):
            self.fin_tabla_mp.setItem(i, 0, QTableWidgetItem(mp))
            self.fin_tabla_mp.setItem(i, 1, QTableWidgetItem("$0"))
        izq.addWidget(self.fin_tabla_mp, 1)
        split.addLayout(izq, 1)

        # Derecha: tabla de gastos (ordenable por encabezado)
        der = QVBoxLayout()
        der.setSpacing(6)
        lbl_g = QLabel("Gastos del período  —  clic en encabezado para ordenar")
        lbl_g.setStyleSheet("font-weight:700; font-size:11pt; color:#EF5350;")
        der.addWidget(lbl_g)

        self.fin_tabla_gastos = QTableWidget(0, 5)
        self.fin_tabla_gastos.setHorizontalHeaderLabels(
            ["Fecha", "Categoría", "Descripción", "Monto", ""])
        self.fin_tabla_gastos.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.fin_tabla_gastos.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.fin_tabla_gastos.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.fin_tabla_gastos.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.fin_tabla_gastos.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.fin_tabla_gastos.verticalHeader().setVisible(False)
        self.fin_tabla_gastos.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.fin_tabla_gastos.setAlternatingRowColors(True)
        self.fin_tabla_gastos.setSortingEnabled(True)
        self.fin_tabla_gastos.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        der.addWidget(self.fin_tabla_gastos, 1)
        split.addLayout(der, 2)

        lay.addLayout(split, 1)
        return w

    def _fin_rango(self):
        """Devuelve (desde, hasta) en formato ISO según el selector."""
        anio = self.fin_spin_anio.value()
        mes  = self.fin_cmb_mes.currentData()
        if mes == 0:
            return f"{anio}-01-01", f"{anio}-12-31"
        import calendar
        ultimo = calendar.monthrange(anio, mes)[1]
        return f"{anio}-{mes:02d}-01", f"{anio}-{mes:02d}-{ultimo:02d}"

    def _fin_cargar(self):
        desde, hasta = self._fin_rango()
        res = db.resumen_finanzas_periodo(desde, hasta)

        # Cards
        def fmt(v): return f"${v:,.2f}"
        self.fin_cards["ingresos"].actualizar(fmt(res["ingresos"]))
        self.fin_cards["costo"].actualizar(fmt(res["costo_estimado"]))
        color_mb = "#4CAF50" if res["margen_bruto"] >= 0 else "#EF5350"
        self.fin_cards["margen_bruto"].titulo_color = color_mb
        self.fin_cards["margen_bruto"].actualizar(fmt(res["margen_bruto"]))
        self.fin_cards["gastos"].actualizar(fmt(res["gastos_operativos"]))
        color_mn = "#2196F3" if res["margen_neto"] >= 0 else "#EF5350"
        self.fin_cards["margen_neto"].titulo_color = color_mn
        self.fin_cards["margen_neto"].actualizar(
            fmt(res["margen_neto"]) + f"  ({res['pct_margen_neto']:.1f}%)")

        # Tarjetas de inventario (siempre actuales, no dependen del período)
        inv = db.valor_stock_inventario()
        self.fin_cards["stock_costo"].actualizar(fmt(inv["al_costo"]))
        self.fin_cards["stock_venta"].actualizar(fmt(inv["al_venta"]))

        # Guardar valores para recalcular sueldos al cambiar el checkbox
        self._fin_margen_bruto = res["margen_bruto"]
        self._fin_margen_neto  = res["margen_neto"]
        self._fin_actualizar_sueldos()

    def _fin_actualizar_sueldos(self):
        """Recalcula tarjetas de sueldo según el checkbox de gastos operativos."""
        base = getattr(self, "_fin_margen_neto", 0) \
            if self.fin_chk_descontar_gastos.isChecked() \
            else getattr(self, "_fin_margen_bruto", 0)
        individual = base / 2
        color_t = "#AB47BC" if base >= 0 else "#EF5350"
        color_i = "#EC407A" if individual >= 0 else "#EF5350"
        self.fin_cards["sueldo_total"].titulo_color = color_t
        self.fin_cards["sueldo_total"].actualizar(f"${base:,.2f}")
        self.fin_cards["sueldo_individual"].titulo_color = color_i
        tipo = "(c/gastos)" if self.fin_chk_descontar_gastos.isChecked() else "(s/gastos)"
        self.fin_cards["sueldo_individual"].actualizar(
            f"${individual:,.2f}", subtitulo=tipo)

    def _fin_agregar_gasto(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Registrar gasto")
        dlg.setMinimumWidth(420)
        lay = QVBoxLayout(dlg)
        lay.setSpacing(10)
        lay.setContentsMargins(20, 16, 20, 16)

        form = QFormLayout()
        form.setSpacing(8)

        # Fecha
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDate(QDate.currentDate())
        date_edit.setDisplayFormat("dd/MM/yyyy")
        form.addRow("Fecha:", date_edit)

        # Categoría
        cmb_cat = QComboBox()
        for cat in db.CATEGORIAS_GASTO:
            cmb_cat.addItem(cat)
        form.addRow("Categoría:", cmb_cat)

        # Descripción
        txt_desc = QLineEdit()
        txt_desc.setPlaceholderText("Ej: Factura Edesur marzo")
        form.addRow("Descripción:", txt_desc)

        # Monto
        spin_monto = QDoubleSpinBox()
        spin_monto.setRange(0, 99999999)
        spin_monto.setDecimals(2)
        spin_monto.setSingleStep(100)
        spin_monto.setPrefix("$ ")
        form.addRow("Monto:", spin_monto)

        lay.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            fecha = date_edit.date().toString("yyyy-MM-dd")
            cat   = cmb_cat.currentText()
            desc  = txt_desc.text().strip()
            monto = spin_monto.value()
            if not desc:
                QMessageBox.warning(self, "Datos incompletos", "Ingresá una descripción.")
                return
            if monto <= 0:
                QMessageBox.warning(self, "Datos incompletos", "El monto debe ser mayor a $0.")
                return
            db.registrar_gasto(fecha, cat, desc, monto)
            self._fin_cargar_detalle()

    def _fin_cargar_detalle(self):
        """Recarga las tablas del tab Detalle usando los filtros de fecha/categoría/texto."""
        desde = self.fin_det_desde.date().toString("yyyy-MM-dd")
        hasta = self.fin_det_hasta.date().toString("yyyy-MM-dd")
        cat_sel = self.fin_det_cat.currentData()          # None → todas
        texto   = self.fin_det_buscar.text().strip().lower()

        # Tabla medios de pago (mismo rango de fechas que los filtros del detalle)
        res = db.resumen_finanzas_periodo(desde, hasta)
        mp  = res["por_medio"]
        for i, key in enumerate(["efectivo","debito","credito","transferencia","qr"]):
            self.fin_tabla_mp.setItem(i, 1, QTableWidgetItem(f"${mp[key]:,.2f}"))

        # Tabla gastos con filtros aplicados en Python
        gastos = db.obtener_gastos_periodo(desde, hasta)
        if cat_sel:
            gastos = [g for g in gastos if g["categoria"] == cat_sel]
        if texto:
            gastos = [g for g in gastos if texto in g["descripcion"].lower()]

        # Subclase local para ordenamiento numérico correcto en columna Monto
        class _NumItem(QTableWidgetItem):
            def __lt__(self, other):
                try:
                    return (float(self.data(Qt.ItemDataRole.UserRole)) <
                            float(other.data(Qt.ItemDataRole.UserRole)))
                except (TypeError, ValueError):
                    return super().__lt__(other)

        self.fin_tabla_gastos.setSortingEnabled(False)
        self.fin_tabla_gastos.setRowCount(len(gastos))
        for i, g in enumerate(gastos):
            self.fin_tabla_gastos.setItem(i, 0, QTableWidgetItem(str(g["fecha"])))
            self.fin_tabla_gastos.setItem(i, 1, QTableWidgetItem(g["categoria"]))
            self.fin_tabla_gastos.setItem(i, 2, QTableWidgetItem(g["descripcion"]))
            monto_it = _NumItem(f"${g['monto']:,.2f}")
            monto_it.setData(Qt.ItemDataRole.UserRole, g["monto"])
            monto_it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            monto_it.setForeground(QColor("#EF5350"))
            self.fin_tabla_gastos.setItem(i, 3, monto_it)
            gid = g["id"]
            btn_del = QPushButton("✕")
            btn_del.setFixedSize(28, 28)
            btn_del.setStyleSheet(
                "QPushButton{background:#5C0000;color:#FF8A80;border-radius:4px;font-weight:700;}"
                "QPushButton:hover{background:#7F0000;}")
            btn_del.clicked.connect(lambda _, gid=gid: self._fin_eliminar_gasto(gid))
            self.fin_tabla_gastos.setCellWidget(i, 4, btn_del)
            self.fin_tabla_gastos.setRowHeight(i, 36)
        self.fin_tabla_gastos.setSortingEnabled(True)

    def _fin_eliminar_gasto(self, gasto_id: int):
        resp = QMessageBox.question(
            self, "Eliminar gasto",
            "¿Eliminás este gasto? Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp == QMessageBox.StandardButton.Yes:
            db.eliminar_gasto(gasto_id)
            self._fin_cargar_detalle()

    # ── Tab: HISTORIAL DE VENTAS ──────────────────────────────

    def _build_tab_historial_ventas(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Desde:"))
        self.date_hist_desde = QDateEdit()
        self.date_hist_desde.setCalendarPopup(True)
        self.date_hist_desde.setDate(QDate.currentDate().addDays(-7))
        ctrl.addWidget(self.date_hist_desde)
        ctrl.addWidget(QLabel("Hasta:"))
        self.date_hist_hasta = QDateEdit()
        self.date_hist_hasta.setCalendarPopup(True)
        self.date_hist_hasta.setDate(QDate.currentDate())
        ctrl.addWidget(self.date_hist_hasta)
        btn = QPushButton("Buscar")
        btn.clicked.connect(self._cargar_historial_ventas)
        ctrl.addWidget(btn)
        ctrl.addStretch()
        lay.addLayout(ctrl)

        self.tabla_hist_ventas = QTableWidget(0, 7)
        self.tabla_hist_ventas.setHorizontalHeaderLabels([
            "#", "Fecha", "Hora", "Productos", "Medio de pago", "Descuento", "Total"
        ])
        self.tabla_hist_ventas.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tabla_hist_ventas.setAlternatingRowColors(True)
        self.tabla_hist_ventas.verticalHeader().setVisible(False)
        lay.addWidget(self.tabla_hist_ventas, 1)
        self._cargar_historial_ventas()
        return w

    def _cargar_historial_ventas(self):
        desde = self.date_hist_desde.date().toString("yyyy-MM-dd")
        hasta = self.date_hist_hasta.date().toString("yyyy-MM-dd")
        from db.database import get_connection
        with get_connection() as conn:
            ventas = conn.execute("""
                SELECT v.*, GROUP_CONCAT(p.nombre || ' x' || dv.cantidad, ' | ') as productos
                FROM ventas v
                LEFT JOIN detalle_ventas dv ON dv.venta_id = v.id
                LEFT JOIN productos p ON p.id = dv.producto_id
                WHERE v.fecha BETWEEN ? AND ?
                GROUP BY v.id ORDER BY v.datetime_venta DESC
            """, (desde, hasta)).fetchall()

        mp_labels = {"efectivo": "💵 Efectivo", "debito": "💳 Débito",
                     "credito": "🏦 Crédito", "transferencia": "📲 Transf.",
                     "qr": "🔲 QR"}
        self.tabla_hist_ventas.setRowCount(len(ventas))
        for i, v in enumerate(ventas):
            self.tabla_hist_ventas.setItem(i, 0, QTableWidgetItem(str(v["id"])))
            self.tabla_hist_ventas.setItem(i, 1, QTableWidgetItem(v["fecha"]))
            self.tabla_hist_ventas.setItem(i, 2, QTableWidgetItem(v["hora"][:5]))
            self.tabla_hist_ventas.setItem(i, 3, QTableWidgetItem(v["productos"] or ""))
            self.tabla_hist_ventas.setItem(i, 4, QTableWidgetItem(
                mp_labels.get(v["medio_pago"], v["medio_pago"])))
            self.tabla_hist_ventas.setItem(i, 5, QTableWidgetItem(f"${v['descuento']:,.2f}"))

            total_item = QTableWidgetItem(f"${v['total']:,.2f}")
            if v["anulada"]:
                total_item.setForeground(QColor("#888"))
                total_item.setText(f"ANULADA")
            self.tabla_hist_ventas.setItem(i, 6, total_item)
            self.tabla_hist_ventas.setRowHeight(i, 40)

    def _tab_changed(self, idx: int):
        if idx == 0:
            self._actualizar_resumen_hoy()

    # ── Exportar Excel ────────────────────────────────────────

    def _exportar_excel(self):
        try:
            import pandas as pd
            from datetime import datetime as dt
            from config import EXPORTS_DIR
            import os

            os.makedirs(EXPORTS_DIR, exist_ok=True)
            ts = dt.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(EXPORTS_DIR, f"reporte_vinoteca_{ts}.xlsx")

            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                # Ventas últimos 30 días
                desde = (date.today() - timedelta(days=30)).isoformat()
                hasta = date.today().isoformat()
                from db.database import get_connection
                with get_connection() as conn:
                    df_ventas = pd.read_sql_query(
                        "SELECT * FROM ventas WHERE fecha BETWEEN ? AND ? ORDER BY fecha DESC",
                        conn, params=(desde, hasta)
                    )
                    df_detalle = pd.read_sql_query(
                        "SELECT dv.*, p.nombre as producto, p.codigo_barras "
                        "FROM detalle_ventas dv JOIN productos p ON p.id = dv.producto_id",
                        conn
                    )
                    df_stock = pd.read_sql_query(
                        "SELECT p.*, c.nombre as categoria FROM productos p "
                        "LEFT JOIN categorias c ON c.id = p.categoria_id WHERE p.activo=1",
                        conn
                    )

                df_ventas.to_excel(writer, sheet_name="Ventas", index=False)
                df_detalle.to_excel(writer, sheet_name="Detalle ventas", index=False)
                df_stock.to_excel(writer, sheet_name="Stock actual", index=False)

            QMessageBox.information(
                self, "✅  Exportado",
                f"Reporte exportado correctamente:\n{path}"
            )
        except ImportError:
            QMessageBox.warning(
                self, "pandas no instalado",
                "Para exportar a Excel ejecutá:\n  pip install pandas openpyxl"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error al exportar", str(e))
