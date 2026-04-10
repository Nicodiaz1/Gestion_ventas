# ─────────────────────────────────────────────────────────────
#  sync/updater.py  –  Actualizaciones automáticas desde GitHub
#
#  Flujo:
#  1. Al iniciar la app, UpdateChecker corre en background.
#  2. Consulta la API de GitHub para ver la última versión.
#  3. Si hay versión nueva, emite señal → se muestra diálogo.
#  4. Si el usuario acepta, descarga el ZIP, reemplaza los
#     archivos del código (preserva db/, exports/, config.py),
#     y pide reiniciar la app.
# ─────────────────────────────────────────────────────────────

import os
import sys
import shutil
import zipfile
import tempfile
import urllib.request
import urllib.error
import json

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QProgressBar, QMessageBox


# ─────────────────────────────────────────────────────────────
#  Thread: chequeo silencioso en background
# ─────────────────────────────────────────────────────────────

class UpdateChecker(QThread):
    """
    Corre en background al iniciar la app.
    Si hay versión nueva, emite `update_disponible(version, download_url)`.
    Si hay error de red lo ignora silenciosamente.
    """
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

            tag         = data.get("tag_name", "").lstrip("v")
            zipball_url = data.get("zipball_url", "")

            if not tag or not zipball_url:
                return

            if self._es_mas_nueva(tag, self.version_actual):
                self.update_disponible.emit(tag, zipball_url)

        except Exception:
            # Sin conexión o repo no configurado → ignorar
            pass

    @staticmethod
    def _es_mas_nueva(nueva: str, actual: str) -> bool:
        """Compara versiones numéricas tipo '1.3' > '1.0'."""
        try:
            def a_tuple(v):
                return tuple(int(x) for x in v.split("."))
            return a_tuple(nueva) > a_tuple(actual)
        except Exception:
            return False


# ─────────────────────────────────────────────────────────────
#  Thread: descarga + aplicación de la actualización
# ─────────────────────────────────────────────────────────────

class UpdateDownloader(QThread):
    """Descarga el ZIP de GitHub y reemplaza los archivos de la app."""
    progreso    = pyqtSignal(int)          # 0-100
    terminado   = pyqtSignal(bool, str)    # (exito, mensaje)

    # Carpetas y archivos que NUNCA se tocan (datos del negocio)
    PRESERVAR = {"db", "exports", ".venv", "__pycache__",
                 "config.py"}

    def __init__(self, download_url: str, base_dir: str, version_nueva: str = ""):
        super().__init__()
        self.download_url  = download_url
        self.base_dir      = base_dir
        self.version_nueva = version_nueva

    def run(self):
        tmp_zip  = None
        tmp_dir  = None
        try:
            # ── 1. Descargar ZIP ──────────────────────────────
            self.progreso.emit(5)
            req = urllib.request.Request(
                self.download_url,
                headers={"User-Agent": "Vinoteca-App-Updater/1.0"}
            )

            tmp_zip = tempfile.NamedTemporaryFile(
                suffix=".zip", delete=False)

            with urllib.request.urlopen(req, timeout=60) as resp:
                total = int(resp.headers.get("Content-Length") or 0)
                descargado = 0
                chunk = 65536
                while True:
                    bloque = resp.read(chunk)
                    if not bloque:
                        break
                    tmp_zip.write(bloque)
                    descargado += len(bloque)
                    if total:
                        pct = int(5 + 60 * descargado / total)
                        self.progreso.emit(min(pct, 65))

            tmp_zip.close()
            self.progreso.emit(65)

            # ── 2. Extraer ZIP a carpeta temporal ─────────────
            tmp_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(tmp_zip.name, "r") as zf:
                zf.extractall(tmp_dir)

            # El ZIP de GitHub tiene una carpeta raíz con nombre
            # tipo "usuario-repo-abc1234/", la buscamos.
            contenidos = os.listdir(tmp_dir)
            carpeta_raiz = os.path.join(tmp_dir, contenidos[0]) \
                if len(contenidos) == 1 and os.path.isdir(
                    os.path.join(tmp_dir, contenidos[0])) \
                else tmp_dir

            self.progreso.emit(70)

            # ── 3. Copiar archivos nuevos (sin pisar datos) ───
            for item in os.listdir(carpeta_raiz):
                if item in self.PRESERVAR:
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

            # Escribir version_stamp.txt
            if self.version_nueva:
                try:
                    stamp = os.path.join(self.base_dir, "version_stamp.txt")
                    with open(stamp, "w", encoding="utf-8") as f:
                        f.write(self.version_nueva)
                except Exception:
                    pass

            # Si corre como .exe de PyInstaller, actualizar el acceso directo
            # para que apunte a pythonw (el .exe no puede actualizarse a sí mismo)
            if getattr(sys, "frozen", False):
                self._migrar_acceso_directo_a_python()

            self.terminado.emit(True, "")

        except Exception as e:
            self.terminado.emit(False, str(e))
        finally:
            if tmp_zip and os.path.exists(tmp_zip.name):
                os.unlink(tmp_zip.name)
            if tmp_dir and os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)

    def _migrar_acceso_directo_a_python(self):
        """Actualiza el acceso directo del escritorio para usar pythonw en lugar
        del .exe empaquetado. Así las próximas aperturas corren el código nuevo."""
        import subprocess, shutil as _shutil

        # 1. Encontrar pythonw.exe
        pythonw = _shutil.which("pythonw") or _shutil.which("pythonw.exe")
        if not pythonw:
            username = os.environ.get("USERNAME", "")
            candidatos = [
                r"C:\Python311\pythonw.exe",
                r"C:\Python312\pythonw.exe",
                r"C:\Python313\pythonw.exe",
                r"C:\Python310\pythonw.exe",
                rf"C:\Users\{username}\AppData\Local\Programs\Python\Python311\pythonw.exe",
                rf"C:\Users\{username}\AppData\Local\Programs\Python\Python312\pythonw.exe",
                rf"C:\Users\{username}\AppData\Local\Programs\Python\Python313\pythonw.exe",
                rf"C:\Users\{username}\AppData\Local\Programs\Python\Python310\pythonw.exe",
            ]
            for c in candidatos:
                if os.path.exists(c):
                    pythonw = c
                    break

        if not pythonw:
            return  # Python no está instalado, no se puede migrar

        main_py  = os.path.join(self.base_dir, "main.py")
        icon_ico = os.path.join(self.base_dir, "assets", "icon.ico")
        desktop  = os.path.join(os.path.expanduser("~"), "Desktop")
        lnk      = os.path.join(desktop, "Vinoteca.lnk")

        # Escapar rutas para PowerShell
        pw  = pythonw.replace("\\", "\\\\")
        mp  = main_py.replace("\\", "\\\\")
        ico = icon_ico.replace("\\", "\\\\")
        lnk_ps = lnk.replace("\\", "\\\\")
        wd  = self.base_dir.replace("\\", "\\\\")

        ps = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut("{lnk_ps}"); '
            f'$s.TargetPath = "{pw}"; '
            f'$s.Arguments = \'"'{mp}"\'; '
            f'$s.WorkingDirectory = "{wd}"; '
            f'$s.IconLocation = "{ico}"; '
            f'$s.Save()'
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True, timeout=15
            )
        except Exception:
            pass  # Si falla, al menos el código nuevo está en disco


