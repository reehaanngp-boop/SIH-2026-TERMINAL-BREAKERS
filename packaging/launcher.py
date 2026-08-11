r"""DigiRaksha Smart Launcher — check, install, and run the app.

Pure-stdlib Python script, compiled to a single EXE with PyInstaller
(--onefile --console). The EXE embeds:
    backend/app          -> backend source (incl. the built SPA under app/static)
    data/models/scam_classifier.joblib -> trained text classifier
    packaging/requirements.txt         -> dependency list for the runtime venv

Heavy ML deps (torch/scipy/librosa/opencv…) are NOT frozen — they install into a
runtime venv on first launch. First run needs internet; later runs are offline.

Behaviour:
  1. Resolve runtime root:  $DIGIRAKSHA_RUNTIME  or  %LOCALAPPDATA%\DigiRaksha
  2. Check for Python 3.12, the venv, importable deps, and materialized files.
  3. Install whatever is missing (Python silently, venv, CPU torch, deps).
  4. Run `venv\Scripts\python -m uvicorn app.main:app` on 127.0.0.1:8000,
     poll the API until it answers, then open the browser.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

APP_NAME = "DigiRaksha"
HOST = "127.0.0.1"
PORT = 8000
PY_VER = "3.12"
PY_FULL = "3.12.10"  # pinned installer (matches the dev venv)
PY_URL = f"https://www.python.org/ftp/python/{PY_FULL}/python-{PY_FULL}-amd64.exe"
META_URL = f"http://{HOST}:{PORT}/api/v1/meta"

# Packages that must import successfully for the app to run. torch is optional
# (voice anti-spoofing degrades gracefully) so it is not checked here.
REQUIRED_IMPORTS = [
    "fastapi",
    "uvicorn",
    "sqlalchemy",
    "pydantic",
    "pydantic_settings",
    "librosa",
    "soundfile",
    "sklearn",
    "joblib",
    "faster_whisper",
    "cv2",
    "reportlab",
]


def log(msg: str) -> None:
    print(f"[{APP_NAME}] {msg}", flush=True)


def runtime_root() -> Path:
    env = os.environ.get("DIGIRAKSHA_RUNTIME")
    if env:
        return Path(env).expanduser()
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / APP_NAME


def embedded_root() -> Path:
    """Where bundled assets live: PyInstaller temp dir when frozen, else repo root."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base)
    # Dev mode: this file lives at <repo>/packaging/launcher.py
    return Path(__file__).resolve().parents[1]


def run(args: list[str], timeout: int = 600) -> tuple[int, str]:
    """Run a command and return (exit_code, combined output)."""
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except FileNotFoundError:
        return -1, f"command not found: {args[0]}"
    except subprocess.TimeoutExpired:
        return -1, f"timeout after {timeout}s: {' '.join(args)}"


def python_version(py: Path | str) -> str:
    code, out = run([str(py), "-c", "import sys; print('.'.join(map(str, sys.version_info[:2])))"], timeout=60)
    return out.strip() if code == 0 else ""


def venv_python(root: Path) -> Path:
    return root / "venv" / "Scripts" / "python.exe"


def find_base_python() -> Path | None:
    """Find a Python 3.12 interpreter on the system (not in the runtime venv)."""
    # py launcher
    for probe in (["py", "-3.12"], ["py", "-3"], ["py"]):
        try:
            code, out = run(probe + ["-c", "import sys; print(sys.executable)"], timeout=60)
            if code == 0:
                exe = out.strip()
                if exe and python_version(exe).startswith(PY_VER):
                    return Path(exe)
        except Exception:
            continue
    # common install locations
    candidates = [
        Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Python312" / "python.exe",
        Path(os.environ.get("LocalAppData", "C:\\Users\\Default")) / "Programs" / "Python" / "Python312" / "python.exe",
        Path("C:\\Python312\\python.exe"),
    ]
    for cand in candidates:
        if cand.exists() and python_version(cand).startswith(PY_VER):
            return cand
    return None


def install_python(root: Path) -> Path:
    target = root / "py312" / "python.exe"
    if not target.exists():
        log(f"Python {PY_VER} not found. Downloading {PY_FULL}…")
        installer = root / f"python-{PY_FULL}-amd64.exe"
        root.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(PY_URL, installer)
        log("Installing Python silently (user-only)…")
        code, out = run(
            [str(installer), "/quiet", "InstallAllUsers=0", f"TargetDir={root / 'py312'}",
             "PrependPath=0", "Include_launcher=0", "Include_test=0", "Include_pip=1"],
            timeout=1800,
        )
        if code != 0 or not target.exists():
            raise SystemExit(f"Python install failed.\n{out[-2000:]}")
        try:
            installer.unlink()
        except OSError:
            pass
    return target


def ensure_venv(root: Path, base: Path) -> Path:
    vp = venv_python(root)
    if vp.exists() and python_version(vp).startswith(PY_VER):
        return vp
    log("Creating runtime virtual environment…")
    root.mkdir(parents=True, exist_ok=True)
    code, out = run([str(base), "-m", "venv", str(root / "venv")], timeout=600)
    if code != 0 or not vp.exists():
        raise SystemExit(f"Failed to create venv.\n{out[-2000:]}")
    return vp


