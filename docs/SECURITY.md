# DigiRaksha — Security Policy

## Overview

DigiRaksha is designed with privacy and security as core principles. All analysis runs locally — no data leaves your server. This document covers the security model, threat considerations, and responsible disclosure.

---

## Threat Model

### What DigiRaksha Protects Against

1. **Digital Arrest Scams** — Fraudsters impersonating police/CBI/customs officials who demand "verification fees" over video calls.
2. **Deepfake Voice Cloning** — AI-generated voice clones used to impersonate family members in distress.
3. **Deepfake Video** — Face-swapped or manipulated video used to make scams appear authentic.
4. **OTP/Financial Phishing** — Social engineering calls that pressure victims into sharing bank details, OTPs, or UPI PINs.

### What DigiRaksha Does NOT Replace

- **Law enforcement reporting** — Always report to [1930](tel:1930) or [cybercrime.gov.in](https://cybercrime.gov.in).
- **Bank fraud prevention** — Contact your bank immediately if financial details have been shared.
- **Professional security auditing** — This is an awareness tool, not a certified security product.

---

## Data Handling

### Local-Only Processing

- All audio/video analysis runs **on your server** using local ML models.
- No data is sent to external APIs, cloud services, or third parties.
- The Whisper ASR model runs locally (CPU int8 quantisation).
- The AASIST anti-spoofing model runs locally (PyTorch).
- The scam classifier runs locally (scikit-learn/joblib).

### Data Storage

| Data | Storage | Retention |
|------|---------|-----------|
| Uploaded files | `data/uploads/` | Temporary — can be cleaned periodically |
| Analysis results | `data/digiraksha.db` (SQLite) | Retained until manually deleted |
| Voice enrollments | `data/digiraksha.db` (SQLite) | Retained until member is deleted |
| ML models | `data/models/` | Permanent |

### Recommended Practices

- **Back up** `data/digiraksha.db` regularly.
- **Clean** `data/uploads/` periodically to reclaim disk space.
- **Restrict access** to the server — the web interface has no built-in authentication.
- **Use HTTPS** in production via a reverse proxy (nginx/Caddy).
- **Restrict CORS** — set `CORS_ORIGINS` to your actual domain, not `*`.

---

## Network Security

- The backend binds to `0.0.0.0:8000` by default. In production, place a reverse proxy in front.
- CORS is configured to allow only specified origins (default: localhost dev ports).
- No authentication is built into the API — add authentication middleware (OAuth2, API keys, etc.) for production deployments exposed to the internet.

### Recommended Production Setup

```
Internet → nginx (TLS) → DigiRaksha (localhost:8000)
```

- Enable HTTPS with Certbot or your TLS solution.
- Add rate limiting in nginx to prevent abuse.
- Restrict access to `/docs` and `/redoc` (Swagger UI) in production.

---

## Vulnerability Scanning

### Dependencies

The project uses known ML and web frameworks. Before deploying:

```bash
# Check Python dependencies for known vulnerabilities
pip install safety
safety check

# Check Node.js dependencies
cd frontend
npm audit
```

### Model Security

- ML models are loaded from local files (`data/models/`). Only use models from trusted sources.
- The AASIST checkpoint is fetched from HuggingFace (`arnabdas8901/aasist-trained-asvspoof2024`).
- The scam classifier is trained on locally generated synthetic data.

---

## Responsible Disclosure

If you discover a security vulnerability in DigiRaksha:

1. **Do NOT** open a public GitHub issue for security vulnerabilities.
2. Email the maintainers (or use GitHub's private vulnerability reporting if available).
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We aim to acknowledge reports within 48 hours and provide a fix timeline within 7 days.

---

## Privacy Considerations

- **No analytics or telemetry** — DigiRaksha does not phone home or collect usage data.
- **No external API calls** — All processing is local.
- **No user accounts** — The system has no built-in authentication (suitable for single-user or trusted-network deployments).
- **Indian regulatory context** — This tool aligns with MHA/I4C, MeitY, and RBI advisories on cyber fraud awareness. It does not store or process personal data beyond what the user explicitly uploads.

---

## Build Reproducibility

- Python dependencies are pinned in `backend/pyproject.toml`.
- Frontend dependencies are locked in `frontend/package-lock.json` (if present) or specified in `package.json`.
- The venv was created with Python 3.12.x (system Python 3.14 is not supported due to missing wheels for librosa/opencv).

For a fully reproducible build, use the Docker deployment which pins the Python version and system dependencies.
