# 🚀 DigiRaksha — Team Setup Guide (for beginners)

**Welcome to the team! 👋** This guide gets DigiRaksha running on *your* laptop
in about 15–20 minutes. You don't need to know anything about the project or
programming to follow it — just copy the commands one by one.

By the end you will have:

- ✅ The DigiRaksha app running in your browser
- ✅ Demo scam calls you can test with (no recording needed)
- ✅ The full codebase on your computer to explore and contribute

---

## Part 0 — What you need to install first (only once)

Install these **three things**. If you already have them, skip to Part 1.

### 1) Python 3.12  ⚠️ (must be exactly 3.12, not 3.13 or 3.14)

1. Go to <https://www.python.org/downloads/>
2. Click the **Download Python 3.12** button (any 3.12.x version).
3. Run the installer.
4. **IMPORTANT:** on the first screen, tick the box that says
   **"Add python.exe to PATH"**, then click **Install Now**.
5. When it finishes, click **Close**.

### 2) Node.js (long-term-support version)

1. Go to <https://nodejs.org/>
2. Click the big green **Download Node.js LTS** button.
3. Run the installer and click **Next** through everything (defaults are fine).
4. Click **Finish**.

### 3) Git (lets you download the project from GitHub)

1. Go to <https://git-scm.com/download/win>
2. It starts downloading automatically. Run the installer.
3. Click **Next / Install** through all the screens (defaults are fine).
4. Click **Finish**.

**To double-check all three worked**, open **PowerShell** (Start menu → type
"PowerShell" → Enter) and type:

```powershell
py -3.12 --version
node --version
git --version
```

You should see three version numbers (e.g. `Python 3.12.10`, `v22.x.x`,
`git version 2.5x.windows.x`). If a command says *"not recognized"*, that
install didn't finish — run its installer again.

---

## Part 1 — Download the project to your laptop

1. Open PowerShell.
2. Create a folder for the project somewhere easy, e.g.:
   ```powershell
   mkdir C:\sih
   cd C:\sih
   ```
3. Download the code:
   ```powershell
   git clone https://github.com/reehaanngp-boop/SIH-2026-TERMINAL-BREAKERS.git
   cd SIH-2026-TERMINAL-BREAKERS
   ```

> 💡 **Tip:** use a short folder like `C:\sih`. If the path is too long, Windows
> can fail on some packages with a "filename too long" error.

---

## Part 2 — One-click setup (downloads everything automatically)

In the project folder, run:

```powershell
powershell -ExecutionPolicy Bypass -File setup_dev.ps1
```

This script does all the boring setup for you:

- Creates a private Python environment (`.venv`) — nothing touches your system Python
- Installs the AI libraries (PyTorch CPU version — small, fast download)
- Installs the backend dependencies
- Installs the frontend (React) dependencies

**It downloads a few hundred MB and can take 5–10 minutes.** Let it run until it
prints `SETUP COMPLETE`. You'll see a green `✓` at the end.

### Troubleshooting during setup

| Problem | Fix |
|---------|-----|
| `py -3.12 is not recognized` | Python 3.12 didn't install or PATH box wasn't ticked. Re-run the Python installer and tick "Add python.exe to PATH". |
| `node / npm not recognized` | Re-run the Node.js installer. |
| `filename too long` / `could not read license file` | Your folder path is too long. Move the project to `C:\sih\` and run setup again. |
| Antivirus / Smart App Control warning | Click **Allow / Run anyway**. If a file is blocked on first run, just run setup again. |
| Internet errors / download fails | Check your Wi-Fi, then re-run the same command. It's safe to run again. |

---

## Part 3 — Run DigiRaksha 🎉

Now you need **two PowerShell windows** (they both stay open while you work).

### Window 1 — Start the backend (the "brain")

```powershell
cd C:\sih\SIH-2026-TERMINAL-BREAKERS\backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Wait until you see `Uvicorn running on http://127.0.0.1:8000`. Keep this window open.

### Window 2 — Start the frontend (the website)

Open a **new** PowerShell window and run:

```powershell
cd C:\sih\SIH-2026-TERMINAL-BREAKERS\frontend
npm run dev
```

Wait until you see `Local: http://localhost:5173/`.

### Open the app

1. Open your browser (Chrome / Edge).
2. Go to **http://localhost:5173**
3. The first time, it will ask you to create a **4-digit PIN** — make one up
   and remember it (it's your access code).
4. Welcome to DigiRaksha! 🛡️

---

## Part 4 — Try it with the demo scam calls

There are sample recordings in `data/samples/` you can test with instantly:

| File | What it is |
|------|-----------|
| `data\samples\scam_digital_arrest.wav` | Fake "CBI digital arrest" call → should be flagged **HIGH** risk |
| `data\samples\scam_courier.wav` | Fake parcel/drugs call → should be flagged **HIGH** risk |
| `data\samples\scam_otp.wav` | OTP-phishing call → should be flagged |
| `data\samples\benign_restaurant.wav` | Normal call → should be **LOW/medium** risk |

Upload one of these in the app and watch the risk engine explain *why* it's a
scam (voice, text, video signals, red flags, next steps).

You can also **record your own voice** with the app and try the
**Family Safe-Voice Registry** (enrol a voice, then verify it).

---

## Part 5 — Understanding the project (quick tour)

This is what you'll see in the repo:

```
SIH-2026-TERMINAL-BREAKERS/
├── backend/           The Python AI server (FastAPI)
│   ├── app/
│   │   ├── detectors/     🎙️ The AI models (voice, text, video)
│   │   ├── core/          ⚖️ The risk engine (scores + red flags)
│   │   ├── api/           🔌 The API endpoints
│   │   └── main.py        The server entry point
│   ├── ml/             Model training scripts
│   └── tests/          Automated tests
├── frontend/          The React website you see in the browser
├── data/              Models + your data (uploads, case files)
└── docs/              All the documentation
```

**Suggested reading order:**

1. `README.md` — the project overview (what it is, features)
2. `docs/DEMO_SCRIPT.md` — how to present it (great for SIH judging!)
3. `backend/app/core/risk_engine.py` — how a call gets a risk score
4. `backend/tests/` — how we test things

---

## Part 6 — Daily workflow (after setup)

Once setup is done, **every time** you want to run the app you only need
Part 3 (the two windows). No re-installing.

### Before you start coding — pull the latest

```powershell
cd C:\sih\SIH-2026-TERMINAL-BREAKERS
git pull
```

### When you change code, save your work back

```powershell
git add .
git commit -m "describe what you changed"
git push
```

> ⚠️ Never push if you're not sure — ask the team lead first. And **never**
> commit the `.env` file (it holds secret API keys).

---

## Help — when something breaks

1. **Read the error carefully** — 90% of the time the fix is in the message.
2. Check the troubleshooting table in [Part 2](#part-2--one-click-setup-downloads-everything-automatically).
3. Search the error on Google or ask the team group chat.
4. Ping the team lead — they've set this exact environment up before.

---

**You're all set. Explore, test, and let's build something great for SIH 2026! 🏆**