def install_deps(vp: Path) -> None:
    log("Installing/upgrading pip…")
    run([str(vp), "-m", "pip", "install", "--upgrade", "pip", "--quiet"], timeout=600)
    log("Installing PyTorch (CPU-only build)…")
    code, out = run(
        [str(vp), "-m", "pip", "install", "torch", "--index-url", "https://download.pytorch.org/whl/cpu"],
        timeout=1800,
    )
    if code != 0:
        log("CPU torch install failed (continuing — anti-spoofing will be disabled):\n" + out[-800:])
    req = embedded_root() / "requirements.txt"
    log(f"Installing dependencies from {req.name} (this can take several minutes)…")
    code, out = run([str(vp), "-m", "pip", "install", "-r", str(req)], timeout=3600)
    if code != 0:
        raise SystemExit(f"Dependency install failed.\n{out[-3000:]}")


def imports_ok(vp: Path) -> bool:
    """Every required import must succeed; retry once (Smart App Control can
    transiently block a freshly-extracted native DLL on first load)."""
    missing: list[str] = []
    for mod in REQUIRED_IMPORTS:
        code, _ = run([str(vp), "-c", f"import {mod}"], timeout=180)
        if code != 0:
            missing.append(mod)
    if missing:
        log(f"Import check failed for: {', '.join(missing)} — retrying once…")
        time.sleep(2)
        still = [m for m in missing if run([str(vp), "-c", f"import {m}"], timeout=180)[0] != 0]
        missing = still
    return not missing


def materialize(root: Path) -> None:
    src = embedded_root()
    need_backend = not (root / "backend" / "app" / "main.py").exists()
    need_static = not (root / "backend" / "app" / "static" / "index.html").exists()
    need_model = not (root / "data" / "models" / "scam_classifier.joblib").exists()

    if need_backend:
        src_backend = src / "backend" / "app"
        if not src_backend.exists():
            raise SystemExit(f"Embedded backend source not found: {src_backend}")
        log("Materialising backend source…")
        shutil.copytree(src_backend, root / "backend" / "app", dirs_exist_ok=True)
    if need_static:
        log("Materialising web UI…")
        shutil.copytree(src / "backend" / "app" / "static", root / "backend" / "app" / "static", dirs_exist_ok=True)
    if need_model:
        log("Materialising scam-text classifier…")
        (root / "data" / "models").mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / "data" / "models" / "scam_classifier.joblib", root / "data" / "models" / "scam_classifier.joblib")
    (root / "data" / "reports").mkdir(parents=True, exist_ok=True)


def port_free() -> bool:
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
        return True
    except OSError:
        return False


def start_server(root: Path, vp: Path) -> subprocess.Popen:
    backend = root / "backend"
    db = root / "data" / "digiraksha.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db.as_posix()}"
    env["ENABLE_AUTH"] = "true"
    env["PYTHONUNBUFFERED"] = "1"
    cmd = [str(vp), "-m", "uvicorn", "app.main:app", "--host", HOST, "--port", str(PORT)]
    log("Starting DigiRaksha server…")
    return subprocess.Popen(cmd, cwd=str(backend), env=env)


def wait_ready(timeout: float = 180.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(META_URL, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.75)
    return False


def main() -> int:
    root = runtime_root()
    log(f"Runtime root: {root}")

    # 1. Python + venv + deps
    vp = venv_python(root)
    if not (vp.exists() and python_version(vp).startswith(PY_VER)):
        base = find_base_python()
        if base is None:
            base = install_python(root)
        vp = ensure_venv(root, base)
        install_deps(vp)
        if not imports_ok(vp):
            raise SystemExit("Dependency verification failed. Run the launcher again — if it "
                             "persists, disable Smart App Control temporarily and retry.")

    # 2. App files
    materialize(root)

    # 3. Run
    if not port_free():
        print(f"\n[{APP_NAME}] Port {PORT} is already in use.\n"
              "If another DigiRaksha is running, open http://127.0.0.1:8000 in your browser.\n"
              "Otherwise close the other program and restart.", flush=True)
        webbrowser.open(f"http://{HOST}:{PORT}")
        return 0

    proc = start_server(root, vp)
    try:
        if wait_ready():
            log("Server is up. Opening browser…")
            webbrowser.open(f"http://{HOST}:{PORT}")
        else:
            log("Timed out waiting for the server. Check the log above.")
        while True:
            time.sleep(1)
            if proc.poll() is not None:
                log(f"Server exited with code {proc.returncode}.")
                return proc.returncode or 0
    except KeyboardInterrupt:
        log("Shutting down…")
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — top-level guard for the user
        print(f"\n[{APP_NAME}] Fatal error: {exc}", flush=True)
        print("Press Enter to close…", flush=True)
        try:
            input()
        except EOFError:
            pass
        raise SystemExit(1)
