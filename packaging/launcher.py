r"""DigiRaksha Smart Launcher — check, install, and run the app.

Pure-stdlib Python script, compiled to a single EXE with PyInstaller
(--onefile --console). The EXE embeds:
    backend/app                     -> backend source (incl. the built SPA under app/static)
    data/models/scam_classifier.joblib -> trained multilingual text classifier
    data/models/aasist.pth          -> GNN voice anti-spoofing model
    data/models/voice_clone_classifier.joblib -> voice clone classifier
    data/models/mesonet             -> MesoNet Inception video deepfake CNN
    data/models/ecapa-tdnn          -> ECAPA-TDNN speaker verification embeddings
    packaging/requirements.txt      -> dependency list for runtime venv

Behavior:
  1. Check existing environment:
     - If running in or adjacent to the DigiRaksha repo or %LOCALAPPDATA%\DigiRaksha,
       and all dependencies & models already exist:
       --> SKIPS ALL DOWNLOADS and immediately boots the server and browser.
  2. If running on a brand new machine / first-time user:
     - Downloads and installs Python 3.12 (if not present), creates venv.
     - Installs PyTorch CPU, onnxruntime, speechbrain, faster-whisper, and deps.
     - Unpacks all embedded AI models and materializes web UI.
     - Verifies components and records version stamp.
  3. Launches uvicorn app.main:app on 127.0.0.1:8000, polls health, and opens browser.
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

APP_NAME = "DigiRaksha"
APP_VERSION = "0.3.0"
HOST = "127.0.0.1"
PORT = 8000
PY_VER = "3.12"
PY_FULL = "3.12.10"
PY_URL = f"https://www.python.org/ftp/python/{PY_FULL}/python-{PY_FULL}-amd64.exe"
META_URL = f"http://{HOST}:{PORT}/api/v1/meta"

# Core packages that must import successfully
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

# Foundation large models
LARGE_MODELS = {
    "dhwani_multilingual.onnx": "https://huggingface.co/ayush2635/Dhwani-Multilingual-Deepfake-Audio-Detection-Model/resolve/main/best_model.onnx",
}


def log(msg: str) -> None:
    print(f"[{APP_NAME}] {msg}", flush=True)


def banner() -> None:
    print("=" * 68)
    print(f"   {APP_NAME} v{APP_VERSION} — AI Scam & Deepfake Protection Suite")
    print("=" * 68, flush=True)


def embedded_root() -> Path:
    """Where bundled assets live: PyInstaller temp dir when frozen, else repo root."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base)
    return Path(__file__).resolve().parents[1]


def resolve_workspace() -> Path:
    """Find the best runtime root directory.
    
    1. If $DIGIRAKSHA_RUNTIME is set, use that.
    2. If launched inside or adjacent to a DigiRaksha repo (where backend/app/main.py exists), use that.
    3. Otherwise, use %LOCALAPPDATA%\DigiRaksha.
    """
    env = os.environ.get("DIGIRAKSHA_RUNTIME")
    if env and Path(env).exists():
        return Path(env).expanduser()

    # Probing candidate folders
    exe_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
    cwd = Path.cwd()

    for candidate in [cwd, exe_dir, exe_dir.parent]:
        if (candidate / "backend" / "app" / "main.py").exists() and (candidate / "data").exists():
            return candidate.resolve()

    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / APP_NAME


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
    code, out = run([str(py), "-c", "import sys; print('.'.join(map(str, sys.version_info[:2])))"], timeout=30)
    return out.strip() if code == 0 else ""


def find_existing_venv(root: Path) -> Path | None:
    """Check for existing valid virtual environments with required packages."""
    candidates = [
        root / "backend" / ".venv" / "Scripts" / "python.exe",
        root / ".venv" / "Scripts" / "python.exe",
        root / "venv" / "Scripts" / "python.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / APP_NAME / "venv" / "Scripts" / "python.exe",
    ]
    for cand in candidates:
        if cand.exists() and python_version(cand).startswith(PY_VER):
            if imports_ok(cand, silent=True):
                return cand
    return None


def venv_python(root: Path) -> Path:
    """Default location for runtime venv."""
    if (root / "backend" / ".venv" / "Scripts" / "python.exe").exists():
        return root / "backend" / ".venv" / "Scripts" / "python.exe"
    if (root / ".venv" / "Scripts" / "python.exe").exists():
        return root / ".venv" / "Scripts" / "python.exe"
    return root / "venv" / "Scripts" / "python.exe"


