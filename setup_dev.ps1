# ============================================================================
#  setup_dev.ps1 — One-time setup for DigiRaksha on a Windows laptop
#
#  What it does:
#    1. Checks you have Python 3.12 and Node.js
#    2. Creates a private virtual environment  (.venv)  — nothing touches
#       your system Python
#    3. Installs PyTorch (CPU-only build — small & fast)
#    4. Installs the backend + all AI libraries
#    5. Installs the frontend (React / Vite) dependencies
#
#  Run it like this (from the project folder):
#     powershell -ExecutionPolicy Bypass -File setup_dev.ps1
#
#  It is safe to re-run — it skips anything already installed.
# ============================================================================

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Write-Step($msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Fail($msg) { Write-Host "    [FAIL] $msg" -ForegroundColor Red }

# ---------------------------------------------------------------------------
# 1. Find Python 3.12 (the ML audio libraries need exactly 3.12)
# ---------------------------------------------------------------------------
$pyCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3.12 --version 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $pyCmd = "py -3.12" }
}
if (-not $pyCmd) {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $ver = python -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($ver -eq "3.12") { $pyCmd = "python" }
    }
}
if (-not $pyCmd) {
    Write-Fail "Python 3.12 was not found."
    Write-Host  "    Install it from https://www.python.org/downloads/ and make sure you"
    Write-Host  "    tick 'Add python.exe to PATH' during installation."
    exit 1
}
Write-Ok "Python 3.12 found ($pyCmd)"

# ---------------------------------------------------------------------------
# 2. Check Node.js
# ---------------------------------------------------------------------------
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Fail "Node.js was not found. Install the LTS version from https://nodejs.org/"
    exit 1
}
Write-Ok "Node.js found ($(node --version))"

# ---------------------------------------------------------------------------
# 3. Create the virtual environment
# ---------------------------------------------------------------------------
$VenvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $VenvPy) {
    Write-Ok "Virtual environment already exists - reusing it"
} else {
    Write-Step "Creating the Python virtual environment (.venv) ..."
    Invoke-Expression "& $pyCmd -m venv `"$Root\.venv`""
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPy)) {
        Write-Fail "Could not create the virtual environment."
        Write-Host  "    If the path above is very long, move the project to a short folder"
        Write-Host  "    like C:\sih\SIH-2026-TERMINAL-BREAKERS and try again."
        exit 1
    }
    Write-Ok "Virtual environment created"
}

# ---------------------------------------------------------------------------
# 4. Install PyTorch (CPU build from the official index)
# ---------------------------------------------------------------------------
Write-Step "Installing PyTorch (CPU-only build) ..."
& $VenvPy -m pip install --disable-pip-version-check --quiet --upgrade pip
& $VenvPy -m pip install --disable-pip-version-check torch --index-url https://download.pytorch.org/whl/cpu
if ($LASTEXITCODE -ne 0) {
    Write-Fail "PyTorch install failed. Check your internet connection and try again."
    exit 1
}
Write-Ok "PyTorch installed"

# ---------------------------------------------------------------------------
# 5. Install backend + AI libraries
# ---------------------------------------------------------------------------
Write-Step "Installing the backend and AI libraries (this is the big one - 5-10 min) ..."
Push-Location (Join-Path $Root "backend")
& $VenvPy -m pip install --disable-pip-version-check -e ".[ml]"
$backendExit = $LASTEXITCODE
Pop-Location
if ($backendExit -ne 0) {
    Write-Fail "Backend install failed. Check your internet connection and try again."
    exit 1
}
Write-Ok "Backend installed"

# ---------------------------------------------------------------------------
# 6. Install frontend dependencies
# ---------------------------------------------------------------------------
Write-Step "Installing the frontend (React/Vite) dependencies ..."
Push-Location (Join-Path $Root "frontend")
npm install --include=dev
$frontExit = $LASTEXITCODE
Pop-Location
if ($frontExit -ne 0) {
    Write-Fail "Frontend install failed. Check your internet connection and try again."
    exit 1
}
Write-Ok "Frontend installed"

# ---------------------------------------------------------------------------
# 7. Done
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "    SETUP COMPLETE! You can now run DigiRaksha. " -ForegroundColor Green
Write-Host ""
Write-Host "  To run it, open TWO PowerShell windows:" -ForegroundColor Yellow
Write-Host ""
Write-Host "    Window 1 - backend:" -ForegroundColor Cyan
Write-Host "        cd `"$Root\backend`""
Write-Host "        ..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
Write-Host ""
Write-Host "    Window 2 - frontend:" -ForegroundColor Cyan
Write-Host "        cd `"$Root\frontend`""
Write-Host "        npm run dev"
Write-Host ""
Write-Host "    Then open http://localhost:5173 in your browser." -ForegroundColor Green
Write-Host "    Full instructions: see docs\TEAM_SETUP.md"
