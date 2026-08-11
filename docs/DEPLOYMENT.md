# DigiRaksha — Deployment Guide

This guide covers three deployment strategies: **Docker** (recommended for production), **local development**, and **systemd** (bare-metal Linux server).

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Option 1: Docker Compose (Recommended)](#option-1-docker-compose-recommended)
- [Option 2: Local Development](#option-2-local-development)
- [Option 3: systemd Service (Linux)](#option-3-systemd-service-linux)
- [Environment Variables](#environment-variables)
- [Building the Frontend](#building-the-frontend)
- [Retraining the Scam Classifier](#retraining-the-scam-classifier)
- [Data Persistence](#data-persistence)
- [Reverse Proxy (nginx)](#reverse-proxy-nginx)

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.12.x (≥3.12, <3.13) |
| Node.js | 18+ (for frontend build) |
| npm | 9+ |
| Docker | 24+ (for Docker deployment) |
| uv | latest (optional, for venv creation) |

---

## Option 1: Docker Compose (Recommended)

### Quick Start

```bash
cd digi-raksha

# Build and start
docker compose up --build -d

# The app is now running at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Dockerfile

The project root `Dockerfile`:

```dockerfile
FROM python:3.12-slim AS backend

WORKDIR /app

# System dependencies for OpenCV and audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml backend/README.md ./
RUN pip install --no-cache-dir ".[ml]"

COPY backend/ ./
COPY data/ /app/data/

# Build frontend if present
COPY frontend/ /tmp/frontend/
RUN if [ -d /tmp/frontend/src ]; then \
      cd /tmp/frontend && npm install --include=dev && npm run build \
      && cp -r dist/* /app/app/static/ ; \
    fi

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
version: "3.9"
services:
  web:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - digiraksha-data:/app/data
    environment:
      - DATABASE_URL=sqlite:///./data/digiraksha.db
      - MAX_UPLOAD_MB=50
      - MAX_CONCURRENT_JOBS=2
      - CORS_ORIGINS=http://localhost:8000
    restart: unless-stopped

volumes:
  digiraksha-data:
```

### Production Notes

- Mount a named volume for `/app/data` to persist the SQLite database, uploads, and models.
- Set `CORS_ORIGINS` to your actual domain if serving the frontend separately.
- Place a reverse proxy (nginx/Caddy) in front for TLS termination.

---

## Option 2: Local Development

### Backend

```bash
cd digi-raksha/backend

# Create venv (using uv or python -m venv)
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# Install dependencies
pip install -e ".[ml]"

# Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend serves the built React SPA from `app/static/` if present.

### Frontend (Hot Reload)

```bash
cd digi-raksha/frontend

npm install --include=dev
npm run dev    # http://localhost:5173, proxies /api to :8000
```

### Full Stack (Development)

Terminal 1 — Backend:
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Terminal 2 — Frontend:
```bash
cd frontend
npm run dev
```

Visit `http://localhost:5173` for the dev UI with hot reload.

---

## Option 3: systemd Service (Linux)

### Service File

Create `/etc/systemd/system/digiraksha.service`:

```ini
[Unit]
Description=DigiRaksha — AI Scam Call Shield
After=network.target

[Service]
Type=simple
User=digiraksha
Group=digiraksha
WorkingDirectory=/opt/digi-raksha/backend
ExecStart=/opt/digi-raksha/backend/.venv/bin/uvicorn app.main:app \
    --host 0.0.0.0 --port 8000 --workers 1
Restart=on-failure
RestartSec=5
Environment=DATABASE_URL=sqlite:///./data/digiraksha.db
Environment=MAX_CONCURRENT_JOBS=2

# Security hardening
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/digi-raksha/backend/data

[Install]
WantedBy=multi-user.target
```

### Setup

```bash
# Create service user
sudo useradd -r -s /bin/false digiraksha

# Deploy code
sudo mkdir -p /opt/digi-raksha
sudo cp -r . /opt/digi-raksha/
sudo chown -R digiraksha:digiraksha /opt/digi-raksha

# Build frontend
cd /opt/digi-raksha/frontend
sudo -u digiraksha npm install --include=dev
sudo -u digiraksha npm run build

# Install Python deps
cd /opt/digi-raksha/backend
sudo -u digiraksha python -m venv .venv
sudo -u digiraksha .venv/bin/pip install -e ".[ml]"

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable --now digiraksha
```

---

## Environment Variables

All settings can be configured via environment variables or a `.env` file in the project root.

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `DigiRaksha` | Application name |
| `VERSION` | `0.1.0` | Version string |
| `DEBUG` | `false` | Enable auto-reload and verbose errors |
| `API_PREFIX` | `/api/v1` | API route prefix |
| `DATABASE_URL` | `sqlite:///./data/digiraksha.db` | SQLAlchemy database URL |
| `DATA_DIR` | `./data` | Root data directory |
| `UPLOAD_DIR` | `./data/uploads` | Temporary upload storage |
| `MODEL_DIR` | `./data/models` | ML model storage |
| `STATIC_DIR` | `./backend/app/static` | Built frontend assets |
| `MAX_UPLOAD_MB` | `50` | Maximum upload file size |
| `MAX_DURATION_SECONDS` | `600` | Maximum media duration |
| `WHISPER_MODEL_SIZE` | `small` | Whisper model: tiny/base/small/medium |
| `WHISPER_DEVICE` | `cpu` | Compute device |
| `WHISPER_COMPUTE_TYPE` | `int8` | Quantization type |
| `ENABLE_AASIST` | `true` | Enable AASIST voice anti-spoofing |
| `JOB_TIMEOUT_SECONDS` | `900` | Analysis job timeout |
| `MAX_CONCURRENT_JOBS` | `2` | Max parallel analysis jobs |
| `VIDEO_FRAME_INTERVAL` | `5` | Analyse every Nth video frame |
| `VIDEO_MAX_FRAMES` | `240` | Max video frames analysed |
| `VERIFY_SIMILARITY_THRESHOLD` | `0.5` | Speaker verification threshold |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Allowed CORS origins (comma-separated) |

---

## Building the Frontend

The frontend is a Vite + React + TypeScript SPA. Build output goes to `backend/app/static/` which FastAPI serves automatically.

```bash
cd frontend
npm install --include=dev
npm run build
```

> **Note:** A global `npm config omit=dev` may exist on this machine. Always pass `--include=dev` explicitly or Vite/TypeScript dev dependencies won't install.

---

## Retraining the Scam Classifier

The scam classifier is trained on synthetic data generated from I4C/RBI scam advisory templates.

```bash
cd backend

# Generate dataset (2,508 samples by default)
.venv/Scripts/python.exe ml/build_dataset.py --per-category 420

# Train and save model
.venv/Scripts/python.exe ml/train_classifier.py
```

The trained model is saved to `data/models/scam_classifier.joblib`.

---

## Data Persistence

| Path | Contents |
|------|----------|
| `data/digiraksha.db` | SQLite database (scans, family members, voice enrollments) |
| `data/uploads/` | Temporary uploaded media files |
| `data/models/` | ML models (scam classifier, AASIST checkpoint) |
| `data/datasets/` | Generated training data |
| `data/samples/` | Demo audio samples |

Back up `data/digiraksha.db` regularly in production. The `uploads/` directory can be cleaned periodically.

---

## Reverse Proxy (nginx)

For production, place nginx in front:

```nginx
server {
    listen 80;
    server_name digiraksha.example.com;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

For HTTPS, use Certbot or your preferred TLS solution with this nginx config as a base.
