@echo off
REM ─────────────────────────────────────────────────────────
REM  instalar_windows.bat  –  Instalador para Windows
REM  Doble clic para instalar todo automáticamente.
REM ─────────────────────────────────────────────────────────
echo.
echo  ========================================
echo   Vinoteca - Instalacion automatica
echo  ========================================
echo.

REM ── Paso 1: Verificar / instalar Python ──────────────────
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [1/4] Python no encontrado. Instalando automaticamente...
    echo       Esto puede tardar unos minutos, espera...
    echo.

    REM Intentar con winget (Windows 10/11 con App Installer)
    winget --version >nul 2>&1
    IF NOT ERRORLEVEL 1 (
        winget install --id Python.Python.3.11 --source winget --silent --accept-package-agreements --accept-source-agreements
    ) ELSE (
        REM Fallback: descargar el instalador de Python con PowerShell
        echo       Descargando instalador de Python...
        powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
        echo       Instalando Python (requiere permisos de administrador)...
        "%TEMP%\python_installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
        del "%TEMP%\python_installer.exe"
    )

    REM Recargar PATH para que python esté disponible
    call refreshenv >nul 2>&1
    python --version >nul 2>&1
    IF ERRORLEVEL 1 (
        echo.
        echo [ERROR] No se pudo instalar Python automaticamente.
        echo         Por favor instala Python manualmente desde https://python.org
        echo         y vuelve a ejecutar este archivo.
        pause
        exit /b 1
    )
    echo       Python instalado correctamente.
) ELSE (
    echo [1/4] Python ya esta instalado. OK
)
echo.

REM ── Paso 2: Instalar dependencias ────────────────────────
echo [2/4] Instalando dependencias Python...
pip install --quiet PyQt6 matplotlib pandas openpyxl pyodbc Pillow
IF ERRORLEVEL 1 (
    echo [ERROR] Fallo la instalacion de dependencias.
    pause
    exit /b 1
)
echo       Dependencias instaladas. OK
echo.

REM ── Paso 3: Inicializar base de datos ────────────────────
echo [3/4] Inicializando base de datos...
python -c "from db.database import init_db; init_db()"
IF ERRORLEVEL 1 (
    echo [ERROR] Fallo al inicializar la base de datos.
    pause
    exit /b 1
)
echo       Base de datos lista. OK
echo.

REM ── Paso 4: Acceso directo en el escritorio ──────────────
echo [4/4] Creando acceso directo en el escritorio...

REM Eliminar acceso directo viejo al .exe si existe
IF EXIST "%USERPROFILE%\Desktop\Vinoteca.lnk" del "%USERPROFILE%\Desktop\Vinoteca.lnk"

powershell -Command "$appDir = (Get-Location).Path; $pyExe = python -c 'import sys,os; print(os.path.join(os.path.dirname(sys.executable), \"pythonw.exe\"))'; if (-not (Test-Path $pyExe)) { $pyExe = 'pythonw' }; $ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'Vinoteca.lnk')); $s.TargetPath = $pyExe; $s.Arguments = '\"' + $appDir + '\main.py\"'; $s.WorkingDirectory = $appDir; $s.IconLocation = $appDir + '\assets\icon.ico'; $s.Save()"
echo       Acceso directo creado en el escritorio. OK
echo.

echo  ========================================
echo   Instalacion completada correctamente!
echo   Usa el acceso directo "Vinoteca" del 
echo   escritorio para abrir la aplicacion.
echo  ========================================
echo.
pause
