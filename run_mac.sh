#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
PYQT6="$DIR/.venv/lib/python3.14/site-packages/PyQt6/Qt6"
export QT_QPA_PLATFORM_PLUGIN_PATH="$PYQT6/plugins/platforms"
export QT_PLUGIN_PATH="$PYQT6/plugins"
cd "$DIR"
exec "$DIR/.venv/bin/python3.14" "$DIR/main.py" "$@"
