# DigiRaksha — Install & Run

DigiRaksha is an offline-first, AI-powered toolkit for detecting scam calls and
building police case files (evidence with SHA-256 integrity, chain-of-custody
audit, voice matching, phone intelligence, PDF case reports).

> **Team members (new users):** start with
> **[docs/TEAM_SETUP.md](docs/TEAM_SETUP.md)** — it has step-by-step
> instructions with screenshots-in-words and troubleshooting for absolute
> beginners. This file is the developer's reference.

---

## Quick start (TL;DR)

```powershell
# One-time environment setup (installs everything — Python venv, packages, models)
powershell -ExecutionPolicy Bypass -File setup_dev.ps1

# Every time you want to run it:
#  Terminal 1 — backend
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

#  Terminal 2 — frontend (hot reload)
cd frontend
npm run dev        # http://localhost:5173 (proxies /api to :8000)
```

---

## Requirements

| Tool | Version | Why |
|------|---------|-----|
| Python | **3.12** (not 3.13/3.14) | The ML audio libs (librosa, OpenCV) have no wheels for newer Pythons |
| Node.js | 20+ (LTS) | Vite + React build tooling |
| npm | 10+ (ships with Node) | Frontend packages |

Check what you have:

```powershell
python --version        # or: py -3.12 --version
node --version
npm --version
```

Install from [python.org/downloads](https://www.python.org/downloads/) (tick
**"Add python.exe to PATH"**) and [nodejs.org](https://nodejs.org/).

---

## Manual install (what `setup_dev.ps1` does, step by step)

```powershell
# 1. Clone the repo and go inside
git clone https://github.com/reehaanngp-boop/SIH-2026-TERMINAL-BREAKERS.git
cd SIH-2026-TERMINAL-BREAKERS

# 2. Create the Python virtual environment (uses Python 3.12)
py -3.12 -m venv .venv

# 3. Install torch FIRST from the CPU index.
#    (Plain `pip install torch` downloads a multi-GB CUDA build you don't need.)
.\.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu

# 4. Install the backend + all its Python dependencies
cd backend
..\.venv\Scripts\python.exe -m pip install -e ".[ml]"

# 5. Install the frontend
cd ..\frontend
npm install --include=dev
cd ..
```

> **Long-path warning (Windows):** if step 3 or 4 fails with `could not read
> license file` / `filename too long`, the project path is too deep. Move the
> folder to a short path like `C:\sih` (i.e. `C:\sih\SIH-2026-TERMINAL-BREAKERS`)
> and repeat.

## Running

### Backend (Terminal 1)

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- API + Swagger docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

### Frontend (Terminal 2)

```powershell
cd frontend
npm run dev          # http://localhost:5173 (proxies /api to :8000)
```

Open http://localhost:5173 in your browser. On first use the app asks you to
create a **PIN** (access code — keep it safe).

---

## First-run notes

- Whisper (speech-to-text) and the ECAPA speaker model are downloaded the first
  time you use them — **internet needed on first use, fully offline after.**
- If Windows Smart App Control blocks a freshly-installed component on the very
  first launch, run the command once more — it usually resolves.
- All data (case files, database, uploads) lives under `data/` in the project
  folder. Back it up by copying that folder.

## Running from a single EXE

The project can be packaged into a self-contained `DigiRaksha.exe` that
bootstraps its own Python runtime:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_exe.ps1
```

Output: `dist\DigiRaksha.exe`. Requires Node/npm and a Python 3.12 environment
with PyInstaller.

## Building the classifier / training

Model training scripts live in `backend/ml/` — see
[docs/AI_MODEL_GUIDE.md](docs/AI_MODEL_GUIDE.md).

## Data & privacy

- All analysis runs locally — no audio or text is uploaded anywhere. The only
  network use is first-run model downloads and the optional scam-number lookup.
- The AI second-opinion layer (OpenRouter) is **off by default** and only
  enabled by setting `ENABLE_LLM_ANALYSIS=true` + an API key in `.env`.

## Support & helplines

- Cybercrime helpline (India): **1930**
- Report scams: [cybercrime.gov.in](https://cybercrime.gov.in)
