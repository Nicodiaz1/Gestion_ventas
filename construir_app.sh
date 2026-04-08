#!/bin/bash
# ╔═══════════════════════════════════════════════════════════════╗
# ║  construir_app.sh  –  Genera Vinoteca.app para macOS         ║
# ║                                                               ║
# ║  Ejecutar: chmod +x construir_app.sh && ./construir_app.sh   ║
# ╚═══════════════════════════════════════════════════════════════╝

set -e   # detener si hay error

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔════════════════════════════════════════════╗"
echo "║     VINOTECA  –  Construir .app macOS      ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# ── 1. Dependencias ──────────────────────────────────────────────────────────
echo "[1/5] Instalando dependencias..."
pip3 install PyQt6 matplotlib pandas openpyxl pillow pyinstaller --quiet --upgrade
echo "      Dependencias OK."

# ── 2. Generar ícono PNG ──────────────────────────────────────────────────────
echo ""
echo "[2/5] Generando ícono de la copa de vino..."
python3 assets/crear_icono.py

# ── 3. Convertir PNG → .icns  (herramientas nativas de macOS) ────────────────
echo ""
echo "[3/5] Convirtiendo ícono a formato macOS (.icns)..."

ICONSET="assets/icon.iconset"
mkdir -p "$ICONSET"

# Generar todos los tamaños requeridos por macOS
sips -z 16    16    assets/icon.png --out "$ICONSET/icon_16x16.png"        2>/dev/null
sips -z 32    32    assets/icon.png --out "$ICONSET/icon_16x16@2x.png"     2>/dev/null
sips -z 32    32    assets/icon.png --out "$ICONSET/icon_32x32.png"        2>/dev/null
sips -z 64    64    assets/icon.png --out "$ICONSET/icon_32x32@2x.png"     2>/dev/null
sips -z 128   128   assets/icon.png --out "$ICONSET/icon_128x128.png"      2>/dev/null
sips -z 256   256   assets/icon.png --out "$ICONSET/icon_128x128@2x.png"   2>/dev/null
sips -z 256   256   assets/icon.png --out "$ICONSET/icon_256x256.png"      2>/dev/null
sips -z 512   512   assets/icon.png --out "$ICONSET/icon_256x256@2x.png"   2>/dev/null
sips -z 512   512   assets/icon.png --out "$ICONSET/icon_512x512.png"      2>/dev/null
sips -z 1024  1024  assets/icon.png --out "$ICONSET/icon_512x512@2x.png"   2>/dev/null

iconutil -c icns "$ICONSET" -o assets/icon.icns
rm -rf "$ICONSET"
echo "      icon.icns creado."

# ── 4. Compilar .app con PyInstaller ─────────────────────────────────────────
echo ""
echo "[4/5] Compilando .app (2-5 minutos)..."
echo "      Esto solo hay que hacerlo una vez."
echo ""

pyinstaller main.py \
    --name              "Vinoteca"               \
    --windowed                                    \
    --icon              "assets/icon.icns"        \
    --add-data          "assets:assets"           \
    --hidden-import     "PyQt6.sip"               \
    --hidden-import     "matplotlib.backends.backend_qtagg" \
    --hidden-import     "matplotlib.backends.backend_pdf"   \
    --hidden-import     "openpyxl"                \
    --hidden-import     "openpyxl.cell._writer"   \
    --exclude-module    "tkinter"                 \
    --exclude-module    "_tkinter"                \
    --noconfirm                                   \
    --clean

# ── 5. Instalar en /Applications y crear acceso en Escritorio ────────────────
echo ""
echo "[5/5] Instalando en /Applications..."

APP_SRC="$SCRIPT_DIR/dist/Vinoteca.app"
APP_DST="/Applications/Vinoteca.app"
DESKTOP="$HOME/Desktop"

if [ -d "$APP_SRC" ]; then
    # Copiar a /Applications (puede pedir contraseña si es necesario)
    if cp -r "$APP_SRC" "$APP_DST" 2>/dev/null; then
        echo "      Vinoteca.app copiado a /Applications"
    else
        echo "      (Sin permisos para /Applications — la app queda en dist/Vinoteca.app)"
        APP_DST="$APP_SRC"
    fi

    # Crear alias en el Escritorio
    osascript 2>/dev/null <<EOF
tell application "Finder"
    make alias file to POSIX file "$APP_DST" at POSIX file "$DESKTOP"
    set name of result to "Vinoteca"
end tell
EOF
    if [ $? -eq 0 ]; then
        echo "      Acceso directo creado en el Escritorio."
    else
        echo "      (Creá el acceso manualmente: arrastrá Vinoteca.app al Escritorio)"
    fi
fi

echo ""
echo "╔════════════════════════════════════════════╗"
echo "║  ✅  Listo! Encontrás Vinoteca.app en:     ║"
echo "║                                            ║"
echo "║    /Applications/Vinoteca.app              ║"
echo "║    ~/Desktop/Vinoteca  (acceso directo)    ║"
echo "║                                            ║"
echo "║  Doble clic para abrir todos los días.     ║"
echo "╚════════════════════════════════════════════╝"
echo ""
