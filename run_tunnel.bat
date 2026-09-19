@echo off
title DigiRaksha - Cloudflare Collaboration Tunnel
cd /d "%~dp0"

echo =======================================================
echo     DigiRaksha Public Cloudflare Tunnel Launcher
echo =======================================================
echo.

if not exist "%~dp0cloudflared.exe" (
    echo [INFO] cloudflared.exe not found locally.
    echo [INFO] Downloading official cloudflared for Windows...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile '%~dp0cloudflared.exe'"
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to download cloudflared.exe. Please download it manually from:
        echo https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
        pause
        exit /b 1
    )
)

echo [INFO] Starting Cloudflare Tunnel pointing to http://127.0.0.1:8000 ...
echo [INFO] Look for your public URL below (e.g. https://xxxx.trycloudflare.com):
echo.

"%~dp0cloudflared.exe" tunnel --url http://127.0.0.1:8000
pause
