# ─────────────────────────────────────────────────────────────
#  db/database.py  –  Capa de acceso a datos (SQLite local)
# ─────────────────────────────────────────────────────────────

import sqlite3
import os
from datetime import datetime, date
from typing import Optional
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH


# ── Conexión ──────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


# ── Inicialización del esquema ────────────────────────────────

SCHEMA = """
-- ── Categorías de producto ──────────────────────────────────
CREATE TABLE IF NOT EXISTS categorias (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT    NOT NULL UNIQUE,
    descripcion TEXT
);

-- ── Proveedores ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS proveedores (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre    TEXT NOT NULL,
    telefono  TEXT,
    email     TEXT,
    notas     TEXT,
    activo    INTEGER DEFAULT 1,
    creado_en DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ── Productos ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS productos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_barras   TEXT UNIQUE,          -- NULL para productos sin código
    nombre          TEXT NOT NULL,
    descripcion     TEXT,
    categoria_id    INTEGER REFERENCES categorias(id),
    proveedor_id    INTEGER REFERENCES proveedores(id),
    precio_venta    REAL NOT NULL DEFAULT 0,
    precio_costo    REAL DEFAULT 0,
    stock_actual    INTEGER NOT NULL DEFAULT 0,
    stock_minimo    INTEGER DEFAULT 3,
    unidad          TEXT DEFAULT 'unidad', -- unidad, caja, botella, etc.
    unidades_por_caja INTEGER DEFAULT 1,  -- cuántas unidades trae una caja
    activo          INTEGER DEFAULT 1,
    sin_codigo      INTEGER DEFAULT 0,    -- 1 = producto sin código de barras
    imagen_path     TEXT,
    creado_en       DATETIME DEFAULT CURRENT_TIMESTAMP,
    modificado_en   DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_productos_barras ON productos(codigo_barras);
CREATE INDEX IF NOT EXISTS idx_productos_nombre ON productos(nombre);

-- ── Ventas (cabecera) ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ventas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha           DATE    NOT NULL,
    hora            TIME    NOT NULL,
    datetime_venta  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    subtotal        REAL NOT NULL DEFAULT 0,
    descuento       REAL NOT NULL DEFAULT 0,
    total           REAL NOT NULL DEFAULT 0,
    medio_pago      TEXT NOT NULL,  -- efectivo|debito|credito|transferencia|qr
    cuotas          INTEGER DEFAULT 1,
    notas           TEXT,
    anulada         INTEGER DEFAULT 0,
    motivo_anulacion TEXT,
    sincronizada    INTEGER DEFAULT 0,
    creado_en       DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ventas_fecha     ON ventas(fecha);
CREATE INDEX IF NOT EXISTS idx_ventas_medio_pago ON ventas(medio_pago);

-- ── Detalle de ventas (ítems) ────────────────────────────────
CREATE TABLE IF NOT EXISTS detalle_ventas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id    INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    cantidad    INTEGER NOT NULL DEFAULT 1,
    precio_unit REAL    NOT NULL,
    subtotal    REAL    NOT NULL,
    descuento   REAL    DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_detalle_venta    ON detalle_ventas(venta_id);
CREATE INDEX IF NOT EXISTS idx_detalle_producto ON detalle_ventas(producto_id);

-- ── Movimientos de stock ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS stock_movimientos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    tipo        TEXT NOT NULL,   -- entrada|salida|ajuste|devolucion
    cantidad    INTEGER NOT NULL,
    stock_anterior INTEGER,
    stock_nuevo    INTEGER,
    motivo      TEXT,
    referencia_id  INTEGER,      -- venta_id si es salida por venta
    fecha       DATETIME DEFAULT CURRENT_TIMESTAMP,
    sincronizado INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_movimientos_producto ON stock_movimientos(producto_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_fecha    ON stock_movimientos(fecha);

-- ── Cierre de caja diario ────────────────────────────────────
CREATE TABLE IF NOT EXISTS caja_diaria (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha           DATE UNIQUE NOT NULL,
    efectivo        REAL DEFAULT 0,
    debito          REAL DEFAULT 0,
    credito         REAL DEFAULT 0,
    transferencia   REAL DEFAULT 0,
    qr              REAL DEFAULT 0,
    total           REAL DEFAULT 0,
    cantidad_ventas INTEGER DEFAULT 0,
    ticket_promedio REAL DEFAULT 0,
    cerrada         INTEGER DEFAULT 0,
    notas           TEXT,
    sincronizada    INTEGER DEFAULT 0
);

-- ── Configuración de la app ──────────────────────────────────
CREATE TABLE IF NOT EXISTS configuracion (
    clave   TEXT PRIMARY KEY,
    valor   TEXT,
    tipo    TEXT DEFAULT 'string'   -- string|int|float|bool
);

-- ── Insertar datos por defecto ───────────────────────────────
INSERT OR IGNORE INTO categorias (nombre) VALUES
    ('Vinos Tintos'),
    ('Vinos Blancos'),
    ('Vinos Rosados'),
    ('Espumantes'),
    ('Cervezas'),
    ('Licores y Spirits'),
    ('Sin Alcohol'),
    ('Snacks y Accesorios'),
    ('Otros');

INSERT OR IGNORE INTO configuracion (clave, valor, tipo) VALUES
    ('nombre_negocio', 'La Vinoteca', 'string'),
    ('moneda', '$', 'string'),
    ('stock_min_alerta', '3', 'int'),
    ('iva_porcentaje', '21', 'float'),
    ('ultima_sincronizacion', '', 'string');
"""


