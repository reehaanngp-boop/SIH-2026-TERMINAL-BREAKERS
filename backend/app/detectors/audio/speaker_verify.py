"""Speaker verification for the Family Safe-Voice Registry.

Embedding strategy (2026-08-09): the original 52-D MFCC-statistics embedding
could not separate speakers — different voices scored cosine 0.64-1.0, so at
the old 0.42 threshold *every* voice matched (100% false-accept rate on real
recordings). It has been replaced by a proper neural speaker embedding:

* **ECAPA-TDNN** (SpeechBrain ``speechbrain/spkrec-ecapa-voxceleb``) — 192-D,
  state-of-the-art on VoxCeleb, free/open. Measured on this project's data it
  gives same-speaker cosine ~0.85 and different-speaker ~0.1-0.3, a clean gap
  around the 0.5 decision threshold.
* **MFCC-statistics fallback** (52-D) — kept so the registry still works on a
  bare/offline install where SpeechBrain or the model files are absent.

The model is downloaded once into ``data/models/ecapa-tdnn`` on first use
(internet needed); afterwards it loads entirely offline (SpeechBrain ``fetch``
skips files that already exist). Enrollments stored with the old 52-D
embedding are not comparable to 192-D probes, so they are filtered out and the
caller is told to re-enrol.
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
MFCC_DIM = 4 * MFCC_COUNT  # 52
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
    """Work around a Windows-only SpeechBrain bug in ``LazyModule``.

    When SpeechBrain is imported it registers lazy placeholders for its optional
    integrations — e.g. ``speechbrain.integrations.k2_fsa``, which needs the
    GPU-only ``k2`` package — in ``sys.modules``. Later, when ``librosa``'s lazy
    loader runs ``inspect.stack()``, Python's ``inspect.getmodule`` walks *every*
    module in ``sys.modules`` and calls ``hasattr(m, '__file__')``. On a
    ``LazyModule`` that attribute access force-loads the target module, so
    ``k2_fsa`` is imported and crashes with ``No module named 'k2'``.

    SpeechBrain guards against exactly this in ``LazyModule.ensure_module``, but
    only for POSIX paths (``filename.endswith("/inspect.py")``); on Windows the
    backslashed ``Lib\\inspect.py`` misses the guard.

    Giving every ``LazyModule`` a real ``__file__`` instance attribute makes
    ``hasattr`` short-circuit without triggering the lazy import, so the
    ``inspect`` walk is safe. Genuine attribute access (e.g. actually loading an
    optional integration) still goes through ``__getattr__`` and loads normally.
    """
    try:
        from speechbrain.utils.importutils import LazyModule
    except Exception:  # noqa: BLE001  (speechbrain not yet importable)
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

        # SpeechBrain is now imported and its lazy k2_fsa placeholder is in
        # sys.modules; neutralise it before anything (librosa) walks sys.modules.
        _neutralize_lazy_modules()

        savedir = settings.model_dir / "ecapa-tdnn"
        # First run downloads into savedir; later runs find the files already
        # present and load fully offline (SpeechBrain's fetch skips them).
        have_local = ecapa_model_present()
        classifier = EncoderClassifier.from_hparams(
            source=_ECAPA_SOURCE,
            savedir=str(savedir),
            run_opts={"device": "cpu"},
            local_strategy=LocalStrategy.COPY,  # copies, never symlinks (Windows-safe)
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

    Prefers the ECAPA-TDNN model (192-D); falls back to MFCC statistics (52-D)
    when the model cannot be loaded.
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
    except Exception:  # noqa: BLE001  (any torch/speechbrain hiccup -> fall back)
        return None
    norm = float(np.linalg.norm(emb))
    if norm == 0:
        return None
    return emb / norm


def _mfcc_embedding(audio: AudioData, *, n_mfcc: int = MFCC_COUNT) -> np.ndarray:
    """52-D MFCC-statistics embedding (fallback engine)."""
    import librosa

    y = audio.samples
    if y is None or len(y) < 1024:
        raise ValueError("audio clip too short to embed")
    # De-emphasise leading/trailing silence so the embedding focuses on speech.
    y = _trim_silence(y, audio.sr)
    if len(y) < 1024:
        y = audio.samples

    mfcc = librosa.feature.mfcc(y=y, sr=audio.sr, n_mfcc=n_mfcc, hop_length=256)
    delta = librosa.feature.delta(mfcc)

    stats = np.concatenate(
        [
            mfcc.mean(axis=1),
            mfcc.std(axis=1),
            delta.mean(axis=1),
            delta.std(axis=1),
        ]
    ).astype(np.float32)

    norm = float(np.linalg.norm(stats))
    if norm == 0:
        raise ValueError("degenerate audio (zero energy) cannot be embedded")
    return stats / norm


def cosine_similarity(a: np.ndarray | list[float], b: np.ndarray | list[float]) -> float:
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def best_match(probe: np.ndarray, enrollments: list[dict[str, Any]]) -> tuple[float | None, int | None]:
    """Return (best cosine similarity, index of best enrollment).

    Enrollments whose embedding dimension differs from the probe (e.g. created
    by the old 52-D MFCC engine) are skipped: their cosine would be meaningless.
    """
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


def _trim_silence(y: np.ndarray, sr: int, *, top_db: int = 30) -> np.ndarray:
    """Remove leading/trailing frames quieter than ``top_db`` relative to peak."""
    import librosa

    idx = librosa.effects.split(y, top_db=top_db, frame_length=256, hop_length=128)
    if len(idx) == 0:
        return y
    start, end = int(idx[0][0]), int(idx[-1][1])
    return y[start:end]