# ─────────────────────────────────────────────────────────────
#  Diálogo de actualización disponible
# ─────────────────────────────────────────────────────────────

class DialogoActualizacion(QDialog):
    def __init__(self, version_nueva: str, download_url: str,
                 version_actual: str, base_dir: str, parent=None):
        super().__init__(parent)
        self.version_nueva  = version_nueva
        self.download_url   = download_url
        self.base_dir       = base_dir
        self.setWindowTitle("Actualización disponible")
        self.setMinimumWidth(420)
        self.setModal(True)
        self._build_ui(version_actual)

    def _build_ui(self, version_actual: str):
        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.setContentsMargins(24, 20, 24, 20)

        ico = QLabel("🆕")
        ico.setStyleSheet("font-size:36px;")
        ico.setAlignment(__import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(ico)

        titulo = QLabel("¡Hay una versión nueva disponible!")
        titulo.setStyleSheet("font-size:15px;font-weight:700;color:#C9A84C;")
        titulo.setAlignment(__import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(titulo)

        info = QLabel(
            f"  Versión actual:    <b>{version_actual}</b><br>"
            f"  Versión nueva:     <b>{self.version_nueva}</b><br><br>"
            "La actualización reemplaza solo el código.<br>"
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

        self.btn_actualizar = QPushButton("⬇  Actualizar ahora")
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
        self.lbl_estado.setText("Descargando actualización…")

        self._downloader = UpdateDownloader(self.download_url, self.base_dir, self.version_nueva)
        self._downloader.progreso.connect(self.progress.setValue)
        self._downloader.terminado.connect(self._descarga_terminada)
        self._downloader.start()

    def _descarga_terminada(self, exito: bool, error: str):
        if exito:
            self.lbl_estado.setText("✅  Actualización aplicada.")
            import sys as _sys
            if getattr(_sys, "frozen", False):
                msg = (
                    "✅  Actualización descargada correctamente.\n\n"
                    "El acceso directo del escritorio fue actualizado.\n\n"
                    "👉  Cerrá la app y volvé a abrirla desde el ícono del escritorio.\n"
                    "    La próxima vez ya vas a tener la versión nueva."
                )
            else:
                msg = (
                    "✅  La app se actualizó correctamente.\n\n"
                    "Cerrá y volvé a abrir la aplicación para usar la nueva versión."
                )
            QMessageBox.information(self, "Actualización lista", msg)
            self.accept()
        else:
            self.lbl_estado.setText(f"❌  Error: {error}")
            self.btn_omitir.setEnabled(True)
            QMessageBox.critical(
                self, "Error al actualizar",
                f"No se pudo descargar la actualización:\n{error}\n\n"
                "Verificá la conexión a internet e intentá de nuevo."
            )
