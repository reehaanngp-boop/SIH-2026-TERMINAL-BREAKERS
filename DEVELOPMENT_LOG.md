# DigiRaksha — Development Log

> Handoff log for continuing work. Read this before making further changes.
> Every entry is dated and records what was done, how it was verified, and any
> gotchas encountered. Append new entries at the bottom when you continue.

Project: **Digital Arrest & Deepfake Scam Call Shield** (SIH 2026 — Blockchain & Cybersecurity theme; MHA/I4C, MeitY, RBI fit).
Root: `https://github.com/reehaanngp-boop/SIH-2026-TERMINAL-BREAKERS`

---

## 1. Quick status (2026-08-04)

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Scaffold + toolchain | ✅ done | Python 3.12.13 venv (uv-created), `pyproject.toml`, hatchling |
| 2 | Backend core (config/DB/models/schemas) | ✅ done | SQLAlchemy 2.0 + SQLite, pydantic-settings |
| 3 | Detectors (ASR/voice/video/text) | ✅ done | faster-whisper, AASIST, OpenCV, TF-IDF+LR |
| 4 | Risk engine + analysis pipeline | ✅ done | weighted aggregation, explainable flags |
| 5 | Family Safe-Voice Registry | ✅ done | MFCC-embedding cosine speaker verification |
| 6 | REST API routes | ✅ done | `/api/v1/*`, job queue, history, registry |
| 7 | Synthetic dataset + scam classifier | ✅ done | 2508 samples, 100% held-out acc, model saved |
| 8 | React frontend | ✅ done | Vite+React+TS, EN/HI i18n, built to `app/static` |
| 9 | Tests | ✅ done | 28 passed (risk engine, classifier, registry, API) |
| 10 | Samples + e2e verification | ✅ done | TTS samples in `data/samples/`, e2e verified |
| 11 | Documentation | ✅ done | Full docs: API, DEPLOYMENT, USER_GUIDE, SECURITY, CONTRIBUTING, DEMO_SCRIPT + root README |
| 12 | GitHub repo + Pages | 🔶 pending | commit everything, push, Pages landing with install steps |

**Remaining to continue (task 12):** `git init` → commit → `gh repo create digiraksha --public --source=. --push` → enable GitHub Pages.

---

## 2. How to run the whole stack

```bash
cd C:\Users\farha\ClaudeWorkspace\digi-raksha\backend

# 1) Backend (FastAPI) — serves the SPA too
./.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
#    -> http://localhost:8000  (React SPA, if app/static/index.html exists)
#    -> http://localhost:8000/docs  (Swagger API)

# 2) Frontend dev mode (hot reload) — optional
cd C:\Users\farha\ClaudeWorkspace\digi-raksha\frontend
npm run dev        # http://localhost:5173, proxies /api to :8000
npm run build      # emits into ../backend/app/static (what FastAPI serves)

# 3) Retrain the scam classifier (after editing ml/build_dataset.py)
cd C:\Users\farha\ClaudeWorkspace\digi-raksha\backend
./.venv/Scripts/python.exe ml/build_dataset.py --per-category 420
./.venv/Scripts/python.exe ml/train_classifier.py

# 4) Regenerate demo samples (pyttsx3 / Windows SAPI5 offline TTS)
./.venv/Scripts/python.exe scripts/generate_samples.py

# 5) Run tests (28 tests; the slow one loads Whisper and takes ~30 s)
./.venv/Scripts/python.exe -m pytest -q
```

---

## 3. Key files map

