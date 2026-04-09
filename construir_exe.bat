@echo off
setlocal enabledelayedexpansion
REM ================================================================
REM  construir_exe.bat  - Genera Vinoteca.exe para Windows
REM  Ejecutar UNA sola vez (o cada vez que actualices la app).
REM ================================================================

echo.
echo  ================================================
echo   VINOTECA  -  Construir .exe
echo  ================================================
echo.

REM ── Posicionarse en la carpeta del script ───────────────────────────────────
cd /d "%~dp0"

REM ── 1. Verificar Python ─────────────────────────────────────────────────────
echo [1/6] Verificando Python...
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo.
    echo  [ERROR] Python no encontrado.
    echo  Descargalo de https://python.org
    echo  Durante la instalacion marca: "Add Python to PATH"
    echo.
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do echo         %%v encontrado.

REM ── 2. Instalar dependencias ─────────────────────────────────────────────────
echo.
echo [2/6] Instalando dependencias ^(puede tardar unos minutos la primera vez^)...
pip install PyQt6 matplotlib pandas openpyxl pyodbc pillow pyinstaller --quiet --upgrade
IF ERRORLEVEL 1 (
    echo  [ERROR] Fallo la instalacion de dependencias.
    echo  Verificar conexion a internet y permisos.
    pause & exit /b 1
)
echo         Dependencias OK.

REM ── 3. Generar ícono ─────────────────────────────────────────────────────────
echo.
echo [3/6] Generando icono de la copa de vino...
python assets\crear_icono.py
IF ERRORLEVEL 1 (
    echo  [ERROR] No se pudo generar el icono.
    pause & exit /b 1
)

REM ── 4. Inicializar base de datos ─────────────────────────────────────────────
echo.
echo [4/6] Inicializando base de datos...
python -c "from db.database import init_db; init_db()"
IF ERRORLEVEL 1 (
    echo  [ERROR] Fallo la inicializacion de la base de datos.
    pause & exit /b 1
)
echo         Base de datos lista.

REM ── 5. Compilar ejecutable ───────────────────────────────────────────────────
echo.
echo [5/6] Compilando ejecutable ^(2-5 minutos^)...
echo       Esto solo hay que hacerlo una vez.
echo.
pyinstaller vinoteca.spec --noconfirm --clean
IF ERRORLEVEL 1 (
    echo.
    echo  [ERROR] Fallo la compilacion.
    echo  Revisa que no haya errores en los modulos de la app.
    pause & exit /b 1
)

REM -- 6. Crear acceso directo en el Escritorio -----------------------------------
echo.
echo [6/6] Creando acceso directo en el Escritorio...

set "EXEPATH=%~dp0dist\Vinoteca\Vinoteca.exe"
set "WORKDIR=%~dp0dist\Vinoteca"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$exe = $env:EXEPATH; $work = $env:WORKDIR; $ws = New-Object -ComObject WScript.Shell; $dt = [Environment]::GetFolderPath('Desktop'); $sc = $ws.CreateShortcut($dt + '\Vinoteca.lnk'); $sc.TargetPath = $exe; $sc.WorkingDirectory = $work; $sc.IconLocation = $exe + ',0'; $sc.Description = 'Sistema de Gestion La Vinoteca'; $sc.Save(); Write-Host 'Acceso directo creado.'"

IF ERRORLEVEL 1 (
    echo  [AVISO] No se pudo crear el acceso directo automaticamente.
    echo  Podes crearlo manualmente: clic derecho en
    echo  "%~dp0dist\Vinoteca\Vinoteca.exe" y elegir "Enviar a - Escritorio"
)

REM -- Listo -----------------------------------------------------------------------
echo.
echo  ================================================
echo   LISTO! Ahora tenes en el Escritorio:
echo.
echo     Vinoteca  (icono de la app)
echo.
echo   Doble clic para abrir todos los dias.
echo   No hace falta Python ni CMD para usarla.
echo  ================================================
echo.
echo  Ubicacion del ejecutable:
echo  %~dp0dist\Vinoteca\Vinoteca.exe
echo.
pause
