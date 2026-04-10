#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
#  main.py  –  Punto de entrada de la aplicación Vinoteca
# ─────────────────────────────────────────────────────────────

import sys
import os

# Asegurar que el directorio raíz esté en el path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from PyQt6.QtWidgets import QApplication, QSplashScreen, QLabel, QComboBox
from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtGui import QPixmap, QFont, QColor, QPainter, QPainterPath


def _patch_combo_popup():
    """Ensancha el popup de todo QComboBox al texto más largo, globalmente."""
    _orig = QComboBox.showPopup

    def _showPopup(self):
        _orig(self)
        view = self.view()
        fm   = view.fontMetrics()
        ancho_max = max(
            (fm.horizontalAdvance(self.itemText(i)) for i in range(self.count())),
            default=0,
        )
        ancho_necesario = ancho_max + 52   # margen para scrollbar y padding
        if ancho_necesario > self.width():
            view.setMinimumWidth(ancho_necesario)

    QComboBox.showPopup = _showPopup


from ui.main_window import MainWindow
from version import VERSION_ACTUAL, get_version_instalada
from config import GITHUB_USUARIO, GITHUB_REPO, CHEQUEAR_UPDATES, BASE_DIR


def main():
    app = QApplication(sys.argv)
    _patch_combo_popup()
    app.setApplicationName("Vinoteca")
    app.setOrganizationName("Vinoteca")
    app.setApplicationVersion(VERSION_ACTUAL)

    # ── Splash screen ─────────────────────────────────────────
    logo_path = os.path.join(BASE_DIR, "assets", "logo.png")
    SPLASH_W, SPLASH_H = 420, 340

    splash_pix = QPixmap(SPLASH_W, SPLASH_H)
    splash_pix.fill(QColor("#1A1A1A"))

    painter = QPainter(splash_pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    if os.path.exists(logo_path):
        logo_pix = QPixmap(logo_path).scaled(
            260, 220,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        # Centrar logo horizontalmente, parte superior con margen
        lx = (SPLASH_W - logo_pix.width()) // 2
        ly = 20
        # Fondo blanco redondeado detrás del logo
        painter.setBrush(QColor("#FFFFFF"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(lx - 10, ly - 8, logo_pix.width() + 20,
                                logo_pix.height() + 16, 12, 12)
        painter.drawPixmap(lx, ly, logo_pix)
        texto_y = ly + logo_pix.height() + 32
    else:
        painter.setPen(QColor("#C9A84C"))
        painter.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        painter.drawText(splash_pix.rect(), Qt.AlignmentFlag.AlignCenter, "🍷  Vinoteca")
        texto_y = SPLASH_H - 60

    # Texto inferior
    painter.setPen(QColor("#AAAAAA"))
    painter.setFont(QFont("Segoe UI", 9))
    painter.drawText(0, texto_y, SPLASH_W, 24, Qt.AlignmentFlag.AlignCenter,
                     "Cargando sistema…")
    # Línea decorativa burdeos
    painter.setPen(QColor("#722F37"))
    painter.drawLine(40, SPLASH_H - 12, SPLASH_W - 40, SPLASH_H - 12)
    painter.end()

    splash = QSplashScreen(splash_pix)
    splash.setWindowFlags(
        Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint
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

    # Usar version_stamp.txt si existe (caso .exe con actualizaciones previas)
    v_instalada = get_version_instalada()
    checker = UpdateChecker(GITHUB_USUARIO, GITHUB_REPO, v_instalada)

    def _on_update(version_nueva, download_url):
        dlg = DialogoActualizacion(
            version_nueva, download_url,
            v_instalada, BASE_DIR, parent
        )
        dlg.exec()

    checker.update_disponible.connect(_on_update)
    # Guardar referencia para que no lo mate el GC
    parent._update_checker = checker
    checker.start()


if __name__ == "__main__":
    main()