```
digi-raksha/
├── backend/
│   ├── app/
│   │   ├── main.py                # app factory, CORS, SPA static mount, run()
│   │   ├── config.py              # Settings (pydantic-settings), paths, thresholds
│   │   ├── db/                    # database.py (SQLite/WAL), models.py (Scan, FamilyMember, VoiceEnrollment)
│   │   ├── schemas/               # common.py, analyze.py, registry.py (Pydantic response models)
│   │   ├── core/                  # risk_engine.py, strings.py (EN/HI), jobs.py, exceptions.py
│   │   ├── detectors/
│   │   │   ├── audio/             # asr.py (faster-whisper), voice_spoof.py (AASIST+heuristics),
│   │   │   │                      # aasist_model.py (vendored), speaker_verify.py, audio_utils.py (imageio-ffmpeg)
│   │   │   ├── video/deepfake.py  # OpenCV Haar cascade frame analysis
│   │   │   └── text/scam_classifier.py  # loads data/models/scam_classifier.joblib
│   │   ├── services/              # pipeline.py, registry_service.py, media.py (upload validation)
│   │   ├── api/routes/            # analyze.py, registry.py, health.py, meta.py
│   │   └── static/                # BUILT frontend (gitignored; regenerate via npm run build)
│   ├── ml/                        # build_dataset.py, train_classifier.py
│   ├── scripts/generate_samples.py
│   └── tests/                     # conftest.py, test_risk_engine.py, test_scam_classifier.py,
│                                  # test_registry_service.py, test_api.py
├── frontend/                      # Vite + React + TS SPA (src/pages, src/components, i18n)
└── data/                          # digiraksha.db, uploads/, models/scam_classifier.joblib,
                                   # datasets/scam_dataset.jsonl, samples/*.wav + manifest.json
```

## 4. Architecture summary

```
Upload / transcript
   └─ AnalysisPipeline
        ├─ ASR        faster-whisper (CPU int8)      -> transcript, language
        ├─ Voice      AASIST anti-spoof (torch) + librosa heuristics -> spoof score
        ├─ Video      MesoNet (MesoInception-4, per-face-crop CNN) primary + OpenCV Haar cascade
        │              face localization + flicker heuristic; falls back to heuristics if weights
        │              missing (capped contribution, warning-only in risk engine)
        └─ Text       TF-IDF(word+char) + LogisticRegression (6 classes) -> scam category + prob
        └─ RiskEngine weights {voice:0.40, text:0.35, video:0.25}, renormalised over available signals,
           thresholds LOW<40<MEDIUM<65<HIGH, critical-escalation (1 crit ×1.05, 2+ ×1.15+0.05)
Registry (proactive)  ECAPA-TDNN embedding (192-D, speechbrain spkrec-ecapa-voxceleb) primary,
                      MFCC-stats (52-D) fallback -> cosine similarity vs enrolled samples
                      threshold 0.5 (config: verify_similarity_threshold); old 52-D rows -> 409 re-enroll
```

## 5. Decisions & gotchas (read before touching things)

- **Python is pinned `>=3.12,<3.13`** in `backend/pyproject.toml`. System Python 3.14 has no wheels for librosa/opencv. The venv was created with `uv` (uv binary is currently NOT on PATH — if you need it again, reinstall uv; `python -m ensurepip --upgrade` was used to bootstrap pip instead).
- **`opencv-python` is pinned `<5`.** OpenCV 5 removed `cv2.CascadeClassifier` (used by the video deepfake analyser). Installed: `opencv-python 4.14.0`. Don't upgrade to 5.
- **AASIST checkpoint**: `arnabdas8901/aasist-trained-asvspoof2024/orig_aasist_epoch_1.pth` from HuggingFace (official clovaai URL 404s). It was trained with `filts=[69,[1,32],[32,32],[32,64],[64,64]]` — the default clovaai config (`filts[0]=128`) raises `tensor a(42) must match b(23)`. The correct args live in `app/detectors/audio/aasist_model.py` (`AASIST_D_ARGS`). If you retrain, keep these.
- **`FamilyMember.relationship`** mapped column shadows the `relationship()` ORM helper — models.py aliases it as `orm_relationship`. Keep the alias.
- **Whisper downloads once** to `~/.cache/huggingface` (244 MB for "small"). `AsrDetector.available()` uses `local_files_only=True` so `/meta` never triggers a download.
- **No system ffmpeg needed** — `imageio-ffmpeg` bundles one (used in `audio_utils.py`).
- **Scam classifier** is trained on synthetic data (templates from I4C/RBI advisories). 100% held-out accuracy is expected on that distribution but real-world generalization needs real transcripts — flagged in `docs/` as a limitation.
- **Benign TTS demo samples score `medium`**, not `low`: AASIST correctly flags pyttsx3's synthetic voice as AI-generated. Real human voices score low. For a `low` demo use **transcript mode** (e.g. "restaurant order" → low). See `data/samples/manifest.json` notes.
- **Job flow**: POST `/api/v1/analyze` returns `{job_id}`; poll `GET /api/v1/analyze/jobs/{job_id}`; completed payload carries `result` (full `AnalysisResult`). Jobs run in a ThreadPoolExecutor with progress callbacks.
- **Frontend build** writes into `backend/app/static` (gitignored). To regenerate: `cd frontend && npm install --include=dev && npm run build`. Note: a global `npm config omit=dev` may exist on this machine — pass `--include=dev` explicitly or dev deps (vite/tsc) won't install.

