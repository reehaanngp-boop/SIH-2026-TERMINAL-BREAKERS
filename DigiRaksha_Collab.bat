@echo off
title DigiRaksha - Collab Launcher (Backend + Tunnel)
cd /d "%~dp0"

echo =======================================================
echo     DigiRaksha Multi-User Collaboration Launcher
echo =======================================================
echo.

:: 1. Launch backend in a separate terminal window
echo [1/2] Launching Backend Server on port 8000...
start "DigiRaksha Backend Server" cmd /k "cd /d "%~dp0" && call DigiRaksha.bat"

:: Wait 3 seconds for backend to initialize
timeout /t 3 /nobreak >nul

:: 2. Launch Cloudflare Tunnel
echo [2/2] Launching Cloudflare Tunnel...
echo.
echo =========================================================================
echo Share the generated https://xxxx.trycloudflare.com URL with your team!
echo Teammates can paste it into the Settings page of the Cloudflare Pages app.
echo =========================================================================
echo.

call "%~dp0run_tunnel.bat"