def init_db():
    """Crea todas las tablas si no existen."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        # ── Migraciones para bases de datos existentes ────────
        columnas = [r[1] for r in conn.execute("PRAGMA table_info(productos)").fetchall()]
        if "unidades_por_caja" not in columnas:
            conn.execute("ALTER TABLE productos ADD COLUMN unidades_por_caja INTEGER DEFAULT 1")
            print("[DB] Migración: columna unidades_por_caja agregada.")
    print(f"[DB] Base de datos inicializada en: {DB_PATH}")


# ══════════════════════════════════════════════════════════════
#  PRODUCTOS
# ══════════════════════════════════════════════════════════════

def buscar_por_codigo(codigo_barras: str) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM productos WHERE codigo_barras = ? AND activo = 1",
            (codigo_barras,)
        ).fetchone()


def buscar_por_nombre(texto: str) -> list:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM productos WHERE nombre LIKE ? AND activo = 1 ORDER BY nombre LIMIT 20",
            (f"%{texto}%",)
        ).fetchall()


def obtener_producto(producto_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT p.*, c.nombre as categoria_nombre FROM productos p "
            "LEFT JOIN categorias c ON p.categoria_id = c.id WHERE p.id = ?",
            (producto_id,)
        ).fetchone()


def obtener_todos_productos(solo_activos=True) -> list:
    with get_connection() as conn:
        q = "SELECT p.*, c.nombre as categoria_nombre FROM productos p LEFT JOIN categorias c ON p.categoria_id = c.id"
        if solo_activos:
            q += " WHERE p.activo = 1"
        q += " ORDER BY p.nombre"
        return conn.execute(q).fetchall()


def crear_producto(datos: dict) -> int:
    campos = ["codigo_barras", "nombre", "descripcion", "categoria_id", "proveedor_id",
              "precio_venta", "precio_costo", "stock_actual", "stock_minimo",
              "unidad", "unidades_por_caja", "sin_codigo", "imagen_path"]
    keys = [c for c in campos if c in datos]
    placeholders = ", ".join("?" for _ in keys)
    cols = ", ".join(keys)
    valores = [datos[k] for k in keys]
    with get_connection() as conn:
        cur = conn.execute(
            f"INSERT INTO productos ({cols}) VALUES ({placeholders})", valores)
        producto_id = cur.lastrowid
        if datos.get("stock_actual", 0) > 0:
            _registrar_movimiento_conn(conn, producto_id, "entrada",
                                       datos["stock_actual"], 0,
                                       datos["stock_actual"], "Stock inicial")
        return producto_id


def actualizar_producto(producto_id: int, datos: dict):
    datos["modificado_en"] = datetime.now().isoformat()
    sets = ", ".join(f"{k} = ?" for k in datos)
    valores = list(datos.values()) + [producto_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE productos SET {sets} WHERE id = ?", valores)


def eliminar_producto(producto_id: int):
    """Soft delete."""
    with get_connection() as conn:
        conn.execute("UPDATE productos SET activo = 0 WHERE id = ?", (producto_id,))


def productos_sin_rotacion(dias: int = 90) -> list:
    """Productos activos que no registran ventas en los últimos N días."""
    with get_connection() as conn:
        return conn.execute("""
            SELECT p.*, MAX(dv.subtotal) as ultima_venta_subtotal,
                   MAX(v.fecha) as ultima_venta_fecha
            FROM productos p
            LEFT JOIN detalle_ventas dv ON dv.producto_id = p.id
            LEFT JOIN ventas v ON v.id = dv.venta_id AND v.anulada = 0
            WHERE p.activo = 1
            GROUP BY p.id
            HAVING ultima_venta_fecha IS NULL
                OR ultima_venta_fecha < date('now', ?)
            ORDER BY ultima_venta_fecha ASC
        """, (f"-{dias} days",)).fetchall()


def productos_bajo_stock() -> list:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM productos WHERE activo = 1 AND stock_actual <= stock_minimo ORDER BY stock_actual ASC"
        ).fetchall()


def productos_para_restock() -> list:
    """Productos con stock_actual < stock_minimo, enriquecidos con proveedor y categoría."""
    with get_connection() as conn:
        return conn.execute("""
            SELECT p.*,
                   c.nombre   AS categoria_nombre,
                   pr.nombre  AS proveedor_nombre,
                   pr.telefono AS proveedor_telefono,
                   pr.email   AS proveedor_email,
                   (p.stock_minimo - p.stock_actual) AS faltante
            FROM productos p
            LEFT JOIN categorias  c  ON c.id  = p.categoria_id
            LEFT JOIN proveedores pr ON pr.id = p.proveedor_id
            WHERE p.activo = 1 AND p.stock_actual < p.stock_minimo
            ORDER BY COALESCE(pr.nombre, '') ASC, p.nombre ASC
        """).fetchall()


# ══════════════════════════════════════════════════════════════
#  STOCK
# ══════════════════════════════════════════════════════════════

def _registrar_movimiento_conn(conn, producto_id, tipo, cantidad,
                                stock_anterior, stock_nuevo, motivo="", ref_id=None):
    conn.execute("""
        INSERT INTO stock_movimientos
        (producto_id, tipo, cantidad, stock_anterior, stock_nuevo, motivo, referencia_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (producto_id, tipo, cantidad, stock_anterior, stock_nuevo, motivo, ref_id))