## 6. API surface (all under `/api/v1`)

- `GET  /health` — liveness
- `GET  /meta` — detector availability + report channels (1930, cybercrime.gov.in)
- `POST /analyze/transcript` — body `{text, language_hint?}` → `AnalysisResult` (sync)
- `POST /analyze` — multipart `file` → `{job_id}` (async)
- `GET  /analyze/jobs/{job_id}` — poll
- `GET  /analyze/results/{scan_id}` — fetch completed result
- `GET  /analyze/history?limit=50` — recent scans
- `POST /registry/members` | `GET /registry/members` | `DELETE /registry/members/{id}`
- `POST /registry/members/{id}/enroll` — multipart voice sample
- `POST /registry/verify` — multipart `member_id` + `file` → `{match, similarity, threshold, guidance}`
- Interactive docs: `/docs` (Swagger), `/redoc`

## 7. Test results (2026-08-04)

```
28 passed, 1 deselected (the slow media-upload test when run separately)
  test_risk_engine.py        8 passed
  test_scam_classifier.py    5 passed
  test_registry_service.py   6 passed
  test_api.py                9 passed (incl. 1 slow: full Whisper media pipeline)
```

End-to-end media run:
```
scam_digital_arrest.wav  -> high   (100.0)  text=digital_arrest
scam_courier.wav         -> high   (100.0)  text=fake_courier
benign_restaurant.wav    -> medium ( 49.4)  text=benign   (TTS voice -> AASIST flags synthetic voice; see §5)
```

---

## 8. Changelog

### 2026-08-04 — Core build complete (session 1)
- Backend: all detectors, risk engine, registry, REST API, job queue implemented & smoke-tested.
- Scam classifier: `ml/build_dataset.py` + `ml/train_classifier.py`, 2508 synthetic samples, saved to `data/models/scam_classifier.joblib`.
- Frontend: Vite+React+TS SPA (Analyse / Safe-Voice Registry / History / About, EN+HI), built to `app/static`.
- Fixed: OpenCV 5 → pinned `<5`; `multi_class` kwarg removed in sklearn ≥1.7; np.str_ JSON hygiene in classifier metrics.
- Tests: 28 passing. E2E: scam audio → high, benign transcript → low.
- Generated 5 demo samples in `data/samples/` with `scripts/generate_samples.py`.

### 2026-08-04 — Documentation & packaging (session 2)
- Written full documentation suite: `docs/API.md`, `docs/DEPLOYMENT.md`, `docs/USER_GUIDE.md`, `docs/SECURITY.md`, `docs/CONTRIBUTING.md`, `docs/DEMO_SCRIPT.md`.
- Root `README.md` with badges, features, architecture, install steps (Docker/local/API), API table, detection categories, tech stack, reporting contacts.
- Added `LICENSE` (MIT).
- Updated `.gitignore` — added `backend/app/static/`, `data/*.db*`, IDE patterns.
- Updated `DEVELOPMENT_LOG.md` to reflect completed tasks.

### 2026-08-09 — Accuracy overhaul (false-positive reduction)
Root cause of most false positives: heuristic detectors treated *normal* phone/video-call characteristics as fraud, and the risk engine gave heuristic-only signals critical weight.

