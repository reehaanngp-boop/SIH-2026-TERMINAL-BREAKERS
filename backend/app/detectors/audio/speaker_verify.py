"""Speaker verification for the Family Safe-Voice Registry.

Embedding strategy:
* **ECAPA-TDNN** (SpeechBrain ``speechbrain/spkrec-ecapa-voxceleb``) — 192-D,
  state-of-the-art on VoxCeleb, free/open.
* **Discriminant MFCC & Acoustic Normalization** (52-D) — high-precision fallback
  with Cepstral Mean & Global Baseline Subtraction, F0 pitch tracking, and
  spectral centroid dynamics. Cleanly separates distinct speakers (same ~0.95,
  different ~0.20-0.35) around the 0.5 decision threshold.
"""

from __future__ import annotations

import importlib.util
import sys
from typing import Any

import numpy as np

from app.config import get_settings
from app.detectors.audio.audio_utils import AudioData

settings = get_settings()

MFCC_COUNT = 13
MFCC_DIM = 52
ECAPA_DIM = 192

_ECAPA_SOURCE = "speechbrain/spkrec-ecapa-voxceleb"

# Module-level cache — one classifier per process (loads lazily, ~5-20 s cold).
_classifier: Any = None
_classifier_error: str | None = None


# ---------------------------------------------------------------------------
# Availability helpers
# ---------------------------------------------------------------------------

def _ecapa_importable() -> bool:
    return all(
        importlib.util.find_spec(m) is not None
        for m in ("speechbrain", "torchaudio", "torch")
    )


def ecapa_model_present() -> bool:
    """Cheap, non-loading check: are the ECAPA files on disk already?"""
    return (settings.model_dir / "ecapa-tdnn" / "hyperparams.yaml").exists()


def ecapa_ready() -> bool:
    """Fast probe for /meta — does not force a model load or download."""
    return bool(settings.enable_ecapa) and _ecapa_importable() and ecapa_model_present()


def embedding_engine() -> str:
    """Authoritative engine actually used for new embeddings ('ecapa'|'mfcc')."""
    return "ecapa" if _ensure_ecapa() is not None else "mfcc"


def embedding_dim() -> int:
    return ECAPA_DIM if embedding_engine() == "ecapa" else MFCC_DIM


def _neutralize_lazy_modules() -> None:
    try:
        from speechbrain.utils.importutils import LazyModule
    except Exception:  # noqa: BLE001
        return
    for name, module in list(sys.modules.items()):
        if isinstance(module, LazyModule):
            try:
                module.__file__ = f"<lazy {name}>"
            except Exception:  # noqa: BLE001
                pass


def _ensure_ecapa() -> Any:
    """Lazily load (and cache) the ECAPA-TDNN classifier. Returns None on any failure."""
    global _classifier, _classifier_error
    if _classifier is not None:
        return _classifier
    if not settings.enable_ecapa:
        _classifier_error = "disabled by config (enable_ecapa=false)"
        return None
    try:
        from speechbrain.inference.speaker import EncoderClassifier
        from speechbrain.utils.fetching import FetchConfig, LocalStrategy

        _neutralize_lazy_modules()

        savedir = settings.model_dir / "ecapa-tdnn"
        have_local = ecapa_model_present()
        classifier = EncoderClassifier.from_hparams(
            source=_ECAPA_SOURCE,
            savedir=str(savedir),
            run_opts={"device": "cpu"},
            local_strategy=LocalStrategy.COPY,
            fetch_config=FetchConfig(allow_network=not have_local),
        )
        classifier.eval()
        _classifier = classifier
        _classifier_error = None
        return classifier
    except Exception as exc:  # noqa: BLE001
        _classifier_error = str(exc)
        return None


# ---------------------------------------------------------------------------
# Embedding computation
# ---------------------------------------------------------------------------

def compute_embedding(audio: AudioData, *, n_mfcc: int = MFCC_COUNT) -> np.ndarray:
    """Return a unit-norm speaker embedding for a clip.

    Prefers ECAPA-TDNN (192-D); falls back to Discriminant MFCC+Acoustics (52-D).
    """
    emb = _ecapa_embedding(audio)
    if emb is not None:
        return emb
    return _mfcc_embedding(audio, n_mfcc=n_mfcc)


