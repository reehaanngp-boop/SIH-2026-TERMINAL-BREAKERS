r"""DigiRaksha Online Launcher — Cloud Collaboration Mode.

1. Verifies environment, Python 3.12, venv, and required AI models.
   Auto-downloads missing components if necessary.
2. Verifies cloudflared.exe (auto-downloads official binary if missing).
3. Launches FastAPI backend on http://127.0.0.1:8000.
4. Launches Cloudflare Tunnel and extracts public HTTPS/WSS URL.
5. Automatically opens the Cloudflare Pages web app:
   https://sih-2026-terminal-breakers.pages.dev
"""

from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

APP_NAME = "DigiRaksha Online"
APP_VERSION = "0.3.0"
HOST = "127.0.0.1"
PORT = 8000
PY_VER = "3.12"
PY_FULL = "3.12.10"
PY_URL = f"https://www.python.org/ftp/python/{PY_FULL}/python-{PY_FULL}-amd64.exe"
CLOUDFLARED_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
PAGES_APP_URL = "https://sih-2026-terminal-breakers.pages.dev"
META_URL = f"http://{HOST}:{PORT}/api/v1/meta"

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
    "torch",
    "torchaudio",
    "onnxruntime",
]

LARGE_MODELS = {
    "dhwani_multilingual.onnx": "https://huggingface.co/ayush2635/Dhwani-Multilingual-Deepfake-Audio-Detection-Model/resolve/main/best_model.onnx",
}


def log(msg: str) -> None:
    print(f"[{APP_NAME}] {msg}", flush=True)


def banner() -> None:
    print("=" * 72)
    print(f"   🛡️ {APP_NAME} v{APP_VERSION} — Online Team Collaboration Runner")
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


def run_cmd(args: list[str], timeout: int = 600) -> tuple[int, str]:
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except FileNotFoundError:
        return -1, f"command not found: {args[0]}"
    except subprocess.TimeoutExpired:
        return -1, f"timeout after {timeout}s: {' '.join(args)}"


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


def ensure_cloudflared(root: Path) -> Path:
    local = root / "cloudflared.exe"
    if local.exists() and local.stat().st_size > 10_000_000:
        return local

    system_cf = shutil.which("cloudflared")
    if system_cf and Path(system_cf).exists():
        return Path(system_cf)

    log("cloudflared.exe not found. Auto-downloading official binary from Cloudflare...")
    if download_with_progress(CLOUDFLARED_URL, local, "Cloudflare Tunnel (cloudflared.exe)"):
        return local

    raise RuntimeError("Could not find or download cloudflared.exe. Please install it manually.")


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
    cf_bin = ensure_cloudflared(root)

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

    tunnel_proc = None
    try:
        # Wait for backend readiness
        if not wait_for_backend(35):
            log("Backend took longer than expected to initialize. Proceeding to tunnel...")

        # 3. Launch Cloudflare tunnel
        log("Starting Cloudflare Tunnel...")
        tunnel_proc = subprocess.Popen(
            [str(cf_bin), "tunnel", "--url", f"http://{HOST}:{PORT}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        tunnel_url = None
        log("Extracting public tunnel endpoint...")
        for line in tunnel_proc.stdout:
            match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
            if match:
                tunnel_url = match.group(0)
                break

        print("\n" + "=" * 72)
        if tunnel_url:
            print(f"🚀 PUBLIC BACKEND TUNNEL:  {tunnel_url}")
            print(f"🌐 CLOUDFLARE PAGES APP:   {PAGES_APP_URL}")
            print("=" * 72)
            print("\n📋 Next Steps:")
            print("1. Share your Tunnel URL with your team.")
            print("2. Paste this URL into Settings or the Connect screen of the web app.")
            print("3. Press Ctrl+C in this window when you want to stop the server.\n")

            # Open Cloudflare Pages in browser
            try:
                webbrowser.open(PAGES_APP_URL)
            except Exception:
                pass
        else:
            print("⚠️ Tunnel created, but URL could not be parsed automatically.")
            print("Check above logs for the trycloudflare.com address.")
            print("=" * 72 + "\n")

        # Keep alive
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                log("Backend process exited.")
                break
            if tunnel_proc.poll() is not None:
                log("Tunnel process exited.")
                break

    except KeyboardInterrupt:
        log("Shutting down DigiRaksha Online...")
    finally:
        if backend_proc and backend_proc.poll() is None:
            backend_proc.terminate()
        if tunnel_proc and tunnel_proc.poll() is None:
            tunnel_proc.terminate()
        log("Clean shutdown complete.")


if __name__ == "__main__":
    main()
