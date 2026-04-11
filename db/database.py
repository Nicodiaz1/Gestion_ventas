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
    ('ultima_sincronizacion', '', 'string'),
    ('dias_alerta_vencimiento', '30', 'int'),
    ('dias_alerta_facturas',    '7',  'int');

-- ── Facturas de proveedores (cuentas corrientes) ─────────────
CREATE TABLE IF NOT EXISTS facturas_proveedores (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    proveedor_id     INTEGER REFERENCES proveedores(id),
    numero_factura   TEXT,
    descripcion      TEXT,
    monto_total      REAL    NOT NULL DEFAULT 0,
    monto_pagado     REAL    NOT NULL DEFAULT 0,
    fecha_emision    DATE    NOT NULL,
    fecha_vencimiento DATE   NOT NULL,
    estado           TEXT    NOT NULL DEFAULT 'pendiente',
    -- pendiente | pagada | vencida | saldo_favor
    dias_alerta      INTEGER NOT NULL DEFAULT 7,  -- días antes del vencimiento para avisar
    notas            TEXT,
    por_revisar      INTEGER NOT NULL DEFAULT 0,  -- 1 = marcar para revisar después
    creado_en        DATETIME DEFAULT CURRENT_TIMESTAMP,
    modificado_en    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_facturas_proveedor  ON facturas_proveedores(proveedor_id);
CREATE INDEX IF NOT EXISTS idx_facturas_vencimiento ON facturas_proveedores(fecha_vencimiento);
CREATE INDEX IF NOT EXISTS idx_facturas_estado      ON facturas_proveedores(estado);

-- ── Lotes de stock (vencimientos y cosechas de vino) ────────────
CREATE TABLE IF NOT EXISTS lotes (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id       INTEGER NOT NULL REFERENCES productos(id),
    cantidad          INTEGER NOT NULL DEFAULT 0,
    cosecha           INTEGER,          -- año de producción (vinos)
    fecha_vencimiento DATE,             -- NULL si no aplica
    motivo            TEXT DEFAULT 'Ingreso de mercancía',
    fecha_ingreso     DATETIME DEFAULT CURRENT_TIMESTAMP,
    notas             TEXT
);
CREATE INDEX IF NOT EXISTS idx_lotes_producto    ON lotes(producto_id);
CREATE INDEX IF NOT EXISTS idx_lotes_vencimiento ON lotes(fecha_vencimiento);
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
        # Migración: tabla facturas_proveedores (por si la DB es anterior)
        tablas = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if "facturas_proveedores" not in tablas:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS facturas_proveedores (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    proveedor_id     INTEGER REFERENCES proveedores(id),
                    numero_factura   TEXT,
                    descripcion      TEXT,
                    monto_total      REAL    NOT NULL DEFAULT 0,
                    monto_pagado     REAL    NOT NULL DEFAULT 0,
                    fecha_emision    DATE    NOT NULL,
                    fecha_vencimiento DATE   NOT NULL,
                    estado           TEXT    NOT NULL DEFAULT 'pendiente',
                    notas            TEXT,
                    creado_en        DATETIME DEFAULT CURRENT_TIMESTAMP,
                    modificado_en    DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_facturas_proveedor   ON facturas_proveedores(proveedor_id);
                CREATE INDEX IF NOT EXISTS idx_facturas_vencimiento ON facturas_proveedores(fecha_vencimiento);
                CREATE INDEX IF NOT EXISTS idx_facturas_estado      ON facturas_proveedores(estado);
            """)
            print("[DB] Migración: tabla facturas_proveedores creada.")
        if "lotes" not in tablas:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS lotes (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto_id       INTEGER NOT NULL REFERENCES productos(id),
                    cantidad          INTEGER NOT NULL DEFAULT 0,
                    cosecha           INTEGER,
                    fecha_vencimiento DATE,
                    motivo            TEXT DEFAULT 'Ingreso de mercancía',
                    fecha_ingreso     DATETIME DEFAULT CURRENT_TIMESTAMP,
                    notas             TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_lotes_producto    ON lotes(producto_id);
                CREATE INDEX IF NOT EXISTS idx_lotes_vencimiento ON lotes(fecha_vencimiento);
            """)
            print("[DB] Migración: tabla lotes creada.")
        # Migración: columna dias_alerta en facturas_proveedores
        cols_facturas = [r[1] for r in conn.execute(
            "PRAGMA table_info(facturas_proveedores)").fetchall()]
        if "facturas_proveedores" in tablas and "dias_alerta" not in cols_facturas:
            conn.execute(
                "ALTER TABLE facturas_proveedores ADD COLUMN dias_alerta INTEGER NOT NULL DEFAULT 7")
            print("[DB] Migración: columna dias_alerta agregada a facturas_proveedores.")
        # Migración: columna lote_id en detalle_ventas
        cols_dv = [r[1] for r in conn.execute(
            "PRAGMA table_info(detalle_ventas)").fetchall()]
        if "lote_id" not in cols_dv:
            conn.execute(
                "ALTER TABLE detalle_ventas ADD COLUMN lote_id INTEGER REFERENCES lotes(id)")
            print("[DB] Migración: columna lote_id agregada a detalle_ventas.")
        # Migración: columna pagos_json en ventas (pago mixto/dividido)
        cols_ventas = [r[1] for r in conn.execute("PRAGMA table_info(ventas)").fetchall()]
        if "pagos_json" not in cols_ventas:
            conn.execute("ALTER TABLE ventas ADD COLUMN pagos_json TEXT")
            print("[DB] Migración: columna pagos_json agregada a ventas.")
        # Migración: columna por_revisar en facturas_proveedores
        cols_facturas2 = [r[1] for r in conn.execute(
            "PRAGMA table_info(facturas_proveedores)").fetchall()]
        if "por_revisar" not in cols_facturas2:
            conn.execute(
                "ALTER TABLE facturas_proveedores ADD COLUMN por_revisar INTEGER NOT NULL DEFAULT 0")
            print("[DB] Migración: columna por_revisar agregada a facturas_proveedores.")
        # Migración: tabla gastos
        if "gastos" not in tablas:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS gastos (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha       DATE    NOT NULL,
                    categoria   TEXT    NOT NULL DEFAULT 'Otro',
                    descripcion TEXT    NOT NULL,
                    monto       REAL    NOT NULL DEFAULT 0,
                    creado_en   DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_gastos_fecha ON gastos(fecha);
            """)
            print("[DB] Migración: tabla gastos creada.")
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


def actualizar_precios_masivo(porcentaje: float, categoria_id: int = None):
    """Aplica un % de aumento/descuento a precio_venta (y costo si se indica).
    categoria_id=None → todos los productos activos."""
    factor = 1 + porcentaje / 100
    with get_connection() as conn:
        if categoria_id:
            conn.execute("""
                UPDATE productos
                SET precio_venta = ROUND(precio_venta * ?, 2),
                    modificado_en = ?
                WHERE activo = 1 AND categoria_id = ?
            """, (factor, datetime.now().isoformat(), categoria_id))
        else:
            conn.execute("""
                UPDATE productos
                SET precio_venta = ROUND(precio_venta * ?, 2),
                    modificado_en = ?
                WHERE activo = 1
            """, (factor, datetime.now().isoformat()))


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
                    cuotas: int = 1, notas: str = "",
                    recargo_pct: float = 0,
                    pagos: list = None) -> int:
    """
    items: [{"producto_id": int, "cantidad": int, "precio_unit": float}, ...]
    recargo_pct: porcentaje de recargo (+) o descuento (-). Ej: 15 = +15%, -10 = -10%
    pagos: lista para pago dividido: [{"metodo": "efectivo", "monto": 21000}, ...]
           Si se provee, medio_pago se sobreescribe con "mixto" (si hay más de uno).
    Retorna el ID de la venta creada.
    """
    import json as _json
    ahora = datetime.now()
    subtotal = sum(i["cantidad"] * i["precio_unit"] for i in items)
    base  = max(0.0, subtotal - descuento)
    total = base * (1 + recargo_pct / 100)

    # ── Resolver medio_pago y pagos_json ──────────────────────
    pagos_json = None
    if pagos and len(pagos) > 1:
        medio_pago = "mixto"
        pagos_json = _json.dumps(pagos, ensure_ascii=False)
    elif pagos and len(pagos) == 1:
        medio_pago = pagos[0]["metodo"]   # pago simple vía nueva interfaz

    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO ventas (fecha, hora, datetime_venta, subtotal, descuento, total,
                                medio_pago, cuotas, notas, pagos_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ahora.date().isoformat(), ahora.strftime("%H:%M:%S"),
              ahora.isoformat(), subtotal, descuento, total,
              medio_pago, cuotas, notas, pagos_json))
        venta_id = cur.lastrowid

        for item in items:
            sub_item = item["cantidad"] * item["precio_unit"]
            conn.execute("""
                INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, precio_unit, subtotal, lote_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (venta_id, item["producto_id"], item["cantidad"],
                  item["precio_unit"], sub_item, item.get("lote_id")))

            # Descontar stock (puede quedar negativo intencionalmente)
            row = conn.execute("SELECT stock_actual FROM productos WHERE id = ?",
                               (item["producto_id"],)).fetchone()
            stock_ant = row["stock_actual"]
            stock_nuevo = stock_ant - item["cantidad"]   # permite negativos
            conn.execute("UPDATE productos SET stock_actual = ?, modificado_en = ? WHERE id = ?",
                         (stock_nuevo, ahora.isoformat(), item["producto_id"]))
            _registrar_movimiento_conn(conn, item["producto_id"], "salida",
                                       item["cantidad"], stock_ant, stock_nuevo,
                                       "Venta", venta_id)

            # Descontar de lotes: si viene lote_id específico úsalo, si no FIFO
            lote_id = item.get("lote_id")
            restante = item["cantidad"]
            if lote_id:
                fila = conn.execute(
                    "SELECT id, cantidad FROM lotes WHERE id = ?", (lote_id,)).fetchone()
                if fila:
                    nueva_cant = max(0, fila["cantidad"] - restante)
                    conn.execute("UPDATE lotes SET cantidad = ? WHERE id = ?",
                                 (nueva_cant, lote_id))
            else:
                # FIFO: descontar por cosecha más antigua con cantidad > 0
                lotes_fifo = conn.execute("""
                    SELECT id, cantidad FROM lotes
                    WHERE producto_id = ? AND cantidad > 0
                    ORDER BY
                        CASE WHEN cosecha IS NULL THEN 1 ELSE 0 END,
                        cosecha ASC,
                        CASE WHEN fecha_vencimiento IS NULL THEN 1 ELSE 0 END,
                        fecha_vencimiento ASC
                """, (item["producto_id"],)).fetchall()
                for lote in lotes_fifo:
                    if restante <= 0:
                        break
                    quitar = min(restante, lote["cantidad"])
                    conn.execute("UPDATE lotes SET cantidad = ? WHERE id = ?",
                                 (lote["cantidad"] - quitar, lote["id"]))
                    restante -= quitar

        # Actualizar caja diaria (distribuir entre métodos si pago mixto)
        # Las extracciones internas no registran cobro en caja
        if medio_pago != "extraccion":
            if pagos and len(pagos) > 1:
                _actualizar_caja_mixto(conn, ahora.date().isoformat(), pagos, total)
            else:
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


def _actualizar_caja_mixto(conn, fecha: str, pagos: list, total: float):
    """Distribuye un pago mixto entre los distintos medios en caja_diaria."""
    col_map = {
        "efectivo": "efectivo", "debito": "debito",
        "credito": "credito", "transferencia": "transferencia", "qr": "qr"
    }
    # Primero asegurar que existe la fila del día y sumar cantidad_ventas + total una vez
    conn.execute("""
        INSERT INTO caja_diaria (fecha, total, cantidad_ventas)
        VALUES (?, ?, 1)
        ON CONFLICT(fecha) DO UPDATE SET
            total = total + excluded.total,
            cantidad_ventas = cantidad_ventas + 1,
            ticket_promedio = (total + excluded.total) / (cantidad_ventas + 1)
    """, (fecha, total))
    # Luego sumar cada método por separado (sin contar cantidad_ventas de nuevo)
    for pago in pagos:
        col = col_map.get(pago["metodo"], "efectivo")
        monto = pago["monto"]
        conn.execute(f"""
            UPDATE caja_diaria SET {col} = {col} + ? WHERE fecha = ?
        """, (monto, fecha))


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
        # Restar de caja diaria (extracciones no afectan caja)
        fecha = venta["fecha"]
        mp = venta["medio_pago"]
        total_v = venta["total"]
        if mp != "extraccion":
            if mp == "mixto" and venta["pagos_json"]:
                import json as _json
                pagos = _json.loads(venta["pagos_json"])
                col_map = {"efectivo": "efectivo", "debito": "debito",
                           "credito": "credito", "transferencia": "transferencia", "qr": "qr"}
                conn.execute("""
                    UPDATE caja_diaria SET total = total - ?,
                    cantidad_ventas = MAX(0, cantidad_ventas - 1) WHERE fecha = ?
                """, (total_v, fecha))
                for pago in pagos:
                    col = col_map.get(pago["metodo"], "efectivo")
                    conn.execute(f"""
                        UPDATE caja_diaria SET {col} = {col} - ? WHERE fecha = ?
                    """, (pago["monto"], fecha))
            else:
                col_map = {"efectivo": "efectivo", "debito": "debito",
                           "credito": "credito", "transferencia": "transferencia", "qr": "qr"}
                col = col_map.get(mp, "efectivo")
                conn.execute(f"""
                    UPDATE caja_diaria SET {col} = {col} - ?, total = total - ?,
                    cantidad_ventas = MAX(0, cantidad_ventas - 1) WHERE fecha = ?
                """, (total_v, total_v, fecha))
        return True


def obtener_venta(venta_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM ventas WHERE id = ?", (venta_id,)).fetchone()


def detalle_venta(venta_id: int) -> list:
    with get_connection() as conn:
        items = conn.execute("""
            SELECT dv.*, p.nombre, p.codigo_barras, p.unidad,
                   l.cosecha
            FROM detalle_ventas dv
            JOIN productos p ON p.id = dv.producto_id
            LEFT JOIN lotes l ON l.id = dv.lote_id
            WHERE dv.venta_id = ?
        """, (venta_id,)).fetchall()
        venta = conn.execute("SELECT * FROM ventas WHERE id = ?", (venta_id,)).fetchone()
        return {"items": items, "venta": venta}


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
            SELECT fecha,
                   SUM(total) as total,
                   COUNT(*) as ventas,
                   SUM(CASE WHEN medio_pago='efectivo'      THEN total ELSE 0 END) as efectivo,
                   SUM(CASE WHEN medio_pago='debito'        THEN total ELSE 0 END) as debito,
                   SUM(CASE WHEN medio_pago='credito'       THEN total ELSE 0 END) as credito,
                   SUM(CASE WHEN medio_pago='transferencia' THEN total ELSE 0 END) as transferencia,
                   SUM(CASE WHEN medio_pago='qr'            THEN total ELSE 0 END) as qr
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


def actualizar_proveedor(proveedor_id: int, datos: dict):
    campos = {k: v for k, v in datos.items()
              if k in ("nombre", "telefono", "email", "notas")}
    if not campos:
        return
    sets = ", ".join(f"{k} = ?" for k in campos)
    vals = list(campos.values()) + [proveedor_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE proveedores SET {sets} WHERE id = ?", vals)


def eliminar_proveedor(proveedor_id: int):
    """Soft-delete: desactiva el proveedor sin borrar su historial de facturas."""
    with get_connection() as conn:
        conn.execute("UPDATE proveedores SET activo = 0 WHERE id = ?", (proveedor_id,))


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


# ══════════════════════════════════════════════════════════════
#  FACTURAS DE PROVEEDORES (cuentas corrientes)
# ══════════════════════════════════════════════════════════════

def _recalc_estado(monto_total: float, monto_pagado: float,
                   fecha_vencimiento: str) -> str:
    """Calcula el estado lógico de una factura."""
    from datetime import date
    saldo = round(monto_total - monto_pagado, 2)
    if saldo <= 0:
        return "saldo_favor" if monto_pagado > monto_total else "pagada"
    hoy = date.today().isoformat()
    return "vencida" if fecha_vencimiento < hoy else "pendiente"


def crear_factura_proveedor(datos: dict) -> int:
    estado = _recalc_estado(
        datos.get("monto_total", 0),
        datos.get("monto_pagado", 0),
        datos["fecha_vencimiento"]
    )
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO facturas_proveedores
            (proveedor_id, numero_factura, descripcion, monto_total,
             monto_pagado, fecha_emision, fecha_vencimiento, estado, dias_alerta, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datos.get("proveedor_id"),
            datos.get("numero_factura", ""),
            datos.get("descripcion", ""),
            datos.get("monto_total", 0),
            datos.get("monto_pagado", 0),
            datos["fecha_emision"],
            datos["fecha_vencimiento"],
            estado,
            datos.get("dias_alerta", 7),
            datos.get("notas", ""),
        ))
        return cur.lastrowid


def actualizar_factura_proveedor(factura_id: int, datos: dict):
    datos["modificado_en"] = datetime.now().isoformat()
    # Recalcular estado automáticamente
    if "monto_total" in datos or "monto_pagado" in datos or "fecha_vencimiento" in datos:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT monto_total, monto_pagado, fecha_vencimiento FROM facturas_proveedores WHERE id=?",
                (factura_id,)
            ).fetchone()
        if row:
            mt  = datos.get("monto_total",       row["monto_total"])
            mp  = datos.get("monto_pagado",      row["monto_pagado"])
            fv  = datos.get("fecha_vencimiento", row["fecha_vencimiento"])
            datos["estado"] = _recalc_estado(mt, mp, fv)
    sets   = ", ".join(f"{k} = ?" for k in datos)
    valores = list(datos.values()) + [factura_id]
    with get_connection() as conn:
        conn.execute(
            f"UPDATE facturas_proveedores SET {sets} WHERE id = ?", valores)


def eliminar_factura_proveedor(factura_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM facturas_proveedores WHERE id = ?", (factura_id,))


def obtener_facturas_proveedor(proveedor_id: int = None,
                                estado: str = None,
                                por_revisar: bool = False) -> list:
    """Todas las facturas enriquecidas con datos del proveedor."""
    with get_connection() as conn:
        conds  = []
        params = []
        if proveedor_id:
            conds.append("f.proveedor_id = ?")
            params.append(proveedor_id)
        if por_revisar:
            conds.append("f.por_revisar = 1")
        elif estado:
            conds.append("f.estado = ?")
            params.append(estado)
        where = ("WHERE " + " AND ".join(conds)) if conds else ""
        return conn.execute(f"""
            SELECT f.*,
                   pr.nombre   AS proveedor_nombre,
                   pr.telefono AS proveedor_telefono,
                   pr.email    AS proveedor_email,
                   (f.monto_total - f.monto_pagado) AS saldo
            FROM facturas_proveedores f
            LEFT JOIN proveedores pr ON pr.id = f.proveedor_id
            {where}
            ORDER BY f.fecha_vencimiento ASC
        """, params).fetchall()


def resumen_deuda_proveedores() -> list:
    """Deuda total agrupada por proveedor."""
    with get_connection() as conn:
        return conn.execute("""
            SELECT pr.id,
                   pr.nombre   AS proveedor_nombre,
                   pr.telefono AS proveedor_telefono,
                   COUNT(f.id) AS total_facturas,
                   SUM(CASE WHEN f.estado IN ('pendiente','vencida')
                            THEN f.monto_total - f.monto_pagado ELSE 0 END) AS deuda_total,
                   SUM(CASE WHEN f.estado = 'vencida'
                            THEN f.monto_total - f.monto_pagado ELSE 0 END) AS deuda_vencida,
                   SUM(CASE WHEN f.estado = 'saldo_favor'
                            THEN f.monto_pagado - f.monto_total ELSE 0 END) AS saldo_favor
            FROM proveedores pr
            LEFT JOIN facturas_proveedores f ON f.proveedor_id = pr.id
            WHERE pr.activo = 1
            GROUP BY pr.id
            ORDER BY deuda_total DESC
        """).fetchall()


def facturas_por_vencer() -> list:
    """Facturas pendientes que vencen dentro del plazo de alerta de cada factura."""
    from datetime import date
    hoy = date.today().isoformat()
    with get_connection() as conn:
        return conn.execute("""
            SELECT f.*,
                   pr.nombre AS proveedor_nombre,
                   (f.monto_total - f.monto_pagado) AS saldo
            FROM facturas_proveedores f
            LEFT JOIN proveedores pr ON pr.id = f.proveedor_id
            WHERE f.estado = 'pendiente'
              AND f.fecha_vencimiento >= ?
              AND f.fecha_vencimiento <= date('now', '+' || f.dias_alerta || ' days')
            ORDER BY f.fecha_vencimiento ASC
        """, (hoy,)).fetchall()


def compras_por_periodo(desde: str, hasta: str, proveedor_id: int = None) -> dict:
    """
    Devuelve compras (facturas_proveedores) agrupadas por mes y por proveedor,
    junto con las ventas del mismo período para calcular ganancia estimada.
    """
    with get_connection() as conn:
        cond_prov  = "AND f.proveedor_id = ?" if proveedor_id else ""
        params_prov = [proveedor_id] if proveedor_id else []

        # Totales del período por proveedor
        por_proveedor = conn.execute(f"""
            SELECT pr.nombre AS proveedor_nombre,
                   COUNT(f.id)              AS total_facturas,
                   SUM(f.monto_total)       AS compras_total,
                   SUM(f.monto_pagado)      AS pagado_total,
                   SUM(f.monto_total - f.monto_pagado) AS deuda_total
            FROM facturas_proveedores f
            LEFT JOIN proveedores pr ON pr.id = f.proveedor_id
            WHERE f.fecha_emision BETWEEN ? AND ?
              {cond_prov}
            GROUP BY f.proveedor_id
            ORDER BY compras_total DESC
        """, [desde, hasta] + params_prov).fetchall()

        # Compras agrupadas por mes para la línea de tiempo
        por_mes = conn.execute(f"""
            SELECT strftime('%Y-%m', f.fecha_emision) AS mes,
                   pr.nombre AS proveedor_nombre,
                   SUM(f.monto_total) AS compras_total
            FROM facturas_proveedores f
            LEFT JOIN proveedores pr ON pr.id = f.proveedor_id
            WHERE f.fecha_emision BETWEEN ? AND ?
              {cond_prov}
            GROUP BY mes, f.proveedor_id
            ORDER BY mes ASC
        """, [desde, hasta] + params_prov).fetchall()

        # Ventas del mismo período
        ventas = conn.execute("""
            SELECT SUM(total) AS ventas_total, COUNT(*) AS cantidad_ventas
            FROM ventas
            WHERE fecha BETWEEN ? AND ? AND anulada = 0
        """, (desde, hasta)).fetchone()

        # Ventas por mes para superponer en el gráfico
        ventas_mes = conn.execute("""
            SELECT strftime('%Y-%m', fecha) AS mes, SUM(total) AS ventas_total
            FROM ventas
            WHERE fecha BETWEEN ? AND ? AND anulada = 0
            GROUP BY mes ORDER BY mes ASC
        """, (desde, hasta)).fetchall()

        return {
            "por_proveedor": por_proveedor,
            "por_mes":       por_mes,
            "ventas":        ventas,
            "ventas_mes":    ventas_mes,
        }


# ══════════════════════════════════════════════════════════════
#  LOTES (vencimientos y cosechas de vino)
# ══════════════════════════════════════════════════════════════

def crear_lote(producto_id: int, cantidad: int,
              fecha_vencimiento: str = None, cosecha: int = None,
              motivo: str = "Ingreso de mercancía", notas: str = "") -> int:
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO lotes (producto_id, cantidad, fecha_vencimiento, cosecha, motivo, notas)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (producto_id, cantidad, fecha_vencimiento, cosecha, motivo, notas))
        return cur.lastrowid


def actualizar_lote(lote_id: int, cosecha: int = None, fecha_vencimiento: str = None) -> None:
    """Actualiza cosecha y/o fecha de vencimiento de un lote existente."""
    with get_connection() as conn:
        conn.execute("""
            UPDATE lotes
            SET cosecha = ?, fecha_vencimiento = ?
            WHERE id = ?
        """, (cosecha, fecha_vencimiento, lote_id))


def obtener_lotes_producto(producto_id: int) -> list:
    """Lotes activos (cantidad > 0) de un producto, ordenados por cosecha y vencimiento."""
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM lotes
            WHERE producto_id = ? AND cantidad > 0
            ORDER BY
                CASE WHEN cosecha IS NULL THEN 1 ELSE 0 END, cosecha ASC,
                CASE WHEN fecha_vencimiento IS NULL THEN 1 ELSE 0 END, fecha_vencimiento ASC
        """, (producto_id,)).fetchall()


def lotes_por_vencer(dias: int = 30) -> list:
    """Lotes cuya fecha_vencimiento cae dentro de los próximos N días (sin contar vencidos)."""
    with get_connection() as conn:
        return conn.execute("""
            SELECT l.*, p.nombre AS producto_nombre
            FROM lotes l
            JOIN productos p ON p.id = l.producto_id
            WHERE l.fecha_vencimiento IS NOT NULL
              AND l.fecha_vencimiento >= date('now')
              AND l.fecha_vencimiento <= date('now', ?)
              AND l.cantidad > 0
              AND p.activo = 1
            ORDER BY l.fecha_vencimiento ASC
        """, (f"+{dias} days",)).fetchall()


def lotes_vencidos() -> list:
    """Lotes ya vencidos (fecha_vencimiento < hoy) con cantidad > 0."""
    with get_connection() as conn:
        return conn.execute("""
            SELECT l.*, p.nombre AS producto_nombre
            FROM lotes l
            JOIN productos p ON p.id = l.producto_id
            WHERE l.fecha_vencimiento IS NOT NULL
              AND l.fecha_vencimiento < date('now')
              AND l.cantidad > 0
              AND p.activo = 1
            ORDER BY l.fecha_vencimiento ASC
        """).fetchall()


def actualizar_cantidad_lote(lote_id: int, nueva_cantidad: int):
    with get_connection() as conn:
        conn.execute("UPDATE lotes SET cantidad = ? WHERE id = ?",
                     (nueva_cantidad, lote_id))


# ══════════════════════════════════════════════════════════════
#  GASTOS OPERATIVOS
# ══════════════════════════════════════════════════════════════

CATEGORIAS_GASTO = [
    "Servicios (Luz/Agua/Gas)",
    "Impuestos / Municipalidad",
    "Comisiones Posnet / Tarjetas",
    "Alquiler",
    "Sueldos / Personal",
    "Obra / Mejora",
    "Otro",
]


def registrar_gasto(fecha: str, categoria: str, descripcion: str, monto: float) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO gastos (fecha, categoria, descripcion, monto) VALUES (?, ?, ?, ?)",
            (fecha, categoria, descripcion, monto))
        return cur.lastrowid


def eliminar_gasto(gasto_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM gastos WHERE id = ?", (gasto_id,))


def obtener_gastos_periodo(desde: str, hasta: str) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM gastos
            WHERE fecha BETWEEN ? AND ?
            ORDER BY fecha DESC, id DESC
        """, (desde, hasta)).fetchall()