def agregar_stock(producto_id: int, cantidad: int, motivo: str = "Ingreso de mercadería") -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT stock_actual FROM productos WHERE id = ?", (producto_id,)).fetchone()
        if not row:
            raise ValueError(f"Producto {producto_id} no existe")
        stock_ant = row["stock_actual"]
        stock_nuevo = stock_ant + cantidad
        conn.execute("UPDATE productos SET stock_actual = ?, modificado_en = ? WHERE id = ?",
                     (stock_nuevo, datetime.now().isoformat(), producto_id))
        _registrar_movimiento_conn(conn, producto_id, "entrada", cantidad,
                                   stock_ant, stock_nuevo, motivo)
        return stock_nuevo


def ajustar_stock(producto_id: int, nuevo_stock: int, motivo: str = "Ajuste manual") -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT stock_actual FROM productos WHERE id = ?", (producto_id,)).fetchone()
        stock_ant = row["stock_actual"]
        diferencia = nuevo_stock - stock_ant
        conn.execute("UPDATE productos SET stock_actual = ?, modificado_en = ? WHERE id = ?",
                     (nuevo_stock, datetime.now().isoformat(), producto_id))
        _registrar_movimiento_conn(conn, producto_id, "ajuste", diferencia,
                                   stock_ant, nuevo_stock, motivo)
        return nuevo_stock


def historial_movimientos(producto_id: int = None, limite: int = 100) -> list:
    with get_connection() as conn:
        if producto_id:
            return conn.execute("""
                SELECT sm.*, p.nombre as producto_nombre
                FROM stock_movimientos sm JOIN productos p ON p.id = sm.producto_id
                WHERE sm.producto_id = ? ORDER BY sm.fecha DESC LIMIT ?
            """, (producto_id, limite)).fetchall()
        return conn.execute("""
            SELECT sm.*, p.nombre as producto_nombre
            FROM stock_movimientos sm JOIN productos p ON p.id = sm.producto_id
            ORDER BY sm.fecha DESC LIMIT ?
        """, (limite,)).fetchall()


# ══════════════════════════════════════════════════════════════
#  VENTAS
# ══════════════════════════════════════════════════════════════

