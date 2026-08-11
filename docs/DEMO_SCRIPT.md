# DigiRaksha — Demo Script

A step-by-step guide for presenting DigiRaksha at SIH 2026 or other events.

---

## Pre-Demo Checklist

- [ ] Backend running: `http://localhost:8000`
- [ ] Frontend built and served (or dev server on `http://localhost:5173`)
- [ ] Demo samples exist in `data/samples/` (generated via `scripts/generate_samples.py`)
- [ ] Swagger docs accessible: `http://localhost:8000/docs`
- [ ] Language toggle working (EN ↔ HI)

---

## Demo Flow (5–7 minutes)

### 1. Introduction (30 seconds)

> "DigiRaksha is an AI-powered shield against Digital Arrest scams and deepfake voice/video fraud. It analyses suspicious calls and gives you an explainable risk score with actionable next steps — in English and Hindi."

**Show:** Landing page with the tagline.

---

### 2. The Problem (30 seconds)

> "Scammers now use AI-cloned voices and real-time deepfake video to impersonate police, judges, and family members. The 'digital arrest' scam has made lakhs of Indians pay fake penalties. Victims can't tell the synthetic voice from the real one."

**Show:** Navigate to the **About** page.

---

### 3. Live Demo — Transcript Analysis (1 minute)

1. Go to **Analyse** → **Paste transcript** tab.
2. Paste this sample scam transcript:
   ```
   This is the CBI. You are under digital arrest for money laundering. 
   Do not disconnect this video call. You must pay the verification fee 
   of 50,000 rupees immediately to clear your name. Share your OTP for 
   verification.
   ```
3. Click **Analyse**.
4. **Result:** High risk score (~100). Multiple red flags:
   - "Matches known 'digital arrest' scam script" (critical)
   - "Requests for OTP / bank verification" (critical)
5. **Show:** Next steps — "Hang up and verify", "Never share OTP", "Report to 1930".

---

### 4. Live Demo — Audio Analysis (1.5 minutes)

1. Go to **Upload recording / video** tab.
2. Upload `data/samples/scam_digital_arrest.wav` (demo sample).
3. **Result:** High risk — the system:
   - Transcribed the audio (Whisper)
   - Detected synthetic voice (AASIST)
   - Matched scam script patterns
4. **Show:** All four detector signals and their individual findings.

**Optional:** Upload `data/samples/benign_restaurant.wav` to show a low/medium risk result and contrast.

---

### 5. Family Safe-Voice Registry (1.5 minutes)

> "The proactive layer. Enrol your family's real voices once. When a 'this is your relative in trouble' call comes in, check it in seconds."

1. Go to **Safe-Voice Registry**.
2. Add a family member (e.g., "Maa", relationship: "Mother").
3. Click **Enrol voice** → upload a voice sample.
4. Click **Verify a call** → upload a suspicious voice note.
5. **Result:** "Matches" or "Does NOT match" with similarity score.

**Talking point:** "If the similarity is below the threshold, this is likely a deepfake clone — do not trust the caller."

---

### 6. Hindi Demo (30 seconds)

1. Switch language to **Hindi** (🌐 button).
2. Show the same results in Hindi.
3. **Talking point:** "Fully localised for Hindi-speaking users — the primary victims of these scams."

---

### 7. Architecture Overview (1 minute)

**Show:** Swagger docs at `/docs`.

> "The system runs four AI models in parallel: Whisper for transcription, AASIST for voice anti-spoofing, OpenCV for video frame analysis, and a TF-IDF + Logistic Regression classifier for scam script matching. The risk engine combines their outputs with weighted aggregation and produces an explainable verdict."

**Key points:**
- All processing is **local** — no data leaves the server.
- **28 tests** passing.
- Graceful degradation when models are unavailable.

---

### 8. Impact & Reporting (30 seconds)

> "Every result includes official reporting channels: the national helpline 1930 and cybercrime.gov.in. DigiRaksha doesn't just detect fraud — it guides victims to take action."

**Show:** The "What to do next" section with helpline links.

---

## API Demo (for technical judges)

```bash
# 1. Health check
curl http://localhost:8000/api/v1/health

# 2. Check detector availability
curl http://localhost:8000/api/v1/meta

# 3. Analyse a transcript
curl -X POST http://localhost:8000/api/v1/analyze/transcript \
  -H "Content-Type: application/json" \
  -d '{"text": "This is CBI, you are under digital arrest. Pay 50000 verification fee."}'

# 4. Upload and analyse
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "file=@data/samples/scam_digital_arrest.wav"

# 5. Check scan history
curl http://localhost:8000/api/v1/analyze/history
```

---

## Talking Points for Judges

### Problem Fit (MHA/I4C, MeitY, RBI)

- **MHA/I4C**: Directly addresses the "digital arrest" scam epidemic flagged by the Indian Cyber Crime Coordination Centre.
- **MeitY**: Leverages AI/ML for digital India security — runs on affordable hardware (CPU-only, no GPU required).
- **RBI**: Protects citizens from financial fraud — the scam classifier detects OTP/banking phishing patterns.

### Technical Highlights

- **Explainable AI**: Every risk score comes with specific red flags and next steps — not a black box.
- **Multi-modal analysis**: Audio + video + text analysis in a single pipeline.
- **Bilingual**: Full EN + HI support for the primary victim demographic.
- **Offline-capable**: All models run locally — works in areas with poor connectivity.
- **Lightweight**: CPU-only inference (int8 quantised Whisper, scikit-learn classifier).

### Scalability Path

- SQLite → PostgreSQL for multi-user deployments.
- Add authentication middleware for internet-facing instances.
- Expand scam templates with real-world data from law enforcement partnerships.
- Add regional language support (Tamil, Telugu, Bengali, etc.).

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Demo samples missing | Run `python scripts/generate_samples.py` |
| Whisper not loading | Ensure `.venv` has `faster-whisper` installed; model downloads on first use |
| AASIST not available | Install `torch` and `scipy`: `pip install -e ".[ml]"` |
| Frontend not loading | Run `cd frontend && npm install --include=dev && npm run build` |
| Port 8000 in use | Kill the existing process or use `--port 8001` |
