# ─────────────────────────────────────────────────────────────
#  ui/exportar.py  –  Panel de exportación a Excel
# ─────────────────────────────────────────────────────────────

import os
import sys
from datetime import date, datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QFileDialog, QMessageBox, QScrollArea,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import database as db


# ─────────────────────────────────────────────────────────────
#  Worker para no bloquear la UI mientras genera el Excel
# ─────────────────────────────────────────────────────────────

class ExportWorker(QThread):
    terminado = pyqtSignal(bool, str)   # (exito, ruta_o_error)

    def __init__(self, tipo: str, ruta: str, periodo: str = "historico"):
        super().__init__()
        self.tipo    = tipo
        self.ruta    = ruta
        self.periodo = periodo

    def run(self):
        try:
            import openpyxl
            from openpyxl.styles import (
                Font, PatternFill, Alignment, Border, Side
            )
            from openpyxl.utils import get_column_letter

            wb = openpyxl.Workbook()
            wb.remove(wb.active)   # quitar hoja vacía por defecto

            # Colores tema vinoteca
            COLOR_ENCABEZADO  = "722F37"   # burdeos
            COLOR_TOTAL       = "4A1520"   # burdeos oscuro
            COLOR_FILA_PAR    = "F5F0F1"   # rosa muy suave
            COLOR_TEXTO_BLANC = "FFFFFF"

            def _estilo_encabezado(cell):
                cell.font      = Font(bold=True, color=COLOR_TEXTO_BLANC, size=10)
                cell.fill      = PatternFill("solid", fgColor=COLOR_ENCABEZADO)
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border    = Border(
                    bottom=Side(style="thin", color="FFFFFF"),
                    right=Side(style="thin",  color="FFFFFF"),
                )

            def _estilo_total(cell):
                cell.font      = Font(bold=True, color=COLOR_TEXTO_BLANC, size=10)
                cell.fill      = PatternFill("solid", fgColor=COLOR_TOTAL)
                cell.alignment = Alignment(horizontal="right", vertical="center")

            def _auto_ancho(ws, min_w=8, max_w=50):
                for col_cells in ws.columns:
                    largo = max(
                        len(str(c.value)) if c.value is not None else 0
                        for c in col_cells
                    )
                    ws.column_dimensions[
                        get_column_letter(col_cells[0].column)
                    ].width = min(max(largo + 3, min_w), max_w)

            def _freeze(ws, cell="A2"):
                ws.freeze_panes = cell

            if self.tipo == "ventas_resumen":
                self._export_ventas_resumen(wb, _estilo_encabezado, _estilo_total,
                                            _auto_ancho, _freeze, COLOR_FILA_PAR)
            elif self.tipo == "ventas_detalle":
                self._export_ventas_detalle(wb, _estilo_encabezado, _estilo_total,
                                            _auto_ancho, _freeze, COLOR_FILA_PAR)
            elif self.tipo == "stock":
                self._export_stock(wb, _estilo_encabezado, _estilo_total,
                                   _auto_ancho, _freeze, COLOR_FILA_PAR)
            elif self.tipo == "proveedores":
                self._export_proveedores(wb, _estilo_encabezado, _estilo_total,
                                         _auto_ancho, _freeze, COLOR_FILA_PAR)
            elif self.tipo == "completo":
                self._export_ventas_resumen(wb, _estilo_encabezado, _estilo_total,
                                            _auto_ancho, _freeze, COLOR_FILA_PAR)
                self._export_ventas_detalle(wb, _estilo_encabezado, _estilo_total,
                                            _auto_ancho, _freeze, COLOR_FILA_PAR)
                self._export_stock(wb, _estilo_encabezado, _estilo_total,
                                   _auto_ancho, _freeze, COLOR_FILA_PAR)
                self._export_proveedores(wb, _estilo_encabezado, _estilo_total,
                                         _auto_ancho, _freeze, COLOR_FILA_PAR)

            wb.save(self.ruta)
            self.terminado.emit(True, self.ruta)

        except Exception as e:
            self.terminado.emit(False, str(e))

    # ── Helpers de período ─────────────────────────────────────

    def _rango_fechas(self):
        """Devuelve (desde, hasta) como strings 'YYYY-MM-DD' según self.periodo."""
        hoy = date.today()
        if self.periodo == "hoy":
            return str(hoy), str(hoy)
        elif self.periodo == "semana":
            from datetime import timedelta
            lunes = hoy - __import__("datetime").timedelta(days=hoy.weekday())
            return str(lunes), str(hoy)
        elif self.periodo == "mes":
            return f"{hoy.year}-{hoy.month:02d}-01", str(hoy)
        elif self.periodo == "anio":
            return f"{hoy.year}-01-01", str(hoy)
        else:  # historico
            return "2000-01-01", str(hoy)

    # ── Hoja: Ventas resumen por día ───────────────────────────

    def _export_ventas_resumen(self, wb, enc, tot, ancho, freeze, fila_par):
        from openpyxl.styles import PatternFill, Alignment, Font, numbers
        ws = wb.create_sheet("Ventas por día")
        freeze(ws)

        desde, hasta = self._rango_fechas()
        conn = db.get_connection()
        rows = conn.execute("""
            SELECT
                v.fecha,
                strftime('%d/%m/%Y', v.fecha)      AS fecha_fmt,
                COUNT(*)                            AS cant_ventas,
                SUM(v.total)                        AS total_dia,
                SUM(v.descuento)                    AS descuentos,
                SUM(CASE WHEN v.medio_pago='efectivo'      THEN v.total ELSE 0 END) AS efectivo,
                SUM(CASE WHEN v.medio_pago='debito'        THEN v.total ELSE 0 END) AS debito,
                SUM(CASE WHEN v.medio_pago='credito'       THEN v.total ELSE 0 END) AS credito,
                SUM(CASE WHEN v.medio_pago='transferencia' THEN v.total ELSE 0 END) AS transferencia,
                SUM(CASE WHEN v.medio_pago='qr'            THEN v.total ELSE 0 END) AS qr
            FROM ventas v
            WHERE v.anulada = 0 AND v.fecha BETWEEN ? AND ?
            GROUP BY v.fecha
            ORDER BY v.fecha
        """, (desde, hasta)).fetchall()
        conn.close()

        encabezados = ["Fecha", "N° Ventas", "Total del día", "Descuentos",
                       "Efectivo", "Débito", "Crédito", "Transferencia", "QR"]
        for col, h in enumerate(encabezados, 1):
            c = ws.cell(row=1, column=col, value=h)
            enc(c)
        ws.row_dimensions[1].height = 28

        total_acum = [0.0] * (len(encabezados) - 2)   # cols numéricas
        for r, row in enumerate(rows, 2):
            valores = [
                row["fecha_fmt"],
                row["cant_ventas"],
                row["total_dia"]       or 0,
                row["descuentos"]      or 0,
                row["efectivo"]        or 0,
                row["debito"]          or 0,
                row["credito"]         or 0,
                row["transferencia"]   or 0,
                row["qr"]              or 0,
            ]
            for i, n in enumerate(valores[2:]):
                total_acum[i] += n

            fill = PatternFill("solid", fgColor=fila_par) if r % 2 == 0 else None
            for col, val in enumerate(valores, 1):
                c = ws.cell(row=r, column=col, value=val)
                c.alignment = Alignment(horizontal="right" if col > 1 else "left",
                                        vertical="center")
                if col > 2:
                    c.number_format = '#,##0.00'
                if fill:
                    c.fill = fill

        # Fila TOTAL
        fila_tot = len(rows) + 2
        ws.cell(row=fila_tot, column=1, value="TOTAL")
        ws.cell(row=fila_tot, column=2, value=sum(r["cant_ventas"] for r in rows))
        for i, v in enumerate(total_acum):
            c = ws.cell(row=fila_tot, column=i + 3, value=v)
            c.number_format = '#,##0.00'
        for col in range(1, len(encabezados) + 1):
            tot(ws.cell(row=fila_tot, column=col))

        ancho(ws)

    # ── Hoja: Ventas detalle (ítem por ítem) ───────────────────

    def _export_ventas_detalle(self, wb, enc, tot, ancho, freeze, fila_par):
        from openpyxl.styles import PatternFill, Alignment
        ws = wb.create_sheet("Ventas detalle")
        freeze(ws)

        desde, hasta = self._rango_fechas()
        conn = db.get_connection()
        rows = conn.execute("""
            SELECT
                strftime('%d/%m/%Y', v.fecha) AS fecha,
                v.hora,
                v.id                           AS n_venta,
                v.medio_pago,
                p.nombre                       AS producto,
                c.nombre                       AS categoria,
                dv.cantidad,
                dv.precio_unit,
                dv.subtotal,
                dv.descuento,
                v.total                        AS total_venta,
                v.notas
            FROM ventas v
            JOIN detalle_ventas dv ON dv.venta_id = v.id
            JOIN productos p       ON p.id = dv.producto_id
            LEFT JOIN categorias c ON c.id = p.categoria_id
            WHERE v.anulada = 0 AND v.fecha BETWEEN ? AND ?
            ORDER BY v.fecha, v.id, p.nombre
        """, (desde, hasta)).fetchall()
        conn.close()

        encabezados = ["Fecha", "Hora", "N° Venta", "Medio pago",
                       "Producto", "Categoría", "Cantidad",
                       "Precio unit.", "Subtotal ítem", "Descuento ítem",
                       "Total venta", "Notas"]
        for col, h in enumerate(encabezados, 1):
            c = ws.cell(row=1, column=col, value=h)
            enc(c)
        ws.row_dimensions[1].height = 28

        nums = {7, 8, 9, 10, 11}
        for r, row in enumerate(rows, 2):
            vals = [
                row["fecha"], row["hora"], row["n_venta"], row["medio_pago"],
                row["producto"], row["categoria"], row["cantidad"],
                row["precio_unit"], row["subtotal"], row["descuento"],
                row["total_venta"], row["notas"] or "",
            ]
            fill = PatternFill("solid", fgColor=fila_par) if r % 2 == 0 else None
            for col, val in enumerate(vals, 1):
                c = ws.cell(row=r, column=col, value=val)
                c.alignment = Alignment(horizontal="right" if col in nums else "left",
                                        vertical="center")
                if col in nums:
                    c.number_format = '#,##0.00'
                if fill:
                    c.fill = fill

        ancho(ws)

    # ── Hoja: Stock actual ─────────────────────────────────────

    def _export_stock(self, wb, enc, tot, ancho, freeze, fila_par):
        from openpyxl.styles import PatternFill, Alignment, Font
        ws = wb.create_sheet("Stock actual")
        freeze(ws)

        conn = db.get_connection()
        rows = conn.execute("""
            SELECT
                p.nombre,
                c.nombre           AS categoria,
                pr.nombre          AS proveedor,
                p.codigo_barras,
                p.precio_venta,
                p.precio_costo,
                p.stock_actual,
                p.stock_minimo,
                p.unidad,
                CASE WHEN p.stock_actual <= p.stock_minimo THEN 'BAJO' ELSE 'OK' END AS alerta
            FROM productos p
            LEFT JOIN categorias c  ON c.id  = p.categoria_id
            LEFT JOIN proveedores pr ON pr.id = p.proveedor_id
            WHERE p.activo = 1
            ORDER BY c.nombre, p.nombre
        """).fetchall()
        conn.close()

        encabezados = ["Producto", "Categoría", "Proveedor", "Cód. barras",
                       "Precio venta", "Precio costo", "Stock actual",
                       "Stock mínimo", "Unidad", "Alerta"]
        for col, h in enumerate(encabezados, 1):
            c = ws.cell(row=1, column=col, value=h)
            enc(c)
        ws.row_dimensions[1].height = 28

        nums = {5, 6, 7, 8}
        for r, row in enumerate(rows, 2):
            vals = [
                row["nombre"], row["categoria"] or "", row["proveedor"] or "",
                row["codigo_barras"] or "", row["precio_venta"], row["precio_costo"],
                row["stock_actual"], row["stock_minimo"], row["unidad"],
                row["alerta"],
            ]
            alerta_bajo = row["alerta"] == "BAJO"
            fill = PatternFill("solid", fgColor="FFD7D7") if alerta_bajo \
                   else PatternFill("solid", fgColor=fila_par) if r % 2 == 0 \
                   else None
            for col, val in enumerate(vals, 1):
                c = ws.cell(row=r, column=col, value=val)
                c.alignment = Alignment(horizontal="right" if col in nums else "left",
                                        vertical="center")
                if col in {5, 6}:
                    c.number_format = '#,##0.00'
                if fill:
                    c.fill = fill
                if col == 10 and alerta_bajo:
                    c.font = Font(bold=True, color="CC0000")

        ancho(ws)

    # ── Hoja: Cuentas proveedores ──────────────────────────────

    def _export_proveedores(self, wb, enc, tot, ancho, freeze, fila_par):
        from openpyxl.styles import PatternFill, Alignment, Font
        ws = wb.create_sheet("Cuentas proveedores")
        freeze(ws)

        conn = db.get_connection()
        rows = conn.execute("""
            SELECT
                pr.nombre                              AS proveedor,
                f.numero_factura                       AS nro_factura,
                f.descripcion,
                strftime('%d/%m/%Y', f.fecha_emision)    AS f_emision,
                strftime('%d/%m/%Y', f.fecha_vencimiento) AS f_vencimiento,
                f.estado,
                f.monto_total,
                f.monto_pagado,
                (f.monto_total - f.monto_pagado)       AS saldo,
                f.notas
            FROM facturas_proveedores f
            JOIN proveedores pr ON pr.id = f.proveedor_id
            ORDER BY pr.nombre, f.fecha_emision DESC
        """).fetchall()
        conn.close()

        encabezados = ["Proveedor", "N° Factura", "Descripción",
                       "F. Emisión", "F. Vencimiento", "Estado",
                       "Total", "Pagado", "Saldo", "Notas"]
        for col, h in enumerate(encabezados, 1):
            c = ws.cell(row=1, column=col, value=h)
            enc(c)
        ws.row_dimensions[1].height = 28

        nums = {7, 8, 9}
        for r, row in enumerate(rows, 2):
            vals = [
                row["proveedor"], row["nro_factura"] or "", row["descripcion"] or "",
                row["f_emision"], row["f_vencimiento"], row["estado"],
                row["monto_total"], row["monto_pagado"], row["saldo"],
                row["notas"] or "",
            ]
            saldo_pendiente = row["saldo"] > 0.01 and row["estado"] != "pagada"
            fill = PatternFill("solid", fgColor="FFD7D7") if saldo_pendiente \
                   else PatternFill("solid", fgColor=fila_par) if r % 2 == 0 \
                   else None
            for col, val in enumerate(vals, 1):
                c = ws.cell(row=r, column=col, value=val)
                c.alignment = Alignment(horizontal="right" if col in nums else "left",
                                        vertical="center")
                if col in nums:
                    c.number_format = '#,##0.00'
                if fill:
                    c.fill = fill

        # Totales
        if rows:
            fila_tot = len(rows) + 2
            ws.cell(row=fila_tot, column=1, value="TOTALES")
            for i, col in enumerate([7, 8, 9]):
                c = ws.cell(row=fila_tot, column=col,
                            value=sum(r[col - 1] for r in
                                      [list(dict(row).values()) for row in rows]))
                c.number_format = '#,##0.00'
                tot(c)
            tot(ws.cell(row=fila_tot, column=1))

        ancho(ws)