**Voice (`voice_spoof.py`)**
- Installed the real AASIST anti-spoof model: `data/models/aasist.pth` (from `arnabdas8901/aasist-trained-asvspoof2024/orig_aasist_epoch_1.pth`). Voice now runs model-backed (engine `aasist`).
- Removed the **bandwidth heuristic** — it flagged telephony-narrowband audio (i.e. *every* real phone call) as synthetic.
- Recalibrated gap/pitch/flatness thresholds so they fire only at genuinely anomalous values, and added an **agreement gate** (≥2 independent features must exceed the suspect threshold before the score is trusted).
- When AASIST is absent (heuristics-only), the risk engine no longer emits AI-clone flags and caps the voice contribution at 0.3.

**Video (`deepfake.py`, `risk_engine.py`)**
- Dropped the "stillness = edited" cues (duplicate-frames, stable sharpness) from the score — steady webcam/video calls were being flagged as deepfakes. Only erratic frame-to-frame flicker remains, with a higher threshold.
- Video heuristic scores are now capped (0.4 contribution) and produce at most a `video-warning`; the critical `video-edited` path is no longer reached by heuristics.

**Text (`build_dataset.py`, `train_classifier.py`, `scam_classifier.py`)**
- Dataset now has **7 balanced classes** (added `neutral`) and richer **benign** transcripts that mention money/courier/banks in legit contexts, plus conversational fillers — 2800 samples. Retrained: 99.8% held-out accuracy.
- Runtime: confidence floor raised `0.35 → 0.5`, and a fraud category is only trusted when it beats benign/neutral by ≥0.15 margin. `other_fraud` risk capped at 0.7; specific scam scripts scale to 0.9.

**Risk engine (`risk_engine.py`)**
- Heuristic-only voice → `voice-cannot-check` (info) + capped score, never critical. Video heuristic → warning + capped. Benign/neutral text → no signal. Critical escalation now only fires on model-backed voice or specific scam scripts.

**Verification**
- `scripts/accuracy_check.py`: 14/14 transcripts match expected level (all benign/neutral → low 5.0; all scams → high 70–94).
- `scripts/audio_check.py`: scam clips → high (98/100/97.7); benign TTS clips → medium *because AASIST correctly flags the synthetic pyttsx3 voice* (real human voices score low). Text signal on benign clips is `benign`.
- Full pytest suite: 67 passing.

### 2026-08-09 — Safe-Voice Registry false-match fix (ECAPA-TDNN upgrade)
Reported: one voice enrolled, but three test MP3s all reported "99% matched".

**Root cause** (`diag_voice_similarity.py`): the old 52-D MFCC-stats embedding
could not separate speakers — *any* two recordings scored cosine 0.64–1.0, so at
the 0.42 threshold every voice matched (100% false-accept rate on real files).

**Fix** — replaced the embedding with a proper neural speaker model:
- `speaker_verify.py` rewritten: **ECAPA-TDNN** (192-D) primary,
  `speechbrain.spkrec-ecapa-voxceleb`, lazy module-level cache, downloaded once
  into `data/models/ecapa-tdnn` (fully offline afterwards); MFCC-stats (52-D)
  kept as a fallback for bare installs. `best_match` now guards embedding
  dimension so old/new vectors are never compared.
- `config.py`: threshold `0.42 → 0.5`, added `enable_ecapa=True`.
- `registry_service.py` / `registry.py`: old 52-D enrollments are detected and
  return a clear **409 `re_enroll_required`** (bilingual guidance added); results
  now carry `engine` + `reason`.
- `voice_match_service.py`: skips wrong-dimension prints (counts them), reports
  `engine` + `skipped_legacy_embeddings`.
- `/meta` now reports `speaker.engine` / `ecapa_ready` / `threshold`.

**Calibration** (`calibrate_threshold.py`): same-speaker ~0.85, different-speaker
~0.18 on this machine's SAPI voices; threshold 0.5 sits cleanly in the gap.

