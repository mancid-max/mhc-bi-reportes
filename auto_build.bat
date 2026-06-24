@echo off
setlocal

set PROJECT_DIR=c:\Users\Lenovo\Desktop\BI REPORTES
set PYTHON="%PROJECT_DIR%\.venv\Scripts\python.exe"
set GIT="C:\Program Files\Git\cmd\git.exe"
set LOG="%PROJECT_DIR%\logs\auto_build.log"

cd /d "%PROJECT_DIR%"

echo [%date% %time%] Iniciando build... >> %LOG%

%PYTHON% scripts/build_static_site.py >> %LOG% 2>&1
if %ERRORLEVEL% neq 0 (
    echo [%date% %time%] ERROR: Build fallo >> %LOG%
    exit /b 1
)

%GIT% add docs/index.html docs/404.html seed/VENTAS-TOD-2026.CSV >> %LOG% 2>&1

%GIT% diff --cached --quiet
if %ERRORLEVEL% equ 0 (
    echo [%date% %time%] Sin cambios. >> %LOG%
    exit /b 0
)

%GIT% commit -m "Auto-actualizar BI Reportes %date% %time:~0,5%" >> %LOG% 2>&1
%GIT% push origin main >> %LOG% 2>&1

if %ERRORLEVEL% equ 0 (
    echo [%date% %time%] Publicado exitosamente. >> %LOG%
) else (
    echo [%date% %time%] ERROR: Push fallo >> %LOG%
    exit /b 1
)

endlocal
