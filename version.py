# ─────────────────────────────────────────────────────────────
#  version.py  –  Versión actual de la aplicación
#
#  Cada vez que hagas un cambio y lo subas a GitHub,
#  incrementá VERSION_ACTUAL. Ejemplo: "1.0" → "1.1"
#
#  GitHub comparará este número con el del repositorio
#  y avisará automáticamente si hay versión nueva.
# ─────────────────────────────────────────────────────────────

VERSION_ACTUAL = "1.6.1"

import os as _os, sys as _sys


def get_version_instalada() -> str:
    """
    Devuelve la versión realmente instalada en disco.
    Cuando la app corre como .exe compilado con PyInstaller, VERSION_ACTUAL
    queda embebida dentro del ejecutable y no cambia aunque el updater
    descargue archivos nuevos. Esta función resuelve esto leyendo
    'version_stamp.txt' que el updater escribe tras cada actualización exitosa.
    """
    if getattr(_sys, "frozen", False):
        base = _os.path.dirname(_sys.executable)
    else:
        base = _os.path.dirname(_os.path.abspath(__file__))
    stamp = _os.path.join(base, "version_stamp.txt")
    if _os.path.exists(stamp):
        try:
            v = open(stamp, encoding="utf-8").read().strip()
            if v:
                return v
        except Exception:
            pass
    return VERSION_ACTUAL