def registrar_venta(items: list, medio_pago: str, descuento: float = 0,
                    cuotas: int = 1, notas: str = "") -> int:
    """
    items: [{"producto_id": int, "cantidad": int, "precio_unit": float}, ...]
    Retorna el ID de la venta creada.
    """
    ahora = datetime.now()
    subtotal = sum(i["cantidad"] * i["precio_unit"] for i in items)
    total = subtotal - descuento

    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO ventas (fecha, hora, datetime_venta, subtotal, descuento, total,
                                medio_pago, cuotas, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ahora.date().isoformat(), ahora.strftime("%H:%M:%S"),
              ahora.isoformat(), subtotal, descuento, total,
              medio_pago, cuotas, notas))
        venta_id = cur.lastrowid

        for item in items:
            sub_item = item["cantidad"] * item["precio_unit"]
            conn.execute("""
                INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, precio_unit, subtotal)
                VALUES (?, ?, ?, ?, ?)
            """, (venta_id, item["producto_id"], item["cantidad"],
                  item["precio_unit"], sub_item))

            # Descontar stock
            row = conn.execute("SELECT stock_actual FROM productos WHERE id = ?",
                               (item["producto_id"],)).fetchone()
            stock_ant = row["stock_actual"]
            stock_nuevo = max(0, stock_ant - item["cantidad"])
            conn.execute("UPDATE productos SET stock_actual = ?, modificado_en = ? WHERE id = ?",
                         (stock_nuevo, ahora.isoformat(), item["producto_id"]))
            _registrar_movimiento_conn(conn, item["producto_id"], "salida",
                                       item["cantidad"], stock_ant, stock_nuevo,
                                       "Venta", venta_id)

        # Actualizar caja diaria
        _actualizar_caja(conn, ahora.date().isoformat(), medio_pago, total)
        return venta_id


def _actualizar_caja(conn, fecha: str, medio_pago: str, total: float):
    col_map = {
        "efectivo": "efectivo", "debito": "debito",
        "credito": "credito", "transferencia": "transferencia", "qr": "qr"
    }
    col = col_map.get(medio_pago, "efectivo")
    conn.execute(f"""
        INSERT INTO caja_diaria (fecha, {col}, total, cantidad_ventas)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(fecha) DO UPDATE SET
            {col} = {col} + excluded.{col},
            total = total + excluded.total,
            cantidad_ventas = cantidad_ventas + 1,
            ticket_promedio = (total + excluded.total) / (cantidad_ventas + 1)
    """, (fecha, total, total))


def anular_venta(venta_id: int, motivo: str = ""):
    with get_connection() as conn:
        venta = conn.execute("SELECT * FROM ventas WHERE id = ?", (venta_id,)).fetchone()
        if not venta or venta["anulada"]:
            return False
        conn.execute("UPDATE ventas SET anulada = 1, motivo_anulacion = ? WHERE id = ?",
                     (motivo, venta_id))
        items = conn.execute("SELECT * FROM detalle_ventas WHERE venta_id = ?",
                             (venta_id,)).fetchall()
        for item in items:
            row = conn.execute("SELECT stock_actual FROM productos WHERE id = ?",
                               (item["producto_id"],)).fetchone()
            stock_ant = row["stock_actual"]
            stock_nuevo = stock_ant + item["cantidad"]
            conn.execute("UPDATE productos SET stock_actual = ? WHERE id = ?",
                         (stock_nuevo, item["producto_id"]))
            _registrar_movimiento_conn(conn, item["producto_id"], "devolucion",
                                       item["cantidad"], stock_ant, stock_nuevo,
                                       f"Anulación venta #{venta_id}", venta_id)
        # Restar de caja diaria
        fecha = venta["fecha"]
        mp = venta["medio_pago"]
        col_map = {"efectivo": "efectivo", "debito": "debito",
                   "credito": "credito", "transferencia": "transferencia", "qr": "qr"}
        col = col_map.get(mp, "efectivo")
        conn.execute(f"""
            UPDATE caja_diaria SET {col} = {col} - ?, total = total - ?,
            cantidad_ventas = MAX(0, cantidad_ventas - 1) WHERE fecha = ?
        """, (venta["total"], venta["total"], fecha))
        return True


def obtener_venta(venta_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM ventas WHERE id = ?", (venta_id,)).fetchone()


def detalle_venta(venta_id: int) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT dv.*, p.nombre, p.codigo_barras
            FROM detalle_ventas dv JOIN productos p ON p.id = dv.producto_id
            WHERE dv.venta_id = ?
        """, (venta_id,)).fetchall()


def ventas_del_dia(fecha: str = None) -> list:
    if not fecha:
        fecha = date.today().isoformat()
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM ventas WHERE fecha = ? AND anulada = 0 ORDER BY datetime_venta DESC",
            (fecha,)
        ).fetchall()


def ultimas_ventas(limite: int = 50) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT v.*, GROUP_CONCAT(p.nombre, ', ') as productos_nombres
            FROM ventas v
            LEFT JOIN detalle_ventas dv ON dv.venta_id = v.id
            LEFT JOIN productos p ON p.id = dv.producto_id
            WHERE v.anulada = 0
            GROUP BY v.id
            ORDER BY v.datetime_venta DESC LIMIT ?
        """, (limite,)).fetchall()