# ─────────────────────────────────────────────────────────────
#  Panel principal de exportación
# ─────────────────────────────────────────────────────────────

class ExportarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # ── Scroll ────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(32, 28, 32, 32)
        lay.setSpacing(20)
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        # ── Título ────────────────────────────────────────────
        titulo = QLabel("📂  Exportar datos a Excel")
        titulo.setStyleSheet(
            "font-size:18px; font-weight:700; color:#C9A84C; padding-bottom:4px;")
        lay.addWidget(titulo)

        subtitulo = QLabel(
            "Descargá tus datos en formato Excel (.xlsx) cuando quieras.\n"
            "Tus registros de ventas, stock y cuentas siempre disponibles."
        )
        subtitulo.setStyleSheet("color:#AAAAAA; font-size:10pt;")
        lay.addWidget(subtitulo)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#333; margin: 4px 0;")
        lay.addWidget(sep)

        # ── Card: Ventas ──────────────────────────────────────
        lay.addWidget(self._card(
            titulo="🛒  Ventas",
            descripcion=(
                "Resumen diario (fecha, total, medio de pago, cantidad de ventas).\n"
                "Ideal para comparar con el registro histórico de Excel."
            ),
            tipo_resumen="ventas_resumen",
            tipo_detalle="ventas_detalle",
            con_periodo=True,
        ))

        # ── Card: Stock ───────────────────────────────────────
        lay.addWidget(self._card(
            titulo="📦  Stock actual",
            descripcion=(
                "Todos los productos activos con precios, stock actual,\n"
                "stock mínimo y alerta de reposición."
            ),
            tipo_resumen="stock",
            con_periodo=False,
        ))

        # ── Card: Cuentas proveedores ─────────────────────────
        lay.addWidget(self._card(
            titulo="🧾  Cuentas proveedores",
            descripcion=(
                "Todas las facturas de proveedores: vencimientos, estado,\n"
                "montos totales, pagados y saldo pendiente."
            ),
            tipo_resumen="proveedores",
            con_periodo=False,
        ))

        # ── Card: Exportación completa ────────────────────────
        lay.addWidget(self._card_completo())

        lay.addStretch()

    # ── Construcción de cards ──────────────────────────────────

    def _card(self, titulo, descripcion, tipo_resumen,
              tipo_detalle=None, con_periodo=False):
        frame = QFrame()
        frame.setObjectName("card_export")
        frame.setStyleSheet(
            "#card_export {"
            "  background:#1E1E1E; border:1px solid #333;"
            "  border-radius:8px; padding:16px;"
            "}"
        )
        lay = QVBoxLayout(frame)
        lay.setSpacing(10)

        lbl_tit = QLabel(titulo)
        lbl_tit.setStyleSheet("font-size:13px; font-weight:700; color:#DDDDDD;")
        lay.addWidget(lbl_tit)

        lbl_desc = QLabel(descripcion)
        lbl_desc.setStyleSheet("color:#888888; font-size:9pt;")
        lay.addWidget(lbl_desc)

        # Fila inferior: periodo (opcional) + botones
        fila = QHBoxLayout()
        fila.setSpacing(10)

        periodo_combo = None
        if con_periodo:
            periodo_combo = QComboBox()
            periodo_combo.addItems(["Histórico completo", "Este año",
                                    "Este mes", "Hoy"])
            periodo_combo.setFixedWidth(200)
            fila.addWidget(periodo_combo)

        fila.addStretch()

        # Botón resumen
        lbl_btn1 = "📊  Descargar resumen" if tipo_detalle else "📥  Descargar Excel"
        btn1 = QPushButton(lbl_btn1)
        btn1.setObjectName("btn_secundario")
        btn1.setFixedHeight(34)
        btn1.setMinimumWidth(180)
        btn1.clicked.connect(
            lambda _, t=tipo_resumen, pc=periodo_combo: self._exportar(t, pc)
        )
        fila.addWidget(btn1)

        if tipo_detalle:
            btn2 = QPushButton("📋  Descargar detalle")
            btn2.setObjectName("btn_secundario")
            btn2.setFixedHeight(34)
            btn2.setMinimumWidth(180)
            btn2.clicked.connect(
                lambda _, t=tipo_detalle, pc=periodo_combo: self._exportar(t, pc)
            )
            fila.addWidget(btn2)

        lay.addLayout(fila)
        return frame

    def _card_completo(self):
        frame = QFrame()
        frame.setObjectName("card_export_full")
        frame.setStyleSheet(
            "#card_export_full {"
            "  background:#2C1A1D; border:1px solid #722F37;"
            "  border-radius:8px; padding:16px;"
            "}"
        )
        lay = QVBoxLayout(frame)
        lay.setSpacing(10)

        lbl_tit = QLabel("📦  Exportación completa")
        lbl_tit.setStyleSheet("font-size:13px; font-weight:700; color:#C9A84C;")
        lay.addWidget(lbl_tit)

        lbl_desc = QLabel(
            "Un solo archivo con todas las hojas: ventas (resumen y detalle),\n"
            "stock actual y cuentas de proveedores."
        )
        lbl_desc.setStyleSheet("color:#888888; font-size:9pt;")
        lay.addWidget(lbl_desc)

        fila = QHBoxLayout()
        fila.addStretch()
        btn = QPushButton("💾  Descargar todo")
        btn.setObjectName("btn_exito")
        btn.setFixedHeight(36)
        btn.setMinimumWidth(200)
        btn.clicked.connect(lambda: self._exportar("completo", None))
        fila.addWidget(btn)
        lay.addLayout(fila)
        return frame

    # ── Lógica de exportación ──────────────────────────────────

    def _exportar(self, tipo: str, combo_periodo):
        PERIODOS = {
            "Histórico completo": "historico",
            "Este año":           "anio",
            "Este mes":           "mes",
            "Hoy":                "hoy",
        }
        periodo = "historico"
        if combo_periodo is not None:
            periodo = PERIODOS.get(combo_periodo.currentText(), "historico")

        NOMBRES = {
            "ventas_resumen": "ventas_resumen",
            "ventas_detalle": "ventas_detalle",
            "stock":          "stock_actual",
            "proveedores":    "cuentas_proveedores",
            "completo":       "vinoteca_completo",
        }
        hoy = datetime.today().strftime("%Y%m%d")
        nombre_ini = f"{NOMBRES[tipo]}_{hoy}.xlsx"

        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar Excel", nombre_ini,
            "Excel (*.xlsx)"
        )
        if not ruta:
            return

        self._worker = ExportWorker(tipo, ruta, periodo)
        self._worker.terminado.connect(self._on_terminado)
        self._worker.start()

    def _on_terminado(self, exito: bool, ruta_o_error: str):
        if exito:
            QMessageBox.information(
                self, "¡Listo!",
                f"✅  Archivo guardado correctamente:\n{ruta_o_error}"
            )
        else:
            QMessageBox.critical(
                self, "Error al exportar",
                f"No se pudo generar el archivo:\n{ruta_o_error}"
            )
