@echo off
title DigiRaksha - AI Scam Shield
cd /d "%~dp0"

echo =======================================================
echo          Starting DigiRaksha Platform...
echo =======================================================
echo.
echo Server: http://127.0.0.1:8000
echo.

:: Check local python dev environment first (for active development)
if exist "%~dp0backend\.venv\Scripts\python.exe" (
    echo [INFO] Running via backend\.venv\Scripts\python.exe
    cd /d "%~dp0backend"
    "%~dp0backend\.venv\Scripts\python.exe" -m app.main
    goto :done
)
if exist "%~dp0backend\.venv\Scripts\digiraksha.exe" (
    echo [INFO] Running in dev mode via backend\.venv\Scripts\digiraksha.exe
    "%~dp0backend\.venv\Scripts\digiraksha.exe"
    goto :done
)
if exist "%~dp0.venv\Scripts\digiraksha.exe" (
    echo [INFO] Running in dev mode via .venv\Scripts\digiraksha.exe
    "%~dp0.venv\Scripts\digiraksha.exe"
    goto :done
)

:: Standalone packaged EXE
if exist "%~dp0DigiRaksha.exe" (
    "%~dp0DigiRaksha.exe"
    goto :done
)
if exist "%~dp0dist\DigiRaksha.exe" (
    "%~dp0dist\DigiRaksha.exe"
    goto :done
)

echo [ERROR] Python environment or DigiRaksha.exe not found.
echo Expected at: %~dp0backend\.venv\Scripts\python.exe
echo.
pause
exit /b 1

:done
if %ERRORLEVEL% neq 0 (
    echo.
    echo [Server exited with code %ERRORLEVEL%]
    pause
)
