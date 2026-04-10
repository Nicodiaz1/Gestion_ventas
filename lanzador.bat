@echo off
REM ================================================================
REM  lanzador.bat  -  Lanzador de Vinoteca (sin .exe)
REM
REM  Si venias usando el .exe compilado y estas viendo esto,
REM  solo hace DOBLE CLIC en este archivo UNA VEZ.
REM  El acceso directo del escritorio se va a actualizar
REM  automaticamente y todo va a funcionar bien.
REM ================================================================

cd /d "%~dp0"

REM -- Buscar pythonw.exe en ubicaciones comunes -------------------
set "PYTHONW="

for %%P in (pythonw.exe) do (
    if not "%%~$PATH:P"=="" set "PYTHONW=%%~$PATH:P"
)

if "%PYTHONW%"=="" (
    for %%D in (
        "C:\Python313" "C:\Python312" "C:\Python311" "C:\Python310"
        "%LOCALAPPDATA%\Programs\Python\Python313"
        "%LOCALAPPDATA%\Programs\Python\Python312"
        "%LOCALAPPDATA%\Programs\Python\Python311"
        "%LOCALAPPDATA%\Programs\Python\Python310"
    ) do (
        if exist "%%~D\pythonw.exe" (
            if "%PYTHONW%"=="" set "PYTHONW=%%~D\pythonw.exe"
        )
    )
)

if "%PYTHONW%"=="" (
    echo.
    echo  [ERROR] No se encontro pythonw.exe.
    echo  Por favor instala Python desde https://python.org
    echo  y marca "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b 1
)

REM -- Actualizar el acceso directo del escritorio -----------------
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $dt = [Environment]::GetFolderPath('Desktop'); ^
   $sc = $ws.CreateShortcut($dt + '\Vinoteca.lnk'); ^
   $sc.TargetPath = '%PYTHONW%'; ^
   $sc.Arguments = '\"' + '%~dp0main.py' + '\"'; ^
   $sc.WorkingDirectory = '%~dp0'; ^
   $sc.IconLocation = '%~dp0assets\icon.ico'; ^
   $sc.Description = 'Sistema de Gestion La Vinoteca'; ^
   $sc.Save()" >nul 2>&1

REM -- Lanzar la app -----------------------------------------------
start "" "%PYTHONW%" "%~dp0main.py"
