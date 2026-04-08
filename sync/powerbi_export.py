# ─────────────────────────────────────────────────────────────
#  sync/powerbi_export.py  –  Exportación de datasets para Power BI
# ─────────────────────────────────────────────────────────────

import os, sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import get_connection
from config import EXPORTS_DIR


def exportar_todos():
    """
    Genera todos los datasets CSV necesarios para conectar Power BI.
    Guardar en /exports/powerbi/
    """
    try:
        import pandas as pd
    except ImportError:
        raise RuntimeError("pandas no instalado. Ejecutá: pip install pandas")

    out_dir = os.path.join(EXPORTS_DIR, "powerbi")
    os.makedirs(out_dir, exist_ok=True)

    with get_connection() as conn:
        # ── 1. Ventas completas ────────────────────────────────
        df_ventas = pd.read_sql_query("""
            SELECT v.id, v.fecha, v.hora, v.datetime_venta,
                   v.subtotal, v.descuento, v.total,
                   v.medio_pago, v.cuotas, v.anulada,
                   strftime('%Y', v.fecha) as anio,
                   strftime('%m', v.fecha) as mes,
                   strftime('%W', v.fecha) as semana,
                   strftime('%u', v.fecha) as dia_semana
            FROM ventas v WHERE v.anulada = 0
        """, conn)
        df_ventas.to_csv(os.path.join(out_dir, "ventas.csv"), index=False, encoding="utf-8-sig")

        # ── 2. Detalle de ventas con producto ──────────────────
        df_detalle = pd.read_sql_query("""
            SELECT dv.id, dv.venta_id, dv.cantidad, dv.precio_unit, dv.subtotal,
                   p.id as producto_id, p.nombre as producto,
                   p.codigo_barras, p.precio_costo,
                   (dv.precio_unit - p.precio_costo) * dv.cantidad as margen_bruto,
                   c.nombre as categoria,
                   v.fecha, v.medio_pago,
                   strftime('%Y', v.fecha) as anio,
                   strftime('%m', v.fecha) as mes
            FROM detalle_ventas dv
            JOIN productos p ON p.id = dv.producto_id
            JOIN ventas v ON v.id = dv.venta_id AND v.anulada = 0
            LEFT JOIN categorias c ON c.id = p.categoria_id
        """, conn)
        df_detalle.to_csv(os.path.join(out_dir, "detalle_ventas.csv"), index=False, encoding="utf-8-sig")

        # ── 3. Productos y stock actual ────────────────────────
        df_productos = pd.read_sql_query("""
            SELECT p.id, p.codigo_barras, p.nombre, p.descripcion,
                   p.precio_venta, p.precio_costo, p.stock_actual, p.stock_minimo,
                   p.unidad, p.sin_codigo, p.activo,
                   c.nombre as categoria,
                   pr.nombre as proveedor,
                   (p.precio_venta - p.precio_costo) as margen_unitario,
                   CASE WHEN p.precio_venta > 0
                        THEN ROUND((p.precio_venta - p.precio_costo) / p.precio_venta * 100, 2)
                        ELSE 0 END as margen_porcentaje
            FROM productos p
            LEFT JOIN categorias c ON c.id = p.categoria_id
            LEFT JOIN proveedores pr ON pr.id = p.proveedor_id
            WHERE p.activo = 1
        """, conn)
        df_productos.to_csv(os.path.join(out_dir, "productos.csv"), index=False, encoding="utf-8-sig")

        # ── 4. Caja diaria ────────────────────────────────────
        df_caja = pd.read_sql_query("""
            SELECT *, strftime('%Y', fecha) as anio, strftime('%m', fecha) as mes
            FROM caja_diaria ORDER BY fecha
        """, conn)
        df_caja.to_csv(os.path.join(out_dir, "caja_diaria.csv"), index=False, encoding="utf-8-sig")

        # ── 5. Resumen mensual ────────────────────────────────
        df_mensual = pd.read_sql_query("""
            SELECT strftime('%Y-%m', fecha) as periodo,
                   SUM(total) as total_ventas,
                   COUNT(*) as cantidad_ventas,
                   AVG(total) as ticket_promedio,
                   SUM(CASE WHEN medio_pago='efectivo' THEN total ELSE 0 END) as efectivo,
                   SUM(CASE WHEN medio_pago='debito'   THEN total ELSE 0 END) as debito,
                   SUM(CASE WHEN medio_pago='credito'  THEN total ELSE 0 END) as credito,
                   SUM(CASE WHEN medio_pago='transferencia' THEN total ELSE 0 END) as transferencia,
                   SUM(CASE WHEN medio_pago='qr'       THEN total ELSE 0 END) as qr
            FROM ventas WHERE anulada = 0
            GROUP BY periodo ORDER BY periodo
        """, conn)
        df_mensual.to_csv(os.path.join(out_dir, "resumen_mensual.csv"), index=False, encoding="utf-8-sig")

        # ── 6. Top productos (últimos 12 meses) ──────────────
        df_top = pd.read_sql_query("""
            SELECT p.nombre, c.nombre as categoria,
                   SUM(dv.cantidad) as unidades_vendidas,
                   SUM(dv.subtotal) as ingresos_total,
                   SUM((dv.precio_unit - p.precio_costo) * dv.cantidad) as margen_total,
                   COUNT(DISTINCT v.id) as veces_en_venta,
                   MAX(v.fecha) as ultima_venta
            FROM detalle_ventas dv
            JOIN productos p ON p.id = dv.producto_id
            JOIN ventas v ON v.id = dv.venta_id AND v.anulada = 0
            LEFT JOIN categorias c ON c.id = p.categoria_id
            WHERE v.fecha >= date('now', '-365 days')
            GROUP BY p.id ORDER BY unidades_vendidas DESC
        """, conn)
        df_top.to_csv(os.path.join(out_dir, "top_productos.csv"), index=False, encoding="utf-8-sig")

        # ── 7. Productos sin rotación ─────────────────────────
        df_sin_rot = pd.read_sql_query("""
            SELECT p.nombre, c.nombre as categoria,
                   p.stock_actual, p.precio_venta, p.precio_costo,
                   MAX(v.fecha) as ultima_venta,
                   julianday('now') - julianday(COALESCE(MAX(v.fecha), p.creado_en)) as dias_sin_venta
            FROM productos p
            LEFT JOIN detalle_ventas dv ON dv.producto_id = p.id
            LEFT JOIN ventas v ON v.id = dv.venta_id AND v.anulada = 0
            LEFT JOIN categorias c ON c.id = p.categoria_id
            WHERE p.activo = 1
            GROUP BY p.id
            HAVING dias_sin_venta > 30
            ORDER BY dias_sin_venta DESC
        """, conn)
        df_sin_rot.to_csv(os.path.join(out_dir, "sin_rotacion.csv"), index=False, encoding="utf-8-sig")

        # ── 8. Movimientos de stock ───────────────────────────
        df_movs = pd.read_sql_query("""
            SELECT sm.*, p.nombre as producto, c.nombre as categoria
            FROM stock_movimientos sm
            JOIN productos p ON p.id = sm.producto_id
            LEFT JOIN categorias c ON c.id = p.categoria_id
            ORDER BY sm.fecha DESC
        """, conn)
        df_movs.to_csv(os.path.join(out_dir, "movimientos_stock.csv"), index=False, encoding="utf-8-sig")

    # ── Generar archivo de instrucciones ──────────────────────
    readme = os.path.join(out_dir, "POWER_BI_INSTRUCCIONES.txt")
    with open(readme, "w", encoding="utf-8") as f:
        f.write("""INSTRUCCIONES PARA CONECTAR POWER BI
=====================================

1. Abrir Power BI Desktop
2. Inicio → Obtener datos → Texto/CSV
3. Seleccionar cada archivo CSV de esta carpeta:

   • ventas.csv          → Tabla maestra de ventas
   • detalle_ventas.csv  → Ítems por venta (con margen)
   • productos.csv       → Catálogo y stock actual
   • caja_diaria.csv     → Cierre de caja por día
   • resumen_mensual.csv → Totales por mes y medio de pago
   • top_productos.csv   → Ranking de productos más vendidos
   • sin_rotacion.csv    → Productos sin ventas (30+ días)
   • movimientos_stock.csv → Historial de entradas y salidas

4. En el Editor de Power Query:
   - Columna "fecha": cambiar tipo → Fecha
   - Columnas de monto: cambiar tipo → Número decimal

5. Relaciones sugeridas:
   ventas[id]        → detalle_ventas[venta_id]
   productos[id]     → detalle_ventas[producto_id]
   productos[id]     → movimientos_stock[producto_id]

6. Métricas DAX sugeridas:
   Total Ventas = SUM(ventas[total])
   Ticket Prom  = AVERAGE(ventas[total])
   Margen Bruto = SUM(detalle_ventas[margen_bruto])
   % Margen     = DIVIDE([Margen Bruto], SUM(detalle_ventas[subtotal]))

Exportar regularmente desde la app (Reportes → Exportar a Excel)
o configurar sincronización automática con SQL Server.
""")

    archivos = [f for f in os.listdir(out_dir) if f.endswith(".csv")]
    return out_dir, archivos


if __name__ == "__main__":
    directorio, archivos = exportar_todos()
    print(f"\n✅  Exportados {len(archivos)} archivos en: {directorio}")
    for a in archivos:
        print(f"  → {a}")
