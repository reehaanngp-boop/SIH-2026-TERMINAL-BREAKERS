# Build the DigiRaksha one-file EXE.
#
# Prereqs:  Node + npm (for the frontend build) and a Python 3.12 venv with
#           PyInstaller installed (e.g. C:\dr-venv as used below).
# Output:   dist\DigiRaksha.exe  (single file; run it on a new machine)
#
# Run from the repository root:
#   powershell -ExecutionPolicy Bypass -File packaging\build_exe.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

# 0. Sanity: PyInstaller must be importable in the build venv.
$Py = "C:\dr-venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    $Py = (Get-Command python -ErrorAction SilentlyContinue).Source
}
if (-not $Py) { throw "Python not found. Set up C:\dr-venv or install python first." }

Write-Host "[build] Frontend build (npm run build)…"
Push-Location frontend
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "npm run build failed" }
} finally {
    Pop-Location
}

Write-Host "[build] Ensure PyInstaller…"
& $Py -m pip install --quiet pyinstaller
if ($LASTEXITCODE -ne 0) { throw "pyinstaller install failed" }

# Verify embedded assets exist before bundling.
$static = Join-Path $Root "backend\app\static\index.html"
$model  = Join-Path $Root "data\models\scam_classifier.joblib"
if (-not (Test-Path $static)) { throw "Built SPA missing: $static (run npm run build)" }
if (-not (Test-Path $model))  { throw "Classifier model missing: $model" }

# Strip bytecode caches from the source tree so they don't bloat the EXE.
Get-ChildItem -Path (Join-Path $Root "backend\app") -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force -Confirm:$false

Write-Host "[build] PyInstaller (onefile console)…"
$out = Join-Path $Root "dist"
# Sources must be absolute: PyInstaller resolves add-data paths relative to the
# spec file's directory, not the working directory.
$srcBackend = Join-Path $Root "backend\app"
$srcModel   = Join-Path $Root "data\models\scam_classifier.joblib"
$srcReq     = Join-Path $Root "packaging\requirements.txt"
& $Py -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --name "DigiRaksha" `
    --console `
    --add-data "$srcBackend;backend\app" `
    --add-data "$srcModel;data\models" `
    --add-data "$srcReq;." `
    --distpath $out `
    --workpath (Join-Path $Root "build\pyinstaller") `
    --specpath (Join-Path $Root "build\spec") `
    "packaging\launcher.py"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$exe = Join-Path $out "DigiRaksha.exe"
if (-not (Test-Path $exe)) { throw "EXE not produced: $exe" }
$size = (Get-Item $exe).Length / 1MB
$sizeMb = "{0:N1}" -f $size
Write-Host ""
Write-Host "[build] Done: $exe  ($sizeMb MB)"
Write-Host "[build] Distribute this single file. First run needs internet; later runs are offline."