def find_base_python() -> Path | None:
    """Find a Python 3.12 interpreter on the host system."""
    for probe in (["py", "-3.12"], ["py", "-3"], ["py"]):
        try:
            code, out = run(probe + ["-c", "import sys; print(sys.executable)"], timeout=30)
            if code == 0:
                exe = out.strip()
                if exe and python_version(exe).startswith(PY_VER):
                    return Path(exe)
        except Exception:
            continue

    candidates = [
        Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Python312" / "python.exe",
        Path(os.environ.get("LocalAppData", "C:\\Users\\Default")) / "Programs" / "Python" / "Python312" / "python.exe",
        Path("C:\\Python312\\python.exe"),
    ]
    for cand in candidates:
        if cand.exists() and python_version(cand).startswith(PY_VER):
            return cand
    return None


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


def install_python(root: Path) -> Path:
    target = root / "py312" / "python.exe"
    if not target.exists():
        log(f"Python {PY_VER} not found on host. Downloading {PY_FULL} installer…")
        installer = root / f"python-{PY_FULL}-amd64.exe"
        root.mkdir(parents=True, exist_ok=True)
        download_with_progress(PY_URL, installer, f"Python {PY_FULL}")
        log("Installing Python silently (isolated user mode)…")
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
    target_dir = vp.parents[1]
    target_dir.mkdir(parents=True, exist_ok=True)
    code, out = run([str(base), "-m", "venv", str(target_dir)], timeout=600)
    if code != 0 or not vp.exists():
        raise SystemExit(f"Failed to create venv.\n{out[-2000:]}")
    return vp


