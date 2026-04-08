#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
#  main.py  –  Punto de entrada de la aplicación Vinoteca
# ─────────────────────────────────────────────────────────────

import sys
import os

# Asegurar que el directorio raíz esté en el path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from PyQt6.QtWidgets import QApplication, QSplashScreen, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QFont, QColor

from ui.main_window import MainWindow
from version import VERSION_ACTUAL
from config import GITHUB_USUARIO, GITHUB_REPO, CHEQUEAR_UPDATES


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Vinoteca")
    app.setOrganizationName("Vinoteca")
    app.setApplicationVersion(VERSION_ACTUAL)

    # ── Splash screen ─────────────────────────────────────────
    splash_pix = QPixmap(400, 250)
    splash_pix.fill(QColor("#1A1A1A"))

    splash = QSplashScreen(splash_pix)
    splash.setWindowFlags(
        Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint
    )

    splash.showMessage(
        "🍷  Vinoteca\n\nCargando sistema…",
        Qt.AlignmentFlag.AlignCenter,
        QColor("#C9A84C")
    )
    splash.show()
    app.processEvents()

    # ── Iniciar ventana principal ─────────────────────────────
    window = MainWindow()

    def mostrar_ventana():
        splash.finish(window)
        window.show()
        window.raise_()
        _iniciar_chequeo_updates(window)

    QTimer.singleShot(1200, mostrar_ventana)

    sys.exit(app.exec())


def _iniciar_chequeo_updates(parent):
    """Lanza el chequeo de updates en background (silencioso)."""
    if not CHEQUEAR_UPDATES:
        return
    if not GITHUB_USUARIO or not GITHUB_REPO:
        return   # Aún no configurado → no hacer nada

    from sync.updater import UpdateChecker, DialogoActualizacion

    checker = UpdateChecker(GITHUB_USUARIO, GITHUB_REPO, VERSION_ACTUAL)

    def _on_update(version_nueva, download_url):
        dlg = DialogoActualizacion(
            version_nueva, download_url,
            VERSION_ACTUAL, BASE_DIR, parent
        )
        dlg.exec()

    checker.update_disponible.connect(_on_update)
    # Guardar referencia para que no lo mate el GC
    parent._update_checker = checker
    checker.start()


if __name__ == "__main__":
    main()