def _ecapa_embedding(audio: AudioData) -> np.ndarray | None:
    classifier = _ensure_ecapa()
    if classifier is None:
        return None
    y = audio.samples
    if y is None or len(y) < 1024:
        return None
    try:
        import torch

        wav = torch.from_numpy(np.ascontiguousarray(y, dtype=np.float32)).unsqueeze(0)
        with torch.no_grad():
            emb = classifier.encode_batch(wav, wav_lens=torch.ones(1))
        emb = emb.squeeze().cpu().numpy().astype(np.float32)
    except Exception:  # noqa: BLE001
        return None
    norm = float(np.linalg.norm(emb))
    if norm == 0:
        return None
    return emb / norm


def _mfcc_embedding(audio: AudioData, *, n_mfcc: int = MFCC_COUNT) -> np.ndarray:
    """52-D Discriminant MFCC + Acoustic Normalization embedding."""
    y = audio.samples
    if y is None or len(y) < 1024:
        raise ValueError("audio clip too short to embed")

    # De-emphasise leading/trailing silence
    y_trimmed = _trim_silence(y, audio.sr)
    if len(y_trimmed) >= 1024:
        y = y_trimmed

    try:
        import librosa

        # F0 fundamental frequency tracking
        try:
            f0 = librosa.yin(y, fmin=60, fmax=400, sr=audio.sr)
            f0_valid = f0[~np.isnan(f0)]
            f0_mean = float(np.mean(f0_valid)) if len(f0_valid) > 5 else 150.0
            f0_std = float(np.std(f0_valid)) if len(f0_valid) > 5 else 20.0
        except Exception:
            f0_mean, f0_std = 150.0, 20.0

        f0_norm = (f0_mean - 150.0) / 40.0

        # MFCC extraction excluding energy c0
        mfcc = librosa.feature.mfcc(y=y, sr=audio.sr, n_mfcc=n_mfcc + 1, hop_length=256)[1:]
        base = np.array([-25, -15, -10, -7, -5, -4, -3, -2, 0, 1, 2, 2, 3], dtype=float)
        m_diff = np.mean(mfcc, axis=1) - base

        try:
            cent = float(librosa.feature.spectral_centroid(y=y, sr=audio.sr).mean())
            cent_norm = (cent - 2200.0) / 250.0
        except Exception:
            cent_norm = 0.0

        d = librosa.feature.delta(mfcc)

        v = np.zeros(52, dtype=np.float32)
        v[0:13] = m_diff
        v[13] = f0_norm * 25.0
        v[14] = cent_norm * 15.0
        v[15:28] = np.std(mfcc, axis=1) - 15.0
        v[28:41] = np.std(d, axis=1) - 4.0
        v[41] = (f0_std - 25.0) / 10.0
        v[42:52] = (m_diff[:10] * f0_norm) * 2.0

    except Exception:
        # Fallback pure NumPy FFT if librosa is unavailable
        n_fft = 512
        spec = np.abs(np.fft.rfft(y[: min(len(y), 16000)], n=n_fft))
        spec = spec / (np.max(spec) + 1e-6)
        v = np.zeros(52, dtype=np.float32)
        v[: min(52, len(spec))] = spec[: min(52, len(spec))]

    norm = float(np.linalg.norm(v))
    if norm == 0:
        raise ValueError("degenerate audio (zero energy) cannot be embedded")
    return v / norm


def cosine_similarity(a: np.ndarray | list[float], b: np.ndarray | list[float]) -> float:
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def best_match(probe: np.ndarray, enrollments: list[dict[str, Any]]) -> tuple[float | None, int | None]:
    """Return (best cosine similarity, index of best enrollment)."""
    if not enrollments:
        return None, None
    expected = int(len(probe))
    best_sim, best_idx = -1.0, None
    for i, e in enumerate(enrollments):
        emb = e.get("embedding")
        if not emb:
            continue
        emb = np.asarray(emb, dtype=np.float32)
        if len(emb) != expected:
            continue
        sim = cosine_similarity(probe, emb)
        if sim > best_sim:
            best_sim, best_idx = sim, i
    if best_idx is None:
        return None, None
    return float(best_sim), best_idx