def install_deps(vp: Path) -> None:
    log("Updating pip…")
    run([str(vp), "-m", "pip", "install", "--upgrade", "pip", "--quiet"], timeout=600)
    log("Installing PyTorch (CPU-only build with torchaudio)…")
    code, out = run(
        [str(vp), "-m", "pip", "install", "torch", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cpu"],
        timeout=1800,
    )
    if code != 0:
        log("PyTorch CPU install warning:\n" + out[-800:])

    req = embedded_root() / "packaging" / "requirements.txt"
    if not req.exists():
        req = embedded_root() / "requirements.txt"
    log("Installing AI & web runtime dependencies (one-time setup)…")
    code, out = run([str(vp), "-m", "pip", "install", "-r", str(req)], timeout=3600)
    if code != 0:
        raise SystemExit(f"Dependency install failed.\n{out[-3000:]}")


def imports_ok(vp: Path, silent: bool = False) -> bool:
    """Verify all critical modules can import successfully."""
    check_code = "; ".join([f"import {mod}" for mod in REQUIRED_IMPORTS])
    code, _ = run([str(vp), "-c", check_code], timeout=60)
    if code == 0:
        return True

    # Detailed identification if batch failed
    missing: list[str] = []
    for mod in REQUIRED_IMPORTS:
        c, _ = run([str(vp), "-c", f"import {mod}"], timeout=15)
        if c != 0:
            missing.append(mod)
    if missing and not silent:
        log(f"Missing modules: {', '.join(missing)} - updating environment...")
    return len(missing) == 0


def _installed_version(root: Path) -> str:
    stamp = root / "VERSION"
    if stamp.exists():
        try:
            return stamp.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    return ""


def _write_version_stamp(root: Path) -> None:
    try:
        (root / "VERSION").write_text(APP_VERSION, encoding="utf-8")
    except OSError:
        pass


def materialize(root: Path) -> None:
    """Extract embedded application source, UI, and models into the runtime root."""
    src = embedded_root()
    installed_ver = _installed_version(root)
    version_mismatch = installed_ver != APP_VERSION and installed_ver != ""

    need_backend = version_mismatch or not (root / "backend" / "app" / "main.py").exists()
    need_static  = version_mismatch or not (root / "backend" / "app" / "static" / "index.html").exists()

    if need_backend:
        src_backend = src / "backend" / "app"
        if src_backend.exists():
            log("Materializing backend source…")
            dest_backend = root / "backend" / "app"
            shutil.copytree(src_backend, dest_backend, dirs_exist_ok=True)

    if need_static:
        src_static = src / "backend" / "app" / "static"
        if src_static.exists():
            log("Materializing web UI…")
            dest_static = root / "backend" / "app" / "static"
            shutil.copytree(src_static, dest_static, dirs_exist_ok=True)

    # Models directory
    models_dir = root / "data" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    (root / "data" / "reports").mkdir(parents=True, exist_ok=True)
    (root / "data" / "uploads").mkdir(parents=True, exist_ok=True)

    # Copy bundled models
    bundled_items = [
        ("data/models/scam_classifier.joblib", models_dir / "scam_classifier.joblib"),
        ("data/models/aasist.pth", models_dir / "aasist.pth"),
        ("data/models/voice_clone_classifier.joblib", models_dir / "voice_clone_classifier.joblib"),
        ("data/models/mesonet", models_dir / "mesonet"),
        ("data/models/ecapa-tdnn", models_dir / "ecapa-tdnn"),
    ]

    for rel_path, dest_path in bundled_items:
        src_path = src / rel_path
        if src_path.exists() and not dest_path.exists():
            log(f"Materializing model: {dest_path.name}…")
            if src_path.is_dir():
                shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
            else:
                shutil.copy2(src_path, dest_path)

    # Large models (dhwani_multilingual.onnx)
    dhwani_dest = models_dir / "dhwani_multilingual.onnx"
    if not dhwani_dest.exists():
        # Check if user has it adjacent to the EXE or in current working dir
        candidates = [
            Path.cwd() / "data" / "models" / "dhwani_multilingual.onnx",
            Path(sys.executable).parent / "data" / "models" / "dhwani_multilingual.onnx",
            Path.cwd() / "dhwani_multilingual.onnx",
            Path(sys.executable).parent / "dhwani_multilingual.onnx",
        ]
        found = False
        for c in candidates:
            if c.exists():
                log(f"Found local Dhwani model at {c}. Copying into runtime…")
                shutil.copy2(c, dhwani_dest)
                found = True
                break

        if not found:
            log("Dhwani multilingual foundation model is not present locally.")
            download_with_progress(LARGE_MODELS["dhwani_multilingual.onnx"], dhwani_dest, "Dhwani Multilingual Model (1.2 GB)")

    _write_version_stamp(root)


def port_free() -> bool:
    try:
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
    log(f"Starting {APP_NAME} server on http://{HOST}:{PORT} …")
    return subprocess.Popen(cmd, cwd=str(backend), env=env)


def wait_ready(timeout: float = 120.0) -> bool:
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
    banner()
    root = resolve_workspace()
    log(f"Runtime directory: {root}")

    # Step 1: Check existing files and environment
    log("Checking existing files, dependencies, and models…")
    vp = find_existing_venv(root)
    all_models_present = (
        (root / "data" / "models" / "scam_classifier.joblib").exists() and
        (root / "data" / "models" / "aasist.pth").exists() and
        (root / "data" / "models" / "dhwani_multilingual.onnx").exists() and
        (root / "backend" / "app" / "static" / "index.html").exists()
    )

    if vp is not None and all_models_present:
        log("[OK] All required files, runtime dependencies, and AI models already exist!")
        log("[SKIP] Skipping downloads. Launching directly…")
    else:
        log("[NOTICE] Required components missing or setup required. Preparing environment…")
        if vp is None:
            base = find_base_python()
            if base is None:
                base = install_python(root)
            vp = ensure_venv(root, base)
            install_deps(vp)
            if not imports_ok(vp):
                raise SystemExit("Dependency verification failed. Please check internet connection and retry.")

        materialize(root)
        log("[OK] Environment ready.")

    # Step 2: Launch server
    if not port_free():
        log(f"Port {PORT} is already active. Opening DigiRaksha in browser…")
        webbrowser.open(f"http://{HOST}:{PORT}")
        return 0

    proc = start_server(root, vp)
    try:
        if wait_ready():
            log(f"DigiRaksha is online! Opening browser at http://{HOST}:{PORT}")
            webbrowser.open(f"http://{HOST}:{PORT}")
        else:
            log("Server started, opening browser…")
            webbrowser.open(f"http://{HOST}:{PORT}")

        while True:
            time.sleep(1)
            if proc.poll() is not None:
                log(f"Server stopped with exit code {proc.returncode}.")
                return proc.returncode or 0
    except KeyboardInterrupt:
        log("Shutting down DigiRaksha…")
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
    except Exception as exc:
        print(f"\n[{APP_NAME}] Fatal error: {exc}", flush=True)
        print("Press Enter to close…", flush=True)
        try:
            input()
        except EOFError:
            pass
        raise SystemExit(1)
