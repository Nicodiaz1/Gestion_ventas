# ─────────────────────────────────────────────────────────────
#  sync/sync_manager.py  –  Sincronización SQLite → SQL Server
# ─────────────────────────────────────────────────────────────

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import get_connection, set_config
from datetime import datetime


class SyncManager:
    """
    Sincroniza los datos locales (SQLite) con SQL Server.
    Diseño "offline-first": la app funciona siempre con SQLite.
    Este proceso sube los registros no sincronizados.
    """

    def __init__(self):
        self.conn_sql = None
        self._conectar()

    def _conectar(self):
        from db.database import get_config
        try:
            import pyodbc
            server   = get_config("sql_server", "")
            database = get_config("sql_database", "vinoteca")
            username = get_config("sql_username", "")
            password = get_config("sql_password", "")

            if not server:
                raise ValueError("SQL Server no configurado. Configuralo en ⚙️ Configuración.")

            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server};DATABASE={database};"
                f"UID={username};PWD={password};Encrypt=no"
            )
            self.conn_sql = pyodbc.connect(conn_str, timeout=10)
            self._crear_tablas_sql()
        except ImportError:
            raise RuntimeError("pyodbc no instalado. Ejecutá: pip install pyodbc")

    def _crear_tablas_sql(self):
        """Crea las tablas en SQL Server si no existen."""
        cursor = self.conn_sql.cursor()

        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='categorias' AND xtype='U')
        CREATE TABLE categorias (
            id INT PRIMARY KEY, nombre NVARCHAR(100), descripcion NVARCHAR(500)
        )""")

        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='productos' AND xtype='U')
        CREATE TABLE productos (
            id INT PRIMARY KEY, codigo_barras NVARCHAR(100),
            nombre NVARCHAR(255) NOT NULL, descripcion NVARCHAR(500),
            categoria_id INT, precio_venta FLOAT, precio_costo FLOAT,
            stock_actual INT, stock_minimo INT, unidad NVARCHAR(50),
            sin_codigo BIT DEFAULT 0, activo BIT DEFAULT 1,
            creado_en DATETIME, modificado_en DATETIME
        )""")

        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='ventas' AND xtype='U')
        CREATE TABLE ventas (
            id INT PRIMARY KEY, fecha DATE, hora TIME, datetime_venta DATETIME,
            subtotal FLOAT, descuento FLOAT, total FLOAT,
            medio_pago NVARCHAR(50), cuotas INT, notas NVARCHAR(500),
            anulada BIT DEFAULT 0, motivo_anulacion NVARCHAR(500)
        )""")

        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='detalle_ventas' AND xtype='U')
        CREATE TABLE detalle_ventas (
            id INT PRIMARY KEY, venta_id INT, producto_id INT,
            cantidad INT, precio_unit FLOAT, subtotal FLOAT, descuento FLOAT
        )""")

        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='stock_movimientos' AND xtype='U')
        CREATE TABLE stock_movimientos (
            id INT PRIMARY KEY, producto_id INT, tipo NVARCHAR(50),
            cantidad INT, stock_anterior INT, stock_nuevo INT,
            motivo NVARCHAR(500), referencia_id INT, fecha DATETIME
        )""")

        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='caja_diaria' AND xtype='U')
        CREATE TABLE caja_diaria (
            id INT PRIMARY KEY, fecha DATE, efectivo FLOAT, debito FLOAT,
            credito FLOAT, transferencia FLOAT, qr FLOAT, total FLOAT,
            cantidad_ventas INT, ticket_promedio FLOAT, cerrada BIT
        )""")

        self.conn_sql.commit()

    def sincronizar(self):
        """Sincroniza todos los registros pendientes."""
        stats = {"ventas": 0, "productos": 0, "movimientos": 0, "caja": 0}

        with get_connection() as sqlite_conn:
            # ── Productos ──────────────────────────────────────
            productos = sqlite_conn.execute(
                "SELECT * FROM productos"
            ).fetchall()
            cursor = self.conn_sql.cursor()
            for p in productos:
                cursor.execute("""
                    MERGE productos AS target
                    USING (VALUES (?,?,?,?,?,?,?,?,?,?,?,?)) AS source
                        (id, codigo_barras, nombre, descripcion, categoria_id,
                         precio_venta, precio_costo, stock_actual, stock_minimo,
                         unidad, sin_codigo, activo)
                    ON target.id = source.id
                    WHEN MATCHED THEN UPDATE SET
                        codigo_barras=source.codigo_barras, nombre=source.nombre,
                        precio_venta=source.precio_venta, precio_costo=source.precio_costo,
                        stock_actual=source.stock_actual, activo=source.activo
                    WHEN NOT MATCHED THEN INSERT
                        (id, codigo_barras, nombre, descripcion, categoria_id,
                         precio_venta, precio_costo, stock_actual, stock_minimo,
                         unidad, sin_codigo, activo)
                    VALUES (source.id, source.codigo_barras, source.nombre,
                            source.descripcion, source.categoria_id,
                            source.precio_venta, source.precio_costo,
                            source.stock_actual, source.stock_minimo,
                            source.unidad, source.sin_codigo, source.activo);
                """, (p["id"], p["codigo_barras"], p["nombre"], p["descripcion"],
                      p["categoria_id"], p["precio_venta"], p["precio_costo"],
                      p["stock_actual"], p["stock_minimo"], p["unidad"],
                      p["sin_codigo"], p["activo"]))
                stats["productos"] += 1

            # ── Ventas no sincronizadas ────────────────────────
            ventas = sqlite_conn.execute(
                "SELECT * FROM ventas WHERE sincronizada = 0"
            ).fetchall()
            for v in ventas:
                try:
                    cursor.execute("""
                        INSERT INTO ventas
                        (id, fecha, hora, datetime_venta, subtotal, descuento, total,
                         medio_pago, cuotas, notas, anulada)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """, (v["id"], v["fecha"], v["hora"], v["datetime_venta"],
                          v["subtotal"], v["descuento"], v["total"],
                          v["medio_pago"], v["cuotas"], v["notas"], v["anulada"]))
                except Exception:
                    pass  # ya existe

                # Detalle
                detalles = sqlite_conn.execute(
                    "SELECT * FROM detalle_ventas WHERE venta_id = ?", (v["id"],)
                ).fetchall()
                for d in detalles:
                    try:
                        cursor.execute("""
                            INSERT INTO detalle_ventas
                            (id, venta_id, producto_id, cantidad, precio_unit, subtotal, descuento)
                            VALUES (?,?,?,?,?,?,?)
                        """, (d["id"], d["venta_id"], d["producto_id"],
                              d["cantidad"], d["precio_unit"], d["subtotal"], d["descuento"]))
                    except Exception:
                        pass

                # Marcar como sincronizada en SQLite
                sqlite_conn.execute(
                    "UPDATE ventas SET sincronizada = 1 WHERE id = ?", (v["id"],))
                stats["ventas"] += 1

            # ── Movimientos de stock ───────────────────────────
            movs = sqlite_conn.execute(
                "SELECT * FROM stock_movimientos WHERE sincronizado = 0"
            ).fetchall()
            for m in movs:
                try:
                    cursor.execute("""
                        INSERT INTO stock_movimientos
                        (id, producto_id, tipo, cantidad, stock_anterior,
                         stock_nuevo, motivo, referencia_id, fecha)
                        VALUES (?,?,?,?,?,?,?,?,?)
                    """, (m["id"], m["producto_id"], m["tipo"], m["cantidad"],
                          m["stock_anterior"], m["stock_nuevo"],
                          m["motivo"], m["referencia_id"], m["fecha"]))
                    sqlite_conn.execute(
                        "UPDATE stock_movimientos SET sincronizado = 1 WHERE id = ?", (m["id"],))
                    stats["movimientos"] += 1
                except Exception:
                    pass

            # ── Caja diaria ────────────────────────────────────
            cajas = sqlite_conn.execute(
                "SELECT * FROM caja_diaria WHERE sincronizada = 0"
            ).fetchall()
            for c in cajas:
                try:
                    cursor.execute("""
                        MERGE caja_diaria AS target
                        USING (VALUES (?,?,?,?,?,?,?,?,?,?)) AS source
                            (id, fecha, efectivo, debito, credito,
                             transferencia, qr, total, cantidad_ventas, ticket_promedio)
                        ON target.fecha = source.fecha
                        WHEN MATCHED THEN UPDATE SET
                            efectivo=source.efectivo, debito=source.debito,
                            credito=source.credito, transferencia=source.transferencia,
                            qr=source.qr, total=source.total,
                            cantidad_ventas=source.cantidad_ventas
                        WHEN NOT MATCHED THEN INSERT
                            (id, fecha, efectivo, debito, credito, transferencia,
                             qr, total, cantidad_ventas, ticket_promedio)
                        VALUES (source.id, source.fecha, source.efectivo, source.debito,
                                source.credito, source.transferencia, source.qr,
                                source.total, source.cantidad_ventas, source.ticket_promedio);
                    """, (c["id"], c["fecha"], c["efectivo"], c["debito"],
                          c["credito"], c["transferencia"], c["qr"],
                          c["total"], c["cantidad_ventas"], c["ticket_promedio"]))
                    sqlite_conn.execute(
                        "UPDATE caja_diaria SET sincronizada = 1 WHERE id = ?", (c["id"],))
                    stats["caja"] += 1
                except Exception:
                    pass

            self.conn_sql.commit()
            set_config("ultima_sincronizacion", datetime.now().isoformat())

        self.conn_sql.close()
        msg = (f"Sincronización completada:\n"
               f"  • Ventas: {stats['ventas']}\n"
               f"  • Productos: {stats['productos']}\n"
               f"  • Movimientos: {stats['movimientos']}\n"
               f"  • Caja: {stats['caja']}")
        print(msg)
        return stats
