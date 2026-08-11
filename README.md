<div align="center">

# 🛡️ DigiRaksha

### AI Shield Against Digital Arrest & Deepfake Scam Calls

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)
[![Tests](https://img.shields.io/badge/tests-28%20passed-brightgreen.svg)](#testing)

*Detect. Explain. Protect.*

[Features](#features) • [Quick Start](#quick-start) • [Architecture](#architecture) • [API Reference](#api-reference) • [Documentation](#documentation)

</div>

---

## What is DigiRaksha?

**DigiRaksha** (डिजीरक्षा — "Digital Protection") is an AI-powered detection and awareness system against **Digital Arrest scams**, **deepfake voice cloning**, and **telecom fraud** targeting Indian citizens.

Scammers now use AI-cloned voices and real-time deepfake video to impersonate police, judges, and family members. The "digital arrest" scam has made lakhs of Indians pay fake penalties while believing they were under investigation. **DigiRaksha helps victims detect these scams before they lose money.**

> Built for **Smart India Hackathon 2026** — Blockchain & Cybersecurity theme (MHA/I4C, MeitY, RBI fit).

---

## Features

### 🎙️ Multi-Modal Scam Detection
- **ASR Transcription** — Whisper-based speech-to-text (CPU int8, offline)
- **Voice Anti-Spoofing** — AASIST model detects AI-generated/cloned voices
- **Video Deepfake Analysis** — OpenCV Haar cascade frame-level tampering detection
- **Scam Script Classifier** — TF-IDF + Logistic Regression matching 6 scam categories

### 📊 Explainable Risk Engine
- Weighted aggregation across all detector signals (voice 40%, text 35%, video 25%)
- Risk score (0–100) with **low / medium / high** classification
- Specific **red flags** explaining *why* something was flagged
- Actionable **next steps** guiding users to verify and report

### 👨‍👩‍👧 Family Safe-Voice Registry
- Pre-enrol real voices of family members
- Instantly verify suspicious "relative in trouble" calls
- MFCC-embedding cosine similarity speaker verification
- Threshold-based match/no-match with guidance

### 🌐 Bilingual (English + Hindi)
- Full UI and result explanations in English and Hindi
- Targeted at the primary demographic affected by these scams

### 🔒 Privacy-First
- **All processing runs locally** — no data leaves your server
- No external API calls, no analytics, no telemetry
- SQLite database, local ML models

---

## 👥 New to the team? Start here

If you're setting DigiRaksha up on **your own laptop** for the first time
(SIH 2026 team members), follow the beginner-friendly
**[docs/TEAM_SETUP.md](docs/TEAM_SETUP.md)** guide. It covers every step,
including installing Python/Node and troubleshooting.

The fastest path is the one-click setup script:

```powershell
git clone https://github.com/reehaanngp-boop/SIH-2026-TERMINAL-BREAKERS.git
cd SIH-2026-TERMINAL-BREAKERS
powershell -ExecutionPolicy Bypass -File setup_dev.ps1
```

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
git clone https://github.com/reehaanngp-boop/SIH-2026-TERMINAL-BREAKERS.git
cd SIH-2026-TERMINAL-BREAKERS
docker compose up --build -d
# → http://localhost:8000
# → Swagger docs: http://localhost:8000/docs
```

### Option 2: Local Development

**Backend:**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

pip install -e ".[ml]"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Frontend (hot reload):**

```bash
cd frontend
npm install --include=dev
npm run dev                     # http://localhost:5173
```

**Build frontend for production:**

```bash
cd frontend
npm run build                   # outputs to backend/app/static/
```

### Option 3: Quick API Test

```bash
# Transcript analysis
curl -X POST http://localhost:8000/api/v1/analyze/transcript \
  -H "Content-Type: application/json" \
  -d '{"text": "This is CBI, you are under digital arrest. Pay the verification fee."}'

# Upload a recording
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "file=@data/samples/scam_digital_arrest.wav"
```

---

## Architecture

```
Upload / transcript
   └─ AnalysisPipeline
        ├─ ASR        faster-whisper (CPU int8)           → transcript, language
        ├─ Voice      AASIST anti-spoof (PyTorch)          → AI-voice score
        ├─ Video      OpenCV Haar cascade frame analysis    → editing score
        └─ Text       TF-IDF + LogisticRegression (6 cls)  → scam category + probability
        └─ RiskEngine  weights {voice:0.40, text:0.35, video:0.25}
                       thresholds LOW<40<MEDIUM<65<HIGH
                       critical-escalation (1 crit ×1.05, 2+ ×1.15+0.05)

Registry (proactive)  MFCC-stats embedding (52-D) → cosine similarity
                      threshold 0.42
```

### Project Structure

```
digi-raksha/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app factory, CORS, SPA mount
│   │   ├── config.py              # Settings (pydantic-settings)
│   │   ├── db/                    # SQLAlchemy models + SQLite (WAL)
│   │   ├── schemas/               # Pydantic request/response models
│   │   ├── core/                  # Risk engine, i18n strings, job queue
│   │   ├── detectors/             # AI detection modules
│   │   │   ├── audio/             # ASR, voice anti-spoof, speaker verify
│   │   │   ├── video/             # Deepfake frame analysis
│   │   │   └── text/              # Scam script classifier
│   │   ├── services/              # Pipeline orchestration, registry
│   │   ├── api/routes/            # REST API endpoints
│   │   └── static/                # Built frontend (gitignored)
│   ├── ml/                        # Dataset generation + model training
│   ├── scripts/                   # Utility scripts
│   └── tests/                     # 28 pytest tests
├── frontend/                      # Vite + React + TypeScript SPA
├── data/                          # Runtime data (gitignored)
│   ├── digiraksha.db              # SQLite database
│   ├── uploads/                   # Temporary media uploads
│   ├── models/                    # ML models
│   ├── datasets/                  # Training data
│   └── samples/                   # Demo audio samples
├── docs/                          # Documentation
└── samples/                       # Demo audio samples
```

---

## API Reference

All endpoints are under `/api/v1`. Interactive docs at `/docs` (Swagger) and `/redoc`.

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Liveness probe |
| `GET` | `/meta` | Detector availability + report channels |

### Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/analyze/transcript` | Analyse a raw transcript (sync) |
| `POST` | `/analyze` | Upload audio/video for analysis (async) |
| `GET` | `/analyze/jobs/{job_id}` | Poll analysis job status |
| `GET` | `/analyze/results/{scan_id}` | Fetch completed result |
| `GET` | `/analyze/history` | Recent scan history |

### Family Safe-Voice Registry

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/registry/members` | Register a family member |
| `GET` | `/registry/members` | List all members |
| `DELETE` | `/registry/members/{id}` | Remove a member |
| `POST` | `/registry/members/{id}/enroll` | Enrol a voice sample |
| `POST` | `/registry/verify` | Verify a voice note against a member |

See [docs/API.md](docs/API.md) for full request/response schemas.

---

## Detection Categories

The scam classifier identifies these fraud patterns:

| Category | Description | Example |
|----------|-------------|---------|
| `digital_arrest` | Fake police/CBI/customs "digital arrest" | "You are under digital arrest, pay verification fee" |
| `fake_courier` | Fake parcel with illegal items | "Your parcel contains drugs, pay customs fee" |
| `otp_phishing` | Bank/service OTP theft | "Share your OTP to verify your account" |
| `kin_emergency` | Fake relative in trouble | "Your son is in the hospital, send money" |
| `other_fraud` | Generic pressure tactics | Urgency, secrecy, threats |
| `benign` | No scam pattern detected | Normal conversation |

---

## Configuration

All settings are configurable via environment variables or a `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/digiraksha.db` | Database connection |
| `WHISPER_MODEL_SIZE` | `small` | ASR model (tiny/base/small/medium) |
| `ENABLE_AASIST` | `true` | Voice anti-spoofing model |
| `MAX_CONCURRENT_JOBS` | `2` | Parallel analysis limit |
| `VERIFY_SIMILARITY_THRESHOLD` | `0.42` | Speaker verification threshold |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed origins |

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the full list.

---

## Testing

```bash
cd backend
pytest -q                # 28 tests (~30s for slow Whisper test)
pytest -q -m "not slow"  # Skip slow tests
```

| Module | Tests |
|--------|-------|
| Risk engine | 8 |
| Scam classifier | 5 |
| Registry service | 6 |
| API endpoints | 9 |

### E2E Verification

```
scam_digital_arrest.wav  → high   (100.0)  ✓ detected
scam_courier.wav         → high   (100.0)  ✓ detected
benign_restaurant.wav    → medium ( 49.4)  ✓ AASIST flags synthetic TTS voice
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [API Reference](docs/API.md) | Full API docs with request/response schemas |
| [Deployment Guide](docs/DEPLOYMENT.md) | Docker, local dev, systemd, nginx |
| [User Guide](docs/USER_GUIDE.md) | End-user instructions (EN/HI) |
| [Security Policy](docs/SECURITY.md) | Threat model, data handling, disclosure |
| [Contributing](docs/CONTRIBUTING.md) | How to contribute |
| [Demo Script](docs/DEMO_SCRIPT.md) | Step-by-step presentation guide |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2 |
| **ASR** | faster-whisper (CPU int8) |
| **Voice Anti-Spoof** | AASIST (PyTorch) |
| **Video Analysis** | OpenCV (Haar cascade) |
| **ML Classifier** | scikit-learn (TF-IDF + LogisticRegression) |
| **Frontend** | React 19, TypeScript, Vite |
| **Database** | SQLite (WAL mode) |
| **Build** | Hatchling (Python), Vite (JS) |

---

## Reporting Scams

If you or someone you know has been a victim of a telecom scam:

| Channel | Contact |
|---------|---------|
| **National Cyber Crime Helpline** | 📞 [1930](tel:1930) |
| **Cyber Crime Reporting Portal** | 🌐 [cybercrime.gov.in](https://cybercrime.gov.in) |
| **I4C (MHA)** | 🌐 [i4c.mha.gov.in](https://i4c.mha.gov.in) |

**Do not pay any money. Do not share OTPs. Hang up and verify independently.**

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ for Smart India Hackathon 2026**

*Awareness today, protection tomorrow.*

</div>
