# ─────────────────────────────────────────────────────────────
#  vinoteca.spec  –  Spec de PyInstaller para Windows
#
#  Genera: dist\Vinoteca\Vinoteca.exe  (carpeta auto-contenida)
#
#  Uso:
#    pyinstaller vinoteca.spec --noconfirm --clean
#
#  O más fácil: ejecutar  construir_exe.bat
# ─────────────────────────────────────────────────────────────

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        # Incluir la carpeta de assets (íconos, etc.)
        ("assets", "assets"),
    ],
    hiddenimports=[
        # PyQt6
        "PyQt6.sip",
        "PyQt6.QtCore",
        "PyQt6.QtWidgets",
        "PyQt6.QtGui",
        "PyQt6.QtPrintSupport",
        # matplotlib
        "matplotlib.backends.backend_qtagg",
        "matplotlib.backends.backend_pdf",
        "matplotlib.backends.backend_svg",
        "matplotlib.figure",
        # pandas / openpyxl
        "pandas._libs.tslibs.base",
        "pandas._libs.tslibs.timezones",
        "openpyxl",
        "openpyxl.cell._writer",
        # stdlib
        "sqlite3",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Excluir módulos innecesarios para reducir tamaño
    excludes=[
        "tkinter",
        "_tkinter",
        "matplotlib.backends.backend_tkagg",
        "matplotlib.backends.backend_wx",
        "wx",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Vinoteca",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,           # UPX puede hacer saltar antivirus; mejor desactivado
    console=False,       # Sin ventana de consola negra al abrir
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",
)

# COLLECT genera la carpeta dist\Vinoteca\ con el .exe + todas las DLLs
# Es más rápido de arrancar que --onefile porque no extrae a un temp cada vez.
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Vinoteca",
)
