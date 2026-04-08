#!/bin/bash
# ─────────────────────────────────────────────────────────
#  instalar_mac.sh  –  Instalador para macOS
# ─────────────────────────────────────────────────────────
echo ""
echo "  ============================================"
echo "   Vinoteca - Instalación en macOS"
echo "  ============================================"
echo ""

echo "[1/3] Instalando dependencias..."
pip3 install PyQt6 matplotlib pandas openpyxl

echo ""
echo "[2/3] Inicializando base de datos..."
python3 -c "from db.database import init_db; init_db()"

echo ""
echo "[3/3] Dando permisos de ejecución..."
chmod +x main.py

echo ""
echo "  ============================================"
echo "   ✅  Instalación completada!"
echo "   Ejecutá: python3 main.py"
echo "  ============================================"