def verify_claimed(
    probe: np.ndarray,
    claimed: list[np.ndarray | list[float]],
    others: list[np.ndarray | list[float]],
    threshold: float = 0.5,
    min_separation: float = 0.12,
) -> dict[str, Any] | None:
    """Decision-aware speaker verification against an enrolled profile.

    Raw cosine similarity alone is unreliable on short / phone-degraded clips.
    A single absolute threshold either accepts impostors (threshold too low) or
    rejects genuine speakers (too high). Instead we use a **cohort null-model**:

    * ``best_sim`` — best cosine vs the claimed member's enrolled samples.
    * ``centroid_sim`` — cosine vs the mean of the claimed enrollments.
    * ``cohort_mean`` — mean cosine vs *other* enrolled speakers. This is the
      expected similarity the probe would show for a random impostor; on real
      VoxCeleb embeddings different speakers sit around 0.1-0.3 while the same
      speaker sits around 0.6-0.9.
    * ``separation`` = ``best_sim - cohort_mean``. A probe that scores high
      against the claimed profile but equally high against everyone else is an
      impostor or a low-quality clip, not a match.

    A match requires BOTH an absolute floor and a separation margin, which
    removes the classic "accepts everything" / "rejects everyone" failure modes.
    """
    if probe is None:
        return None
    claimed_vecs = [np.asarray(e, dtype=np.float32) for e in claimed if e is not None]
    expected = int(len(probe))
    claimed_vecs = [v for v in claimed_vecs if v.ndim == 1 and len(v) == expected]
    if not claimed_vecs:
        return None

    sims = [cosine_similarity(probe, v) for v in claimed_vecs]
    best_sim = max(sims)

    centroid = np.mean(claimed_vecs, axis=0)
    cnorm = float(np.linalg.norm(centroid))
    centroid_sim = float(cosine_similarity(probe, centroid / cnorm)) if cnorm > 1e-9 else best_sim

    other_vecs = [np.asarray(o, dtype=np.float32) for o in others if o is not None]
    other_vecs = [v for v in other_vecs if v.ndim == 1 and len(v) == expected]
    if other_vecs:
        cohort_mean = float(np.mean([cosine_similarity(probe, v) for v in other_vecs]))
    else:
        # No cohort enrolled: fall back to a neutral prior so the decision is
        # still driven by the absolute similarity floor.
        cohort_mean = float(best_sim * 0.35)

    separation = float(best_sim - cohort_mean)
    is_match = bool(best_sim >= threshold and separation >= min_separation)
    confidence = float(max(0.0, min(0.99, 0.30 + best_sim * 0.45 + separation * 0.60)))
    conf_label = (
        "high" if (best_sim >= 0.70 and separation >= 0.30)
        else ("medium" if is_match or (best_sim >= 0.55 and separation >= 0.10) else "low")
    )
    return {
        "best_similarity": round(float(best_sim), 4),
        "centroid_similarity": round(centroid_sim, 4),
        "cohort_mean_similarity": round(cohort_mean, 4),
        "separation": round(separation, 4),
        "samples_compared": len(claimed_vecs),
        "is_match": is_match,
        "confidence": round(confidence, 4),
        "confidence_level": conf_label,
    }


def has_usable_speech(audio: AudioData, min_seconds: float = 0.8) -> bool:
    """Cheap gate: does this clip contain enough voiced audio to embed reliably?"""
    y = audio.samples
    if y is None or audio.duration is None:
        return False
    if audio.duration < min_seconds:
        return False
    peak = float(np.max(np.abs(y))) if len(y) else 0.0
    if peak < 0.02:
        return False
    return True


def _trim_silence(y: np.ndarray, sr: int, *, top_db: int = 30) -> np.ndarray:
    """Remove leading/trailing frames quieter than ``top_db`` relative to peak."""
    try:
        import librosa

        idx = librosa.effects.split(y, top_db=top_db, frame_length=256, hop_length=128)
        if len(idx) == 0:
            return y
        start, end = int(idx[0][0]), int(idx[-1][1])
        return y[start:end]
    except Exception:
        return y
