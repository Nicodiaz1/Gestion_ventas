# ─────────────────────────────────────────────────────────────
#  config.py  –  Configuración global de la aplicación
# ─────────────────────────────────────────────────────────────

import os
import sys

# ── Ruta base: funciona tanto en desarrollo (script) como ─────
#    empaquetado con PyInstaller (.exe / .app)             ─────
if getattr(sys, "frozen", False):
    # PyInstaller congela el código; los datos viven junto al .exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Base de datos local ───────────────────────────────────────
DB_PATH = os.path.join(BASE_DIR, "db", "vinoteca.db")

# ── SQL Server (sincronización) ───────────────────────────────
SQL_SERVER_CONFIG = {
    "server":   "NOMBRE_SERVIDOR",
    "database": "vinoteca",
    "username": "usuario",
    "password": "contraseña",
    "driver":   "ODBC Driver 17 for SQL Server",
}

# ── Negocio ───────────────────────────────────────────────────
NOMBRE_NEGOCIO  = "La Vinoteca"
MONEDA          = "$"
STOCK_MIN_ALERTA = 3          # cantidad mínima antes de mostrar alerta

# ── Exportaciones ─────────────────────────────────────────────
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")

# ── UI ────────────────────────────────────────────────────────
TEMA = "dark"    # "dark" | "light"
COLOR_PRIMARIO   = "#722F37"   # vino
COLOR_SECUNDARIO = "#2C2C2C"
COLOR_ACENTO     = "#C9A84C"   # dorado
COLOR_FONDO      = "#1A1A1A"
COLOR_TEXTO      = "#F5F5F5"
COLOR_EXITO      = "#4CAF50"
COLOR_ADVERTENCIA= "#FF9800"
COLOR_ERROR      = "#F44336"

FUENTE_FAMILIA  = "Segoe UI"
FUENTE_TAMANO   = 11

# ── Actualizaciones automáticas (GitHub) ──────────────────────
# Completar con tu usuario y nombre del repositorio en GitHub.
# Dejarlo en None desactiva las actualizaciones automáticas.
GITHUB_USUARIO    = "Nicodiaz1"
GITHUB_REPO       = "Gestion_ventas"
CHEQUEAR_UPDATES  = True          # False para desactivar por completo
