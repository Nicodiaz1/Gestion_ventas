# ─────────────────────────────────────────────────────────────
#  ui/reportes.py  –  Reportes y métricas
# ─────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QTabWidget, QDateEdit, QMessageBox, QSizePolicy, QFrame,
    QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt, QDate
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
    def __init__(self, titulo: str, valor: str, subtitulo: str = "", color: str = "#722F37"):
        super().__init__()
        self.setObjectName("card_widget")
        self.setMinimumSize(160, 100)
        self.setMaximumHeight(130)

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
        lay.addStretch()

        self.lbl_val = lbl_val
        self.lbl_sub = lbl_sub

    def actualizar(self, valor: str, subtitulo: str = ""):
        self.lbl_val.setText(valor)
        if subtitulo:
            self.lbl_sub.setText(subtitulo)


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

        # Tarjetas de métricas
        self.cards_hoy = {}
        cards_layout = QHBoxLayout()
        metricas = [
            ("total_dia",    "Total del día",    "$0",    "#C9A84C"),
            ("ventas_dia",   "Ventas realizadas","0",     "#4CAF50"),
            ("ticket_prom",  "Ticket promedio",  "$0",    "#2196F3"),
            ("efectivo",     "💵 Efectivo",       "$0",    "#4CAF50"),
            ("debito",       "💳 Débito",          "$0",    "#1565C0"),
            ("credito",      "🏦 Crédito",        "$0",    "#7B1FA2"),
            ("transferencia","📲 Transferencia",  "$0",    "#E65100"),
            ("qr",           "🔲 QR",             "$0",    "#00695C"),
        ]
        for key, titulo, val, color in metricas:
            card = TarjetaMetrica(titulo, val, "", color)
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
        btn_refrescar.clicked.connect(self._actualizar_resumen_hoy)
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
            nombres = ", ".join(f"{d['cantidad']}x {d['nombre']}" for d in detalle)
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
        for lbl, dias in [("Hoy", 0), ("7 días", 6), ("30 días", 29),
                           ("Este mes", -1), ("Este año", -2)]:
            btn = QPushButton(lbl)
            btn.setObjectName("btn_secundario")
            btn.setMaximumWidth(80)
            btn.clicked.connect(lambda _, d=dias: self._set_rango(d))
            ctrl.addWidget(btn)

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

    def _set_rango(self, dias: int):
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
            fechas = [r["fecha"] for r in por_dia]
            totales = [r["total"] for r in por_dia]
            self.canvas_periodo.fig.clear()
            ax = self.canvas_periodo.fig.add_subplot(111)
            ax.set_facecolor("#1E1E1E")
            ax.bar(range(len(fechas)), totales, color="#722F37", alpha=0.85)
            ax.set_xticks(range(len(fechas)))
            xticklabels = [f[-5:] for f in fechas]  # MM-DD
            ax.set_xticklabels(xticklabels, rotation=45, color="#AAAAAA", fontsize=8)
            ax.tick_params(axis="y", colors="#AAAAAA")
            ax.set_ylabel("Total ($)", color="#AAAAAA")
            ax.set_title("Ventas por día", color="#F5F5F5")
            ax.spines[:].set_color("#333")
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
        self.tabla_top.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla_top.setAlternatingRowColors(True)
        self.tabla_top.verticalHeader().setVisible(False)
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
            self.tabla_top.setItem(i, 1, QTableWidgetItem(p["nombre"]))
            self.tabla_top.setItem(i, 2, QTableWidgetItem(p["categoria"] or "—"))
            self.tabla_top.setItem(i, 3, QTableWidgetItem(str(p["unidades_vendidas"])))
            self.tabla_top.setItem(i, 4, QTableWidgetItem(f"${p['ingresos_total']:,.2f}"))

        # Gráfico torta
        if HAS_MATPLOTLIB and productos:
            top5 = productos[:8]
            nombres = [p["nombre"][:20] for p in top5]
            unidades = [p["unidades_vendidas"] for p in top5]
            colores = ["#722F37", "#C9A84C", "#8B3A44", "#A07830",
                       "#5C2530", "#D4A840", "#4A1A20", "#E8C860"]

            self.canvas_top.fig.clear()
            ax = self.canvas_top.fig.add_subplot(111)
            ax.set_facecolor("#1E1E1E")
            wedges, texts, autotexts = ax.pie(
                unidades, labels=None, colors=colores[:len(top5)],
                autopct="%1.1f%%", startangle=90,
                textprops={"color": "#F5F5F5", "fontsize": 8}
            )
            ax.legend(wedges, nombres, loc="lower left",
                      fontsize=7, framealpha=0.3,
                      labelcolor="#F5F5F5",
                      facecolor="#2C2C2C")
            ax.set_title("Participación de ventas", color="#F5F5F5", fontsize=10)
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