**Verification**
- `diag_voice_similarity.py` (ECAPA): cross-voice cosine now 0.0–0.28 — every
  remaining accept is a byte-identical duplicate file (correct).
- Live API: enroll `29f6c7e…m4a` → verify identical copy `30345e53…m4a`
  **match 1.0**; verify a genuinely different voice **reject 0.14** (was 0.6–1.0).
- Full pytest suite: **69 passing** (fixtures switched from pure tones to real
  SAPI speech — a speech model clusters out-of-distribution tones together).

**New docs:** `docs/AI_MODEL_GUIDE.md` — 7-step recipe for adding any free AI
model, with the ECAPA upgrade as the worked example.

### 2026-08-09 — Video deepfake detector upgraded to MesoNet (real CNN)
The video detector previously used OpenCV heuristics only (Haar-cascade face
cues + flicker). It now scores each sampled face crop with **MesoNet's
MesoInception-4** — a 28k-param CNN trained on FaceForensics-style data to
classify a face crop as real (0) / manipulated (1).

- `app/detectors/video/mesonet_model.py` — faithful PyTorch port of the Keras
  `MesoInception_4` from `DariusAf/MesoNet` (Apache-2.0), incl. the dilated
  3x3 branches and BN `eps=1e-3`.
- `scripts/convert_mesonet_weights.py` — converts `MesoInception_DF.h5` to a
  `.pth` state dict and **proves correctness with an independent numpy forward**
  (`scipy.ndimage.correlate` == 'same' cross-correlation): |numpy − torch| < 1e-4
  on 3 inputs. Saves to `data/models/mesonet/mesoInception_DF.pth` (131 KB).
  Gotchas handled: Keras2.1.5 stores `layer_names` scrambled → sort by numeric
  suffix; `kernel:0` key suffix → strip; dilation must be replicated in numpy.
- `app/detectors/video/deepfake.py` — lazy, cached MesoNet loader behind the
  existing cascade pattern; per-frame RGB face crop is padded to a square,
  resized 256x256, normalized, then scored. Aggregate = 0.5·mean + 0.3·max +
  0.2·fraction>0.5, blended with the flicker heuristic. `engine`/`video_engine`
  field reports `mesonet` vs `unavailable`; graceful fallback to heuristics when
  weights/torch are absent. `describe()` exposes `mesonet_available` → `/meta`.
- **Risk invariant preserved:** the risk engine caps video at 0.4 and emits at
  most a `video-warning` regardless of engine, so a model-backed verdict can
  never push a benign video call to high (tested explicitly).

**Verification**
- New `tests/test_video_deepfake.py` (4 tests): missing-weights fallback,
  real-model crop scoring (256x256 shape/range + score in [0,1]), `/meta`
  reporting, and the risk-cap invariant. Full suite now **73 passing**.
- `scripts/video_check.py` end-to-end: synthetic video → `analyze()` returns
  `engine=mesonet`, risk engine stays `low`. `/meta` shows
  `video.engine = mesonet`.

### 2026-08-09 — Fixed: media scans crash with `Lazy import of ... k2_fsa ... failed`
**Symptom:** every media scan (POST `/analyze`) after a fresh server start failed
in the job queue with `Lazy import of LazyModule(package=None,
target=speechbrain.integrations.k2_fsa, loaded=False) failed`.

**Root cause (Windows-only SpeechBrain defect):** loading ECAPA for `/meta`
imports SpeechBrain, which registers a lazy placeholder for the optional
GPU-only integration `speechbrain.integrations.k2_fsa` in `sys.modules`. When
the scan later imports `librosa` for the first time, librosa's lazy loader runs
`inspect.stack()`, and Python's `inspect.getmodule` walks *every* module in
`sys.modules` calling `hasattr(m, '__file__')`. On a SpeechBrain `LazyModule`
that `hasattr` force-loads the target — `import k2` fails (not installed,
GPU-only). SpeechBrain guards against this (`importutils.py` raises
`AttributeError` when the importer frame ends with `/inspect.py`), but that
guard is **POSIX-only**: on Windows the path is `Lib\inspect.py` with
backslashes, so the guard never fires. A fresh process didn't hit it because
librosa imports before speechbrain ever loads; the server loads speechbrain
first via `/meta`, then librosa trips over the lazy module.

