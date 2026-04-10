# ─────────────────────────────────────────────────────────────
#  sync/updater.py  –  Actualizaciones automáticas desde GitHub
#
#  Flujo cuando corre como .exe (PyInstaller):
#  1. UpdateChecker busca "Vinoteca-Windows.zip" en los assets del release.
#  2. Lo descarga, extrae en carpeta temporal.
#  3. Crea do_update.bat que reemplaza archivos y relanza Vinoteca.exe.
#  4. Lanza do_update.bat y cierra la app actual.
#
#  Flujo cuando corre como .py (Python puro):
#  1. Descarga el zipball del código fuente.
#  2. Reemplaza los archivos .py directamente.
# ─────────────────────────────────────────────────────────────

import os
import sys
import shutil
import zipfile
import tempfile
import subprocess
import urllib.request
import urllib.error
import json

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton,
    QHBoxLayout, QProgressBar, QMessageBox, QApplication
)

# ─────────────────────────────────────────────────────────────
#  Thread: chequeo silencioso en background
# ─────────────────────────────────────────────────────────────

class UpdateChecker(QThread):
    """Chequea en background si hay version nueva en GitHub."""
    update_disponible = pyqtSignal(str, str)   # (version_nueva, download_url)

    def __init__(self, usuario: str, repo: str, version_actual: str):
        super().__init__()
        self.usuario        = usuario
        self.repo           = repo
        self.version_actual = version_actual

    def run(self):
        try:
            api_url = (
                f"https://api.github.com/repos/{self.usuario}/{self.repo}"
                f"/releases/latest"
            )
            req = urllib.request.Request(
                api_url,
                headers={"User-Agent": "Vinoteca-App-Updater/1.0"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())

            tag = data.get("tag_name", "").lstrip("v")
            if not tag:
                return

            if not self._es_mas_nueva(tag, self.version_actual):
                return

            # Si corre como .exe: buscar el asset Vinoteca-Windows.zip
            download_url = ""
            if getattr(sys, "frozen", False):
                for asset in data.get("assets", []):
                    if asset.get("name") == "Vinoteca-Windows.zip":
                        download_url = asset.get("browser_download_url", "")
                        break

            # Fallback: zipball del codigo fuente (para modo Python)
            if not download_url:
                download_url = data.get("zipball_url", "")

            if download_url:
                self.update_disponible.emit(tag, download_url)

        except Exception:
            pass

    @staticmethod
    def _es_mas_nueva(nueva: str, actual: str) -> bool:
        try:
            def _t(v):
                return tuple(int(x) for x in v.split("."))
            return _t(nueva) > _t(actual)
        except Exception:
            return False


# ─────────────────────────────────────────────────────────────
#  Thread: descarga + aplicacion
# ─────────────────────────────────────────────────────────────

class UpdateDownloader(QThread):
    progreso  = pyqtSignal(int)          # 0-100
    terminado = pyqtSignal(bool, str)    # (exito, msg)  msg=="REINICIAR" -> cerrar app

    PRESERVAR_PY = {"db", "exports", ".venv", "__pycache__", "config.py"}

    def __init__(self, download_url: str, base_dir: str, version_nueva: str = ""):
        super().__init__()
        self.download_url  = download_url
        self.base_dir      = base_dir
        self.version_nueva = version_nueva

    def run(self):
        if getattr(sys, "frozen", False):
            self._actualizar_exe()
        else:
            self._actualizar_python()

    # ── Modo .exe: descarga ZIP compilado, helper bat, cierra app ──

    def _actualizar_exe(self):
        tmp_zip = None
        tmp_dir = None
        try:
            self.progreso.emit(5)
            tmp_zip = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
            self._descargar(self.download_url, tmp_zip, 5, 65)
            tmp_zip.close()
            self.progreso.emit(65)

            # Extraer ZIP a carpeta temporal
            tmp_dir = tempfile.mkdtemp(prefix="vinoteca_upd_")
            with zipfile.ZipFile(tmp_zip.name, "r") as zf:
                zf.extractall(tmp_dir)

            # Si el ZIP tiene subcarpeta raiz, entrar en ella
            contenidos = os.listdir(tmp_dir)
            if len(contenidos) == 1 and os.path.isdir(
                    os.path.join(tmp_dir, contenidos[0])):
                carpeta_src = os.path.join(tmp_dir, contenidos[0])
            else:
                carpeta_src = tmp_dir

            self.progreso.emit(75)

            # Crear do_update.bat en la carpeta de la app
            bat_path = os.path.join(self.base_dir, "do_update.bat")
            exe_path = os.path.join(self.base_dir, "Vinoteca.exe")
            self._escribir_bat(bat_path, carpeta_src, self.base_dir, exe_path)

            self.progreso.emit(90)

            # Lanzar bat desconectado (corre despues de que la app cierre)
            subprocess.Popen(
                ["cmd.exe", "/c", bat_path],
                creationflags=0x00000008,   # DETACHED_PROCESS
                close_fds=True
            )

            self.progreso.emit(100)
            self.terminado.emit(True, "REINICIAR")

        except Exception as e:
            self.terminado.emit(False, str(e))
        finally:
            if tmp_zip:
                try:
                    os.unlink(tmp_zip.name)
                except Exception:
                    pass
            # NO borrar tmp_dir aqui: el bat lo usa despues de cerrar la app

    def _escribir_bat(self, bat_path, src, dst, exe):
        stamp_path = os.path.join(dst, "version_stamp.txt")
        lineas = [
            "@echo off",
            "timeout /t 4 /nobreak >nul",
            f'robocopy "{src}" "{dst}" /E /IS /IT /XD db exports .venv __pycache__ /XF config.py /NFL /NDL /NJH /NJS /nc /ns /np',
            f'echo {self.version_nueva}> "{stamp_path}"',
            f'start "" "{exe}"',
            'del "%~f0"',
        ]
        with open(bat_path, "w", encoding="cp1252") as f:
            f.write("\r\n".join(lineas))

    # ── Modo Python: reemplaza .py directamente ────────────────

    def _actualizar_python(self):
        tmp_zip = None
        tmp_dir = None
        try:
            self.progreso.emit(5)
            tmp_zip = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
            self._descargar(self.download_url, tmp_zip, 5, 65)
            tmp_zip.close()
            self.progreso.emit(65)

            tmp_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(tmp_zip.name, "r") as zf:
                zf.extractall(tmp_dir)

            contenidos = os.listdir(tmp_dir)
            carpeta_raiz = os.path.join(tmp_dir, contenidos[0]) \
                if len(contenidos) == 1 and os.path.isdir(
                    os.path.join(tmp_dir, contenidos[0])) else tmp_dir

            self.progreso.emit(70)

            for item in os.listdir(carpeta_raiz):
                if item in self.PRESERVAR_PY:
                    continue
                src  = os.path.join(carpeta_raiz, item)
                dest = os.path.join(self.base_dir, item)
                if os.path.isdir(src):
                    if os.path.exists(dest):
                        shutil.rmtree(dest)
                    shutil.copytree(src, dest)
                else:
                    shutil.copy2(src, dest)

            self.progreso.emit(100)

            if self.version_nueva:
                try:
                    stamp = os.path.join(self.base_dir, "version_stamp.txt")
                    with open(stamp, "w", encoding="utf-8") as f:
                        f.write(self.version_nueva)
                except Exception:
                    pass

            self.terminado.emit(True, "")

        except Exception as e:
            self.terminado.emit(False, str(e))
        finally:
            if tmp_zip:
                try:
                    os.unlink(tmp_zip.name)
                except Exception:
                    pass
            if tmp_dir:
                shutil.rmtree(tmp_dir, ignore_errors=True)

    # ── Helper: descarga con progreso ─────────────────────────

    def _descargar(self, url, tmp_file, pct_ini, pct_fin):
        req = urllib.request.Request(
            url, headers={"User-Agent": "Vinoteca-App-Updater/1.0"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            total      = int(resp.headers.get("Content-Length") or 0)
            descargado = 0
            while True:
                bloque = resp.read(65536)
                if not bloque:
                    break
                tmp_file.write(bloque)
                descargado += len(bloque)
                if total:
                    pct = int(pct_ini + (pct_fin - pct_ini) * descargado / total)
                    self.progreso.emit(min(pct, pct_fin))


# ─────────────────────────────────────────────────────────────
#  Dialogo de actualizacion disponible
# ─────────────────────────────────────────────────────────────

class DialogoActualizacion(QDialog):
    def __init__(self, version_nueva: str, download_url: str,
                 version_actual: str, base_dir: str, parent=None):
        super().__init__(parent)
        self.version_nueva  = version_nueva
        self.download_url   = download_url
        self.base_dir       = base_dir
        self.setWindowTitle("Actualizacion disponible")
        self.setMinimumWidth(420)
        self.setModal(True)
        self._build_ui(version_actual)

    def _build_ui(self, version_actual: str):
        from PyQt6.QtCore import Qt
        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.setContentsMargins(24, 20, 24, 20)

        ico = QLabel("🆕")
        ico.setStyleSheet("font-size:36px;")
        ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(ico)

        titulo = QLabel("Hay una version nueva disponible!")
        titulo.setStyleSheet("font-size:15px;font-weight:700;color:#C9A84C;")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(titulo)

        info = QLabel(
            f"  Version actual:    <b>{version_actual}</b><br>"
            f"  Version nueva:     <b>{self.version_nueva}</b><br><br>"
            "La actualizacion reemplaza solo el codigo.<br>"
            "<b>Tus datos, ventas e historial no se tocan.</b>"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#CCCCCC;line-height:1.6;")
        lay.addWidget(info)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        self.progress.setStyleSheet(
            "QProgressBar{background:#2C2C2C;border-radius:4px;height:16px;}"
            "QProgressBar::chunk{background:#C9A84C;border-radius:4px;}"
        )
        lay.addWidget(self.progress)

        self.lbl_estado = QLabel("")
        self.lbl_estado.setStyleSheet("color:#999;font-size:11px;")
        self.lbl_estado.setVisible(False)
        lay.addWidget(self.lbl_estado)

        btn_row = QHBoxLayout()

        self.btn_omitir = QPushButton("Ahora no")
        self.btn_omitir.setObjectName("btn_secundario")
        self.btn_omitir.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_omitir)

        self.btn_actualizar = QPushButton("Actualizar ahora")
        self.btn_actualizar.setObjectName("btn_exito")
        self.btn_actualizar.setMinimumWidth(180)
        self.btn_actualizar.clicked.connect(self._iniciar_descarga)
        btn_row.addWidget(self.btn_actualizar)

        lay.addLayout(btn_row)

    def _iniciar_descarga(self):
        self.btn_actualizar.setEnabled(False)
        self.btn_omitir.setEnabled(False)
        self.progress.setVisible(True)
        self.lbl_estado.setVisible(True)
        self.lbl_estado.setText("Descargando actualizacion...")

        self._downloader = UpdateDownloader(
            self.download_url, self.base_dir, self.version_nueva
        )
        self._downloader.progreso.connect(self.progress.setValue)
        self._downloader.terminado.connect(self._descarga_terminada)
        self._downloader.start()

    def _descarga_terminada(self, exito: bool, mensaje: str):
        if exito:
            if mensaje == "REINICIAR":
                self.lbl_estado.setText("Instalando... cerrando app")
                QMessageBox.information(
                    self,
                    "Actualizando",
                    "La actualizacion esta instalandose.\n\n"
                    "La app se va a cerrar y volver a abrir\n"
                    "sola en unos segundos con la version nueva."
                )
                self.accept()
                # Marcar la ventana principal para que no pida confirmacion
                for w in QApplication.topLevelWidgets():
                    w._cerrar_para_actualizacion = True
                QApplication.quit()
            else:
                self.lbl_estado.setText("Actualizacion aplicada.")
                QMessageBox.information(
                    self,
                    "Actualizacion lista",
                    "La app se actualizo correctamente.\n\n"
                    "Cerra y volve a abrir la aplicacion para usar la nueva version."
                )
                self.accept()
        else:
            self.lbl_estado.setText(f"Error: {mensaje}")
            self.btn_omitir.setEnabled(True)
            QMessageBox.critical(
                self, "Error al actualizar",
                f"No se pudo descargar la actualizacion:\n{mensaje}\n\n"
                "Verifica la conexion a internet e intenta de nuevo."
            )
