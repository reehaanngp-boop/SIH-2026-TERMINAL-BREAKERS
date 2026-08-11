# Contributing to DigiRaksha

Thank you for your interest in contributing to DigiRaksha! This document provides guidelines and instructions for contributing.

---

## Table of Contents

- [About the Project](#about-the-project)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)

---

## About the Project

DigiRaksha is an AI-based **Digital Arrest & Deepfake Scam Call Shield** built for SIH 2026 (Blockchain & Cybersecurity theme). It detects deepfake voice/video fraud and "digital arrest" scams using:

- **ASR** (faster-whisper) for speech-to-text transcription
- **Voice anti-spoofing** (AASIST) for AI-generated voice detection
- **Video analysis** (OpenCV Haar cascade) for deepfake frame detection
- **Scam classifier** (TF-IDF + LogisticRegression) for scam-script language matching
- **Risk engine** with weighted aggregation and explainable results
- **Family Safe-Voice Registry** for proactive voice verification

---

## Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork:
   ```bash
   git clone https://github.com/reehaanngp-boop/SIH-2026-TERMINAL-BREAKERS.git
   cd SIH-2026-TERMINAL-BREAKERS
   ```
3. **Create a branch** for your change:
   ```bash
   git checkout -b feature/your-feature-name
   ```

---

## Development Setup

### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# Install dependencies (including ML extras)
pip install -e ".[ml]"

# Run the server with auto-reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend

# Install dependencies (including dev tools)
npm install --include=dev

# Start dev server with hot reload
npm run dev    # http://localhost:5173
```

### Run Tests

```bash
cd backend
pytest -q
```

All 92 tests should pass. The slow test loads Whisper and takes ~30 seconds.

---

## Project Structure

```
digi-raksha/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app factory
│   │   ├── config.py              # Settings (pydantic-settings)
│   │   ├── db/                    # SQLAlchemy models + SQLite
│   │   ├── schemas/               # Pydantic request/response models
│   │   ├── core/                  # Risk engine, strings (i18n), job queue
│   │   ├── detectors/             # AI detection modules
│   │   │   ├── audio/             # ASR, voice anti-spoof, speaker verify
│   │   │   ├── video/             # Deepfake frame analysis
│   │   │   └── text/              # Scam script classifier
│   │   ├── services/              # Pipeline orchestration, registry
│   │   ├── api/routes/            # REST API endpoints
│   │   └── static/                # Built frontend (gitignored)
│   ├── ml/                        # Dataset generation + model training
│   ├── scripts/                   # Utility scripts (sample generation)
│   └── tests/                     # pytest test suite
├── frontend/                      # Vite + React + TypeScript SPA
├── data/                          # Runtime data (gitignored)
├── docs/                          # Documentation
└── samples/                       # Demo audio samples
```

---

## Making Changes

### Backend

- **Detectors** go in `app/detectors/`. Each detector has a `describe()` method and returns a standardised result dict with `status`, `score`, `label`, and `metrics`.
- **API routes** go in `app/api/routes/`. Follow the existing pattern with `APIRouter` and Pydantic models.
- **Risk engine** (`app/core/risk_engine.py`) aggregates detector outputs. Weights and thresholds are defined at module level.
- **Localised strings** go in `app/core/strings.py`. Always provide both English (`en`) and Hindi (`hi`) text.
- **Schemas** go in `app/schemas/`. Use Pydantic v2 `BaseModel`.

### Frontend

- **Pages** go in `frontend/src/pages/`.
- **Components** go in `frontend/src/components/`.
- **Translations** go in `frontend/src/i18n.tsx`. Always add both `en` and `hi` entries.
- Use TypeScript for all new code.
- Follow the existing component patterns (functional components, hooks).

### ML / Data Science

- **Dataset generation**: `backend/ml/build_dataset.py`
- **Model training**: `backend/ml/train_classifier.py`
- Training data is synthetic (from I4C/RBI scam advisory templates). Real-world generalisation needs real transcripts — this is a known limitation.

---

## Testing

```bash
cd backend
pytest -q                # Run all tests
pytest -q -m "not slow"  # Skip slow tests (Whisper)
pytest -q -k "test_risk" # Run specific test file/pattern
```

### Test Coverage

| Module | Tests |
|--------|-------|
| Risk engine | 8 tests |
| Scam classifier | 5 tests |
| Registry service | 6 tests |
| API endpoints | 9 tests (incl. 1 slow media pipeline test) |

### Writing Tests

- Tests go in `backend/tests/`.
- Use `pytest` fixtures from `conftest.py`.
- Mark slow tests with `@pytest.mark.slow`.

---

## Code Style

### Python

- **Formatter**: Any PEP 8 compliant style (black, ruff format).
- **Type hints**: Use modern Python 3.12+ syntax (`str | None` not `Optional[str]`).
- **Docstrings**: Module-level docstrings for all files. Method-level for public APIs.
- **Imports**: `from __future__ import annotations` at the top of every file.

### TypeScript/React

- **Strict TypeScript**: No `any` types where avoidable.
- **Functional components**: No class components.
- **Hooks**: Use `useState`, `useMemo`, `useContext` — no external state management libraries.

---

## Submitting a Pull Request

1. Ensure all tests pass: `pytest -q`
2. Build the frontend: `cd frontend && npm run build`
3. Commit your changes with a descriptive message:
   ```bash
   git add .
   git commit -m "feat: add new detector for X"
   ```
4. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
5. Open a Pull Request on the main repository with:
   - A clear title describing the change
   - Description of what was changed and why
   - Any testing steps or screenshots

### PR Guidelines

- Keep PRs focused — one feature or fix per PR.
- Include tests for new functionality.
- Update documentation if adding user-facing features.
- Follow the existing code style and patterns.

---

## Reporting Bugs

Open a GitHub issue with:

- **Title**: Clear, concise description
- **Steps to reproduce**: What you did, what you expected, what happened
- **Environment**: OS, Python version, browser (for frontend issues)
- **Screenshots**: If applicable

---

## Suggesting Features

Open a GitHub issue with:

- **Title**: Feature name
- **Problem**: What problem does this solve?
- **Solution**: Your proposed approach
- **Alternatives**: Other solutions you considered
- **Context**: Any additional information (regulatory requirements, user research, etc.)

---

## Code of Conduct

Be respectful, inclusive, and constructive. We're building a tool to protect people from fraud — let's treat each other with the same care.

---

## Questions?

If you have questions about contributing, open a GitHub issue with the label "question" or reach out to the maintainers.