# ══════════════════════════════════════════════════════════════
#  REPORTES
# ══════════════════════════════════════════════════════════════

def reporte_ventas_por_periodo(desde: str, hasta: str) -> dict:
    with get_connection() as conn:
        totales = conn.execute("""
            SELECT
                COUNT(*) as cantidad_ventas,
                SUM(total) as total_ventas,
                AVG(total) as ticket_promedio,
                SUM(CASE WHEN medio_pago='efectivo' THEN total ELSE 0 END) as efectivo,
                SUM(CASE WHEN medio_pago='debito'   THEN total ELSE 0 END) as debito,
                SUM(CASE WHEN medio_pago='credito'  THEN total ELSE 0 END) as credito,
                SUM(CASE WHEN medio_pago='transferencia' THEN total ELSE 0 END) as transferencia,
                SUM(CASE WHEN medio_pago='qr'       THEN total ELSE 0 END) as qr
            FROM ventas WHERE fecha BETWEEN ? AND ? AND anulada = 0
        """, (desde, hasta)).fetchone()

        por_dia = conn.execute("""
            SELECT fecha, SUM(total) as total, COUNT(*) as ventas
            FROM ventas WHERE fecha BETWEEN ? AND ? AND anulada = 0
            GROUP BY fecha ORDER BY fecha
        """, (desde, hasta)).fetchall()

        return {"totales": totales, "por_dia": por_dia}


def reporte_productos_mas_vendidos(desde: str = None, hasta: str = None,
                                   limite: int = 20) -> list:
    with get_connection() as conn:
        filtro = ""
        params = []
        if desde and hasta:
            filtro = "WHERE v.fecha BETWEEN ? AND ?"
            params = [desde, hasta]
        return conn.execute(f"""
            SELECT p.id, p.nombre, p.categoria_id, c.nombre as categoria,
                   SUM(dv.cantidad) as unidades_vendidas,
                   SUM(dv.subtotal) as ingresos_total,
                   COUNT(DISTINCT v.id) as veces_vendido
            FROM detalle_ventas dv
            JOIN productos p ON p.id = dv.producto_id
            JOIN ventas v ON v.id = dv.venta_id AND v.anulada = 0
            LEFT JOIN categorias c ON c.id = p.categoria_id
            {filtro}
            GROUP BY p.id ORDER BY unidades_vendidas DESC LIMIT ?
        """, params + [limite]).fetchall()


def reporte_ingresos_mensuales(anio: int = None) -> list:
    if not anio:
        anio = date.today().year
    with get_connection() as conn:
        return conn.execute("""
            SELECT strftime('%Y-%m', fecha) as mes,
                   SUM(total) as total,
                   COUNT(*) as ventas,
                   AVG(total) as ticket_promedio
            FROM ventas
            WHERE strftime('%Y', fecha) = ? AND anulada = 0
            GROUP BY mes ORDER BY mes
        """, (str(anio),)).fetchall()


def reporte_caja_diaria(desde: str, hasta: str) -> list:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM caja_diaria WHERE fecha BETWEEN ? AND ? ORDER BY fecha DESC",
            (desde, hasta)
        ).fetchall()


# ══════════════════════════════════════════════════════════════
#  CATEGORÍAS / PROVEEDORES
# ══════════════════════════════════════════════════════════════

def obtener_categorias() -> list:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM categorias ORDER BY nombre").fetchall()


def obtener_proveedores(solo_activos=True) -> list:
    with get_connection() as conn:
        q = "SELECT * FROM proveedores"
        if solo_activos:
            q += " WHERE activo = 1"
        return conn.execute(q + " ORDER BY nombre").fetchall()


def crear_proveedor(nombre: str, telefono: str = "", email: str = "", notas: str = "") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO proveedores (nombre, telefono, email, notas) VALUES (?, ?, ?, ?)",
            (nombre, telefono, email, notas)
        )
        return cur.lastrowid


# ══════════════════════════════════════════════════════════════
#  CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════

def get_config(clave: str, default=None):
    with get_connection() as conn:
        row = conn.execute("SELECT valor, tipo FROM configuracion WHERE clave = ?", (clave,)).fetchone()
        if not row:
            return default
        v, t = row["valor"], row["tipo"]
        if t == "int":
            return int(v)
        if t == "float":
            return float(v)
        if t == "bool":
            return v.lower() in ("1", "true", "si")
        return v


def set_config(clave: str, valor, tipo: str = "string"):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO configuracion (clave, valor, tipo) VALUES (?, ?, ?)
            ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor
        """, (clave, str(valor), tipo))


if __name__ == "__main__":
    init_db()
    print("[OK] Base de datos creada correctamente.")
