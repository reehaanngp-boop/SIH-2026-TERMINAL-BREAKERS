# DigiRaksha — How to Add an AI Model

A step-by-step playbook for integrating any free, offline-capable AI model into
DigiRaksha. Use this when you want to add or upgrade a detector — voice, audio,
text, or video.

It is built around the **ECAPA-TDNN speaker-verification upgrade** as a worked
example (the whole thing landed in this repo in one sitting), so you can see the
pattern against real code rather than an abstraction.

---

## 1. The 3 rules of choosing a model (free)

| Rule | Why | Example |
|------|-----|---------|
| **Truly free** — open weights, no per-call API fee | A hackathon demo and a student project must cost ₹0 and run offline | ECAPA-TDNN (Apache-2.0), AASIST (already vendored), faster-whisper (MIT) |
| **Runs on your machine** — CPU-only, fits RAM | No GPU on this laptop; a model that needs a GPU is dead weight | `small` Whisper (~2 GB RAM), ECAPA (~40 MB) |
| **First-class Python / ONNX / HF Hub support** | You want `pip install` + a download, not a C++ build | Anything on Hugging Face Hub |

Avoid: proprietary APIs with keys, models needing >4 GB RAM on CPU, models with
no pretrained weights.

**Rule of thumb for accuracy-first:** for each of the 4 detectors, pick the
strongest *open-weights* model you can run in <10 s per file on a CPU. The
current stack after this upgrade:

| Task | Model | License | Size |
|------|-------|---------|------|
| Speech-to-text | faster-whisper `small` | MIT | ~460 MB |
| Voice anti-spoof (AI-cloned voice) | AASIST | Apache-2.0 | ~5 MB |
| **Speaker verification (registry)** | **ECAPA-TDNN** (`speechbrain/spkrec-ecapa-voxceleb`) | Apache-2.0 | ~40 MB |
| Text scam classifier | TF-IDF + logistic regression (own model) | — | ~1 MB |
| Video deepfake | OpenCV heuristics (see §7 for upgrade path) | BSD | — |

---

## 2. The recipe (7 steps)

Every model integration follows the same shape. Do it in this order.

### Step 1 — Add a config toggle

Never hard-wire a model on. Add two settings: an `enable_*` flag and any
thresholds the model needs.

```python
# app/config.py
class Settings(BaseSettings):
    ...
    # Speaker verification (Safe-Voice Registry)
    verify_similarity_threshold: float = 0.5
    enable_ecapa: bool = True  # ECAPA-TDNN embedding; falls back to MFCC stats
```

Thresholds go in config so you can recalibrate them without touching code.

### Step 2 — Write a detector module with a *lazy, cached* loader

The two things that break hackathon demos are (a) models that take 20 s to load
blocking startup, and (b) crashes when a model file is missing. Solve both:

- load the model **on first use**, not at import time;
- cache it in a module-level variable;
- return `None` (or fall back) on any load failure.

```python
# app/detectors/audio/speaker_verify.py
_classifier = None          # cached across calls
_classifier_error = None

def _ensure_ecapa() -> Any:
    global _classifier, _classifier_error
    if _classifier is not None:
        return _classifier
    if not settings.enable_ecapa:
        return None
    try:
        from speechbrain.inference.speaker import EncoderClassifier
        classifier = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir=str(settings.model_dir / "ecapa-tdnn"),
            run_opts={"device": "cpu"},
            local_strategy=LocalStrategy.COPY,   # Windows-safe (no symlinks)
        )
        classifier.eval()
        _classifier = classifier
        return classifier
    except Exception as exc:
        _classifier_error = str(exc)
        return None
```

### Step 3 — Provide availability probes for `/meta`

So the frontend can show "AI engine: ECAPA ✅ / fallback ⚠️" without triggering a
model download, add a **cheap on-disk check** and surface it:

```python
def ecapa_model_present() -> bool:            # fast: files on disk?
    return (settings.model_dir / "ecapa-tdnn" / "hyperparams.yaml").exists()

def ecapa_ready() -> bool:                    # fast probe for /meta
    return settings.enable_ecapa and _ecapa_importable() and ecapa_model_present()

def embedding_engine() -> str:                # authoritative engine actually used
    return "ecapa" if _ensure_ecapa() is not None else "mfcc"
```

Wire it into the detector registry (`app/detectors/__init__.py`, `describe()`)
so it shows up at `GET /api/v1/meta`.

### Step 4 — Keep a fallback path

If the model can't load (offline first-run, missing dependency), the app should
**degrade, not crash**:

