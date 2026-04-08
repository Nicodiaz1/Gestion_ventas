@echo off
REM ─────────────────────────────────────────────────────────
REM  instalar_windows.bat  –  Instalador para Windows
REM ─────────────────────────────────────────────────────────
echo.
echo  ========================================
echo   Vinoteca - Instalacion de dependencias
echo  ========================================
echo.

REM Verificar Python
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Python no encontrado. Descargalo de https://python.org
    pause
    exit /b 1
)

echo [1/3] Instalando dependencias Python...
pip install PyQt6 matplotlib pandas openpyxl pyodbc

echo.
echo [2/3] Inicializando base de datos...
python -c "from db.database import init_db; init_db()"

echo.
echo [3/3] Creando acceso directo en el escritorio...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'Vinoteca.lnk')); $s.TargetPath = 'pythonw'; $s.Arguments = '\"' + (Get-Location).Path + '\main.py\"'; $s.WorkingDirectory = (Get-Location).Path; $s.IconLocation = 'shell32.dll,174'; $s.Save()"

echo.
echo  ========================================
echo   Instalacion completada exitosamente!
echo   Ejecuta 'python main.py' para iniciar
echo  ========================================
pause
