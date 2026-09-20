"""Wav2Vec2 fine-tuned deepfake / voice-cloning detection.

Two complementary transformers classifiers fine-tuned on the ASVspoof logical
access task (voice-conversion & synthetic-voice deepfakes):

* **Base** — ``DeepFake-Audio-Rangers/DeepfakeDetect_wav2vec2`` (wav2vec2-base).
  Strongest generalisation: reliably separates genuine human speech from
  synthetic/TTS audio (acc 0.979, AUC 0.998 on ASVspoof DF).
* **Large** — ``garystafford/wav2vec2-deepfake-voice-detector`` (wav2vec2-large).
  Trained specifically on cloned voices; catches modern zero-shot neural clones
  that evade the base model, at the cost of an occasional false positive on
  heavily processed natural speech.

Neither model alone is sufficient (base misses modern clones, large can flag a
real human voice), so a three-signal fusion is applied (Dhwani's XLS-R + AASIST
is passed in by ``voice_spoof`` as the trusted tiebreaker — it was trained on
Indian-context voice cloning and resolves modern-clone vs human ties that the
two Wav2Vec2 checkpoints dispute):

1. Base >= 0.5                     -> trust the base model & corroborators.
2. Base < 0.5, Dhwani >= 0.5       -> trust the specialist (modern clone caught).
3. Base < 0.5, large >= 0.5 only   -> disagreement: 0.30 *borderline* (verify),
                                       or consensus-real if Dhwani agrees real.
4. Everything < 0.5                -> consensus *real*.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
MAX_AUDIO_SECONDS = 15.0  # cap analysed window for fast, memory-safe inference

# (huggingface repo id, local cache dir under data/models)
PRIMARY_MODEL_ID = "DeepFake-Audio-Rangers/DeepfakeDetect_wav2vec2"
PRIMARY_LOCAL_DIR = "wav2vec2-deepfake"
SECONDARY_MODEL_ID = "garystafford/wav2vec2-deepfake-voice-detector"
SECONDARY_LOCAL_DIR = "wav2vec2-large-vcd"

_GLOBAL_LOCK = threading.Lock()
_GLOBAL_MODELS: dict[str, Any] = {}


class Wav2Vec2SpoofDetector:
    """Ensemble of fine-tuned Wav2Vec2 anti-spoofing classifiers (CPU)."""

    def __init__(self, settings: Any = None):
        self.settings = settings or get_settings()
        self.primary_dir = self.settings.model_dir / PRIMARY_LOCAL_DIR
        self.secondary_dir = self.settings.model_dir / SECONDARY_LOCAL_DIR
        self._load_errors: dict[str, str] = {}

    # -- Availability -------------------------------------------------------
    def installed(self) -> bool:
        """Cheap check used by /meta and fallback logic: transformers importable
        and the primary model folder is present (never loads weights)."""
        try:
            import transformers  # noqa: F401
        except Exception:
            return False
        return (self.primary_dir / "model.safetensors").exists()

    def available(self) -> bool:
        """True when the primary model can actually be loaded."""
        return self._load("primary") is not None

    def describe(self) -> dict[str, Any]:
        return {
            "available": self.installed(),
            "primary": self._describe_model("primary"),
            "secondary": self._describe_model("secondary"),
            "architecture": "Wav2Vec2 (base + large) fine-tuned on ASVspoof logical access",
            "error": self._load_errors or None,
        }

    def _describe_model(self, key: str) -> dict[str, Any]:
        local = self.primary_dir if key == "primary" else self.secondary_dir
        if (local / "model.safetensors").exists():
            return {"available": True, "path": str(local)}
        return {"available": False, "path": str(local), "error": self._load_errors.get(key)}

    # -- Model lifecycle ----------------------------------------------------
    @staticmethod
    def _cache_get(key: str):
        with _GLOBAL_LOCK:
            return _GLOBAL_MODELS.get(key)

    @staticmethod
    def _cache_set(key: str, value: Any) -> None:
        with _GLOBAL_LOCK:
            _GLOBAL_MODELS[key] = value

    def _load(self, key: str):
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        model_id = PRIMARY_MODEL_ID if key == "primary" else SECONDARY_MODEL_ID
        local_dir = self.primary_dir if key == "primary" else self.secondary_dir
        try:
            from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

            if (local_dir / "config.json").exists() and (local_dir / "preprocessor_config.json").exists():
                source = str(local_dir)
            else:
                source = model_id
                local_dir.mkdir(parents=True, exist_ok=True)

            extractor = AutoFeatureExtractor.from_pretrained(source)
            model = AutoModelForAudioClassification.from_pretrained(source)
            model.eval()

            # If we loaded from the remote repo, persist locally for offline use.
            if str(local_dir) != source and not (local_dir / "model.safetensors").exists():
                ext_dir = local_dir / "feature_extractor"
                extractor.save_pretrained(ext_dir)
                model.save_pretrained(local_dir)

            self._cache_set(key, (extractor, model))
            logger.info("Wav2Vec2 spoof model %s ready from %s", key, source)
            return self._cache_get(key)
        except Exception as exc:  # pragma: no cover - environment dependent
            self._load_errors[key] = str(exc)
            logger.warning("Wav2Vec2 spoof model %s unavailable: %s", key, exc)
            return None

    @staticmethod
    def _fake_index(model) -> int:
        """Robust mapping: find the label standing for fake/spoof."""
        id2label = getattr(model.config, "id2label", None)
        if id2label:
            for idx, label in id2label.items():
                if any(marker in label.lower() for marker in ("fake", "spoof", "synthetic")):
                    return int(idx)
        return 0  # conventional default: class 0 == spoof

    # -- Main entry ----------------------------------------------------------
    def analyze(
        self,
        samples: np.ndarray | None,
        sample_rate: int = SAMPLE_RATE,
        dhwani_probability: float | None = None,
    ) -> dict[str, Any]:
        """Compute the fused fake probability from base + corroborating engines.

        ``dhwani_probability`` is fused in as a third model-backed signal.
        """
        if samples is None or len(samples) < 1600:
            return {
                "available": False,
                "error": "Audio clip too short (< 1600 samples)",
                "fake_probability": 0.0,
                "verdict": "UNKNOWN",
            }

        y = self._prep(samples, sample_rate)
        if y is None:
            return {
                "available": False,
                "error": "No usable audio after resampling",
                "fake_probability": 0.0,
                "verdict": "UNKNOWN",
            }

        primary = self._load("primary")
        secondary = self._load("secondary")
        if primary is None:
            return {
                "available": False,
                "error": self._load_errors.get("primary") or "Wav2Vec2 models not loaded",
                "fake_probability": 0.0,
                "verdict": "UNAVAILABLE",
            }

        p_base = self._infer(primary, y)
        p_large = self._infer(secondary, y) if secondary is not None else None

        p_fused, mode = self._fuse(p_base, p_large, dhwani_probability)

        verdict = (
            "CRITICAL_SYNTHETIC"
            if p_fused >= 0.55
            else ("BORDERLINE_SYNTHETIC" if p_fused >= 0.35 else "AUTHENTIC_HUMAN")
        )

        return {
            "available": True,
            "fake_probability": round(float(p_fused), 4),
            "bonafide_probability": round(1.0 - float(p_fused), 4),
            "verdict": verdict,
            "fusion": mode,
            "primary": {
                "available": True,
                "model": PRIMARY_MODEL_ID,
                "fake_probability": round(float(p_base), 4),
            },
            "secondary": (
                {
                    "available": True,
                    "model": SECONDARY_MODEL_ID,
                    "fake_probability": round(float(p_large), 4),
                }
                if p_large is not None
                else {"available": False}
            ),
            "architecture": "Wav2Vec2-base + Wav2Vec2-large (ASVspoof fine-tuned)",
            "window_seconds": round(len(y) / SAMPLE_RATE, 2),
        }

    def analyze_chunk(self, samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> dict[str, Any]:
        """Low-latency path for live streams: base model only."""
        if samples is None or len(samples) < 1600:
            return {"available": False, "fake_probability": 0.0, "verdict": "UNKNOWN"}
        primary = self._load("primary")
        if primary is None:
            return {"available": False, "fake_probability": 0.0, "verdict": "UNAVAILABLE"}
        y = self._prep(samples, sample_rate)
        if y is None:
            return {"available": False, "fake_probability": 0.0, "verdict": "UNKNOWN"}
        p = float(self._infer(primary, y))
        return {
            "available": True,
            "fake_probability": round(p, 4),
            "verdict": "CRITICAL_SYNTHETIC" if p >= 0.5 else ("BORDERLINE_SYNTHETIC" if p >= 0.35 else "AUTHENTIC_HUMAN"),
        }

    # -- Helpers ---------------------------------------------------------------
    def _prep(self, samples: np.ndarray, sample_rate: int) -> np.ndarray | None:
        try:
            import librosa

            if samples.ndim > 1:
                samples = samples.mean(axis=1)
            y = samples.astype(np.float32)
            if sample_rate != SAMPLE_RATE:
                y = librosa.resample(y, orig_sr=sample_rate, target_sr=SAMPLE_RATE)
            max_len = int(MAX_AUDIO_SECONDS * SAMPLE_RATE)
            if len(y) > max_len:
                start = (len(y) - max_len) // 2
                y = y[start : start + max_len]
            peak = float(np.max(np.abs(y))) if len(y) else 0.0
            if peak < 1e-4:
                return None
            return y
        except Exception as exc:
            self._load_errors["prep"] = str(exc)
            return None

    def _infer(self, pair, y: np.ndarray) -> float:
        extractor, model = pair
        import torch

        with torch.no_grad():
            inputs = extractor(y, sampling_rate=SAMPLE_RATE, return_tensors="pt")
            logits = model(**inputs).logits
        probs = torch.softmax(logits, dim=1)[0]
        return float(probs[self._fake_index(model)])

    @staticmethod
    def _fuse(p_base: float, p_large: float | None, p_dhwani: float | None) -> tuple[float, str]:
        """Three-signal, disagreement-aware fusion of model-backed signals.

        Priority: base (best generalisation) -> Dhwani (specialised on Indian
        context voice cloning, resolves modern-clone ties) -> large (catches
        zero-shot clones but can false-positive matured natural speech).
        """
        others = [p for p in (p_large, p_dhwani) if p is not None]
        suspects = [p for p in others if p >= 0.5]

        if p_base >= 0.5:
            # Base already sees synthetic phonation; corroboration can only raise.
            return max([p_base] + suspects), "primary-fake"

        if p_dhwani is not None and p_dhwani >= 0.5:
            # Base read "real" but the specialised multilingual model firmly
            # disagrees: trust the specialist (it catches modern neural clones).
            return p_dhwani, "dhwani-fake"

        if p_large is not None and p_large >= 0.5:
            if p_dhwani is not None and p_dhwani < 0.5:
                # Base and Dhwani both read real; the large model is the outlier
                # (known false-positive behaviour on processed human speech).
                return min([p_base, p_dhwani, p_large]), "consensus-real"
            return 0.30, "disagreement"

        if others:
            # Every signal agrees on genuine human speech.
            return min([p_base] + others), "consensus-real"
        return p_base, "primary-only"