```python
def compute_embedding(audio):
    emb = _ecapa_embedding(audio)     # None if model unavailable
    if emb is not None:
        return emb
    return _mfcc_embedding(audio)     # old 52-D stats — still works
```

### Step 5 — Guard dimension changes

Neural embeddings have a fixed size (ECAPA = 192-D, the old MFCC = 52-D). **Never
compare two embeddings of different sizes** — the cosine is meaningless. Always
filter by dimension and tell the user to re-enrol when nothing matches:

```python
dim = int(len(probe))
compatible = [e for e in enrollments if len(e["embedding"]) == dim]
if not compatible:
    return {... "match": None, "reason": "incompatible",
            "guidance": _guidance("incompatible", name)}
```

### Step 6 — Calibrate the threshold on *your* data

Do not trust the model's default threshold. Embed known examples, compute the
cosine/similarity matrix, and pick a threshold in the gap:

```text
SAME speaker  (David vs David)      -> 0.85 - 1.00
DIFFERENT speakers (David vs Zira)  -> 0.10 - 0.30
            chosen threshold        -> 0.50   <-- sits in the gap
```

Script: `backend/scripts/calibrate_threshold.py`. Run the diagnostic before and
after: `backend/scripts/diag_voice_similarity.py`.

### Step 7 — Test, then verify live

- **Unit tests** on real fixtures (tones are useless — a speech model treats
  them as out-of-distribution and clusters them all together; use real speech).
  See `tests/test_registry_service.py` and `tests/fixtures/speaker_{david,zira}.wav`.
- **Live check** against the running server: enroll a real file, verify a
  byte-identical copy (must match) and a genuinely different voice (must reject).

---

## 3. Model storage & offline behaviour

- Models live under `data/models/<name>/` (`settings.model_dir`).
- **First use downloads** into that folder (needs internet once).
- **Afterwards it's fully offline**: SpeechBrain's `fetch` skips files that
  already exist, and the code passes `FetchConfig(allow_network=not have_local)`.
- To ship the model on a machine with no internet, just copy the folder into
  `data/models/` — `ecapa_model_present()` will find it and load offline.

---

## 4. Windows gotchas (this repo runs on Windows 11, no GPU)

| Gotcha | Fix |
|--------|-----|
| SpeechBrain `WinError 1314` (symlink) when saving the model | pass `local_strategy=LocalStrategy.COPY` |
| Deprecated `speechbrain.pretrained` API | import from `speechbrain.inference.speaker` |
| `.cache` in the user profile instead of `data/models` | set `savedir=settings.model_dir / <name>` explicitly |
| HF Hub rate limits on unauthenticated downloads | set `HF_TOKEN` for faster downloads (optional) |

---

## 5. Adding a whole *new* detector (not just upgrading)

Same recipe plus wiring into the pipeline:

1. Create `app/detectors/<modality>/<name>.py` with a `describe()` method
   (name, description, `available`).
2. Add it to `DetectorManager` in `app/detectors/__init__.py`.
3. Add its result to the analysis pipeline `app/services/pipeline.py` and fold
   its score into the risk engine (`app/core/risk_engine.py`) with a weight.
4. Add any new fields to the Scan/analysis schemas and the frontend result card.
5. Expose availability via `describe()` → `/api/v1/meta`.

---

## 6. Future upgrade path for each detector

- **Video deepfake (current: OpenCV heuristics)** → replace with a CNN that runs
  on CPU, e.g. an EfficientNet fine-tuned on the **DFDC / Celeb-DF** dataset
  (free to download, ~1-4 GB). Keep the frame sampler; run the CNN per face crop
  instead of hand-crafted heuristics.
- **Text scam (TF-IDF + LR)** → keep the fast model for the 100% hit path and
  layer a stronger transformer (e.g. **multilingual DistilBERT** / a fine-tuned
  `bert-base-multilingual-cased` on scam scripts) as a second opinion only when
  confidence is low. Transformers on CPU are slow, so use them sparingly.
- **ASR** → move `small` → `medium` Whisper if RAM allows (~4 GB).
- **Voice anti-spoof** → already AASIST (SOTA on LA/PA of ASVspoof2019).

---

## 7. Checklist before you call it done

- [ ] `enable_*` flag exists and default matches this machine
- [ ] Model loads lazily and is cached
- [ ] `/api/v1/meta` reports availability without forcing a download
- [ ] Fallback path exists when the model is absent
- [ ] Embedding/feature dimension mismatch is guarded
- [ ] Threshold was calibrated on real data, not the model default
- [ ] Tests use real audio fixtures, not pure tones
- [ ] Works fully offline after the first download
- [ ] Updates to `DEVELOPMENT_LOG.md` appended
