#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$DIR/.venv/bin/python"
PYQT6="$("$PYTHON" -c "import PyQt6, os; print(os.path.join(os.path.dirname(PyQt6.__file__), 'Qt6'))")"
export QT_QPA_PLATFORM_PLUGIN_PATH="$PYQT6/plugins/platforms"
export QT_PLUGIN_PATH="$PYQT6/plugins"
unset QT_DEBUG_PLUGINS
cd "$DIR"
exec "$PYTHON" "$DIR/main.py" "$@"