**Fix** (`app/detectors/audio/speaker_verify.py`): `_neutralize_lazy_modules()`,
called right after SpeechBrain is imported in `_ensure_ecapa()`. It gives every
`LazyModule` in `sys.modules` a real `__file__` instance attribute, so
`hasattr(m, '__file__')` short-circuits instead of force-loading. Genuine
attribute access still lazy-loads normally.

**Verification**
- Repro script (load ECAPA → run scan in a worker thread): failed before,
  `OK medium 43.2` after.
- Live API: `/meta` (loads ECAPA) → `POST /analyze` media scan completes,
  `risk 100.0 (high)` on `scam_digital_arrest.wav`.
- Full pytest suite: **73 passing**.

### NEXT (task 12) — remaining
1. `git add .` → commit → `gh repo create digiraksha --public --source=. --push`
2. GitHub Pages: enable from the repo (docs root or main branch) so the README renders.

---

## 2026-08-09 — AI second-opinion layer via OpenRouter (free LLM)

The text dimension only knew the fixed scam scripts the local TF-IDF/LR model
was trained on, so a real scam worded differently could slip through as benign.
Added an opt-in LLM second opinion that reads the transcript plus the local
detector signals (AASIST voice score, MesoNet video score, text label/score,
current risk) and returns a structured verdict. The user chose **escalation**:
a confident AI scam verdict can *raise* a low/medium local verdict (capped,
never lowers a local high), and a **free** model default.

- **Model:** `poolside/laguna-s-2.1:free` ($0) via OpenRouter
  `chat/completions`. Configurable through `OPENROUTER_MODEL`. (Live probing
  showed the nominal `inclusionai/ling-3.0-tiny:free` 429-rate-limited on its
  shared free pool, so the default was switched to the free model that actually
  responds; a short bounded 429 backoff was added to `_post_json`.)
- **Privacy:** OFF by default (`enable_llm_analysis=false`) — enabling sends
  the transcript to an external API. Footer disclaimer updated to stop claiming
  "no data leaves your server".
- **Graceful degradation:** any failure (no key, timeout, HTTP error, unparseable
  reply) → `ai_analysis: null`, verdict identical to the local-only result.
  Stdlib `urllib` only — no new dependency, EXE build unaffected.
- **Files:** new `app/services/llm_analysis.py` + `tests/test_llm_analysis.py`;
  `config.py` (6 settings), `risk_engine.py` (`assess(..., ai=)` + `ai-llm-corrob`
  escalation, constant `AI_ESCALATE_CONFIDENCE=0.7`), `strings.py` (new red flag),
  `pipeline.py` (`_attach_ai` in both entry points), `schemas/analyze.py`
  (`AiVerdict`/`AiAnalysis`), `analyze.py` route (`build_result_model`),
  `detectors/__init__.py` (`/meta` reports `ai`), frontend `types.ts`/`i18n.tsx`/
  `Results.tsx` (AI card), rebuilt static bundle.

**Verification**
- New unit tests (17): parsing (fenced/prose/garbage), disabled/missing-key/short
  transcript, transport failure → None, assess escalation/no-op/never-downgrade,
  pipeline wiring. Full suite **90 passing**.
- Frontend: `tsc --noEmit && vite build` clean; new bundle in `app/static`.
- Live API (AI off): `/meta` reports `ai.available=false`, model id present;
  `POST /analyze/transcript` on a digital-arrest script → `high 93.0`,
  `ai_analysis: null`, no crash.
- **TODO (needs user's OpenRouter key):** set `ENABLE_LLM_ANALYSIS=true` +
  `OPENROUTER_API_KEY` in `.env`, restart, re-scan → expect `ai_analysis.verdict`
  + `ai-llm-corrob` flag + escalated risk.