def resumen_finanzas_periodo(desde: str, hasta: str) -> dict:
    """Devuelve ingresos por medio de pago, costo estimado, gastos y margen del período."""
    with get_connection() as conn:
        # Ingresos de ventas
        r = conn.execute("""
            SELECT
                COALESCE(SUM(total), 0)        as ingresos,
                COALESCE(SUM(descuento), 0)    as descuentos,
                COUNT(*)                        as n_ventas,
                COALESCE(SUM(CASE WHEN medio_pago='efectivo'     THEN total ELSE 0 END), 0) as efectivo,
                COALESCE(SUM(CASE WHEN medio_pago='debito'       THEN total ELSE 0 END), 0) as debito,
                COALESCE(SUM(CASE WHEN medio_pago='credito'      THEN total ELSE 0 END), 0) as credito,
                COALESCE(SUM(CASE WHEN medio_pago='transferencia' THEN total ELSE 0 END), 0) as transferencia,
                COALESCE(SUM(CASE WHEN medio_pago='qr'           THEN total ELSE 0 END), 0) as qr
            FROM ventas WHERE fecha BETWEEN ? AND ? AND anulada = 0
        """, (desde, hasta)).fetchone()

        # Costo estimado (costo unitario × cantidad vendida)
        costo = conn.execute("""
            SELECT COALESCE(SUM(p.precio_costo * dv.cantidad), 0) as costo_total
            FROM detalle_ventas dv
            JOIN ventas v ON v.id = dv.venta_id
            JOIN productos p ON p.id = dv.producto_id
            WHERE v.fecha BETWEEN ? AND ? AND v.anulada = 0
        """, (desde, hasta)).fetchone()["costo_total"]

        # Gastos operativos
        gastos_rows = conn.execute("""
            SELECT COALESCE(SUM(monto), 0) as total_gastos FROM gastos
            WHERE fecha BETWEEN ? AND ?
        """, (desde, hasta)).fetchone()

        ingresos = r["ingresos"]
        total_gastos = gastos_rows["total_gastos"]
        margen_bruto = ingresos - costo
        margen_neto  = margen_bruto - total_gastos

        return {
            "ingresos":         ingresos,
            "descuentos":       r["descuentos"],
            "n_ventas":         r["n_ventas"],
            "costo_estimado":   costo,
            "margen_bruto":     margen_bruto,
            "gastos_operativos": total_gastos,
            "margen_neto":      margen_neto,
            "pct_margen_neto":  (margen_neto / ingresos * 100) if ingresos else 0,
            "por_medio": {
                "efectivo":      r["efectivo"],
                "debito":        r["debito"],
                "credito":       r["credito"],
                "transferencia": r["transferencia"],
                "qr":            r["qr"],
            }
        }
