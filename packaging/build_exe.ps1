# Build the DigiRaksha one-file EXE — v0.3.0 (AI Assist + Multilingual Detection)
#
# Prereqs:  Node + npm (for the frontend build) and Python with PyInstaller
# Output:   dist\DigiRaksha.exe & DigiRaksha.exe (single file; run on any machine)
#
# Run from repository root:
#   powershell -ExecutionPolicy Bypass -File packaging\build_exe.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

# 0. Find python interpreter with PyInstaller
$candidatePy = @(
    (Join-Path $Root "backend\.venv\Scripts\python.exe"),
    (Join-Path $Root ".venv\Scripts\python.exe"),
    "C:\dr-venv\Scripts\python.exe",
    ((Get-Command python -ErrorAction SilentlyContinue).Source)
)

$Py = $null
foreach ($cand in $candidatePy) {
    if ($cand -and (Test-Path $cand)) {
        $Py = $cand
        break
    }
}

if (-not $Py) { throw "Python not found in .venv or system. Please install Python 3.12." }
Write-Host "[build] Using Python: $Py"

Write-Host "[build] Ensuring PyInstaller is ready..."
& $Py -m pip install --quiet pyinstaller
if ($LASTEXITCODE -ne 0) { throw "pyinstaller install failed" }

Write-Host "[build] Building frontend bundle (npm run build)..."
Push-Location frontend
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "npm run build failed" }
} finally {
    Pop-Location
}

# Verify embedded assets exist before bundling
$static = Join-Path $Root "backend\app\static\index.html"
$model  = Join-Path $Root "data\models\scam_classifier.joblib"
if (-not (Test-Path $static)) { throw "Built SPA missing: $static (run npm run build)" }
if (-not (Test-Path $model))  { throw "Classifier model missing: $model" }

# Strip bytecode caches from the source tree so they don't bloat the EXE
Get-ChildItem -Path (Join-Path $Root "backend\app") -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force -Confirm:$false

Write-Host "[build] Configuring PyInstaller embedded assets..."
$out = Join-Path $Root "dist"
$srcBackend    = Join-Path $Root "backend\app"
$srcModel      = Join-Path $Root "data\models\scam_classifier.joblib"
$srcAasist     = Join-Path $Root "data\models\aasist.pth"
$srcVoiceModel = Join-Path $Root "data\models\voice_clone_classifier.joblib"
$srcMesonet    = Join-Path $Root "data\models\mesonet"
$srcEcapa      = Join-Path $Root "data\models\ecapa-tdnn"
$srcReq        = Join-Path $Root "packaging\requirements.txt"

$addDataArgs = @(
    "--add-data", "$srcBackend;backend\app",
    "--add-data", "$srcModel;data\models",
    "--add-data", "$srcReq;packaging"
)

if (Test-Path $srcAasist) {
    Write-Host "[build] Bundling aasist.pth..."
    $addDataArgs += "--add-data"
    $addDataArgs += "$srcAasist;data\models"
}

if (Test-Path $srcVoiceModel) {
    Write-Host "[build] Bundling voice_clone_classifier.joblib..."
    $addDataArgs += "--add-data"
    $addDataArgs += "$srcVoiceModel;data\models"
}

if (Test-Path $srcMesonet) {
    Write-Host "[build] Bundling mesonet models..."
    $addDataArgs += "--add-data"
    $addDataArgs += "$srcMesonet;data\models\mesonet"
}

if (Test-Path $srcEcapa) {
    Write-Host "[build] Bundling ECAPA-TDNN speaker embeddings..."
    $addDataArgs += "--add-data"
    $addDataArgs += "$srcEcapa;data\models\ecapa-tdnn"
}

Write-Host "[build] Running PyInstaller (onefile console)..."
& $Py -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --name "DigiRaksha" `
    --console `
    @addDataArgs `
    --distpath $out `
    --workpath (Join-Path $Root "build\pyinstaller") `
    --specpath (Join-Path $Root "build\spec") `
    "packaging\launcher.py"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$exe = Join-Path $out "DigiRaksha.exe"
if (-not (Test-Path $exe)) { throw "EXE not produced: $exe" }

# Copy to root as well for convenience
$rootExe = Join-Path $Root "DigiRaksha.exe"
Copy-Item $exe $rootExe -Force

$size = (Get-Item $exe).Length / 1MB
$sizeMb = "{0:N1}" -f $size
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "[build] SUCCESS: DigiRaksha.exe successfully created!" -ForegroundColor Green
Write-Host "[build] Location 1: $exe  ($sizeMb MB)" -ForegroundColor Cyan
Write-Host "[build] Location 2: $rootExe  ($sizeMb MB)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Green
Write-Host "[build] Behavior when double-clicked by any user:"
Write-Host "        - If files/dependencies exist: skips download and launches immediately."
Write-Host "        - If files/dependencies missing: auto-downloads & sets up, then launches."
