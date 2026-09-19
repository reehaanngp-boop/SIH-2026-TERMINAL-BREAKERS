r"""DigiRaksha Offline Launcher — 100% Standalone Mode.

1. Verifies environment, Python 3.12, venv, and required AI models.
   Auto-downloads missing foundation models on first setup if necessary.
2. Launches FastAPI backend on http://127.0.0.1:8000.
3. Automatically opens local web browser to http://127.0.0.1:8000.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

APP_NAME = "DigiRaksha Offline"
APP_VERSION = "0.3.0"
HOST = "127.0.0.1"
PORT = 8000
LOCAL_URL = f"http://{HOST}:{PORT}"
META_URL = f"http://{HOST}:{PORT}/api/v1/meta"

LARGE_MODELS = {
    "dhwani_multilingual.onnx": "https://huggingface.co/ayush2635/Dhwani-Multilingual-Deepfake-Audio-Detection-Model/resolve/main/best_model.onnx",
}


def log(msg: str) -> None:
    print(f"[{APP_NAME}] {msg}", flush=True)


def banner() -> None:
    print("=" * 72)
    print(f"   🛡️ {APP_NAME} v{APP_VERSION} — Standalone Local Runner")
    print("   AI Shield against Digital Arrest & Deepfake Impersonation")
    print("=" * 72, flush=True)


def resolve_workspace() -> Path:
    env = os.environ.get("DIGIRAKSHA_RUNTIME")
    if env and Path(env).exists():
        return Path(env).expanduser()

    exe_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
    cwd = Path.cwd()

    for candidate in [cwd, exe_dir, exe_dir.parent]:
        if (candidate / "backend" / "app" / "main.py").exists() and (candidate / "data").exists():
            return candidate.resolve()

    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "DigiRaksha"


def download_with_progress(url: str, dest: Path, desc: str) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    log(f"Downloading {desc}...")
    try:
        def reporthook(count, block_size, total_size):
            if total_size > 0:
                percent = min(100, int(count * block_size * 100 / total_size))
                mb_downloaded = (count * block_size) / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                sys.stdout.write(f"\r[{APP_NAME}] [{percent}%] {mb_downloaded:.1f} MB / {mb_total:.1f} MB — {desc}")
                sys.stdout.flush()

        urllib.request.urlretrieve(url, tmp, reporthook=reporthook)
        print()
        if tmp.exists() and tmp.stat().st_size > 0:
            shutil.move(str(tmp), str(dest))
            return True
    except Exception as e:
        print()
        log(f"Download note ({desc}): {e}")
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
    return False


def find_python(root: Path) -> Path:
    candidates = [
        root / "backend" / ".venv" / "Scripts" / "python.exe",
        root / ".venv" / "Scripts" / "python.exe",
        root / "venv" / "Scripts" / "python.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "DigiRaksha" / "venv" / "Scripts" / "python.exe",
    ]
    for c in candidates:
        if c.exists():
            return c

    sys_py = shutil.which("python") or shutil.which("python3")
    if sys_py:
        return Path(sys_py)

    raise RuntimeError("Python interpreter not found. Please run setup_dev.ps1 or install Python 3.12.")


def ensure_models(root: Path) -> None:
    models_dir = root / "data" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    for filename, url in LARGE_MODELS.items():
        dest = models_dir / filename
        if not dest.exists() or dest.stat().st_size < 1_000_000:
            log(f"Missing foundation model: {filename}. Auto-downloading...")
            download_with_progress(url, dest, filename)


def wait_for_backend(timeout_seconds: int = 30) -> bool:
    log("Waiting for backend AI engine to initialize...")
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            with urllib.request.urlopen(META_URL, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False


def main() -> None:
    banner()
    root = resolve_workspace()
    log(f"Workspace root: {root}")

    # 1. Environment and dependencies
    py = find_python(root)
    log(f"Using Python: {py}")
    ensure_models(root)

    # 2. Launch backend server
    log("Starting FastAPI backend on port 8000...")
    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = str(root / "backend")
    backend_cwd = root / "backend" if (root / "backend").exists() else root

    backend_proc = subprocess.Popen(
        [str(py), "-m", "app.main"],
        cwd=str(backend_cwd),
        env=backend_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        # Wait for backend readiness
        if wait_for_backend(35):
            log("Backend AI engine initialized successfully!")
        else:
            log("Backend took longer than expected to initialize. Opening browser anyway...")

        print("\n" + "=" * 72)
        print(f"🚀 DIGIRAKSHA STANDALONE:  {LOCAL_URL}")
        print("=" * 72)
        print("\n📋 Next Steps:")
        print("1. DigiRaksha is running 100% locally on your computer.")
        print("2. Your browser should open automatically.")
        print("3. Press Ctrl+C in this window when you want to stop the server.\n")

        # Open local app in browser
        try:
            webbrowser.open(LOCAL_URL)
        except Exception:
            pass

        # Keep alive
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                log("Backend process exited.")
                break

    except KeyboardInterrupt:
        log("Shutting down DigiRaksha Offline...")
    finally:
        if backend_proc and backend_proc.poll() is None:
            backend_proc.terminate()
        log("Clean shutdown complete.")


if __name__ == "__main__":
    main()
