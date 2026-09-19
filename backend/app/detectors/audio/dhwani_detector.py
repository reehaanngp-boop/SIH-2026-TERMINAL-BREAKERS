"""Dhwani: Multilingual Deepfake Audio & Voice Cloning Detector.

Hybrid Architecture:
- Front-End: Facebook's Wav2Vec2 XLS-R (300M) self-supervised speech representation
- Back-End: AASIST (Spectro-Temporal Graph Attention Network)
- Export: ONNX Runtime optimized (CPU inference sub-45ms)
- Languages: English, Hindi, Tamil, Telugu, Malayalam (Mozilla Common Voice + IndicSynth)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)

DHWANI_HF_REPO = "ayush2635/Dhwani-Multilingual-Deepfake-Audio-Detection-Model"
DHWANI_HF_FILENAME = "best_model.onnx"
WINDOW_SAMPLES = 48000  # 3.0 seconds at 16kHz
SAMPLE_RATE = 16000


class DhwaniDetector:
    """Multilingual Voice Cloning & Deepfake Detection Engine via ONNX Runtime."""

    def __init__(self, model_path: Path | str | None = None):
        settings = get_settings()
        if model_path:
            self.model_path = Path(model_path)
        elif settings.dhwani_model_path:
            self.model_path = Path(settings.dhwani_model_path)
        else:
            # Check either dhwani_multilingual.onnx or best_model.onnx in model_dir
            cand1 = settings.model_dir / "dhwani_multilingual.onnx"
            cand2 = settings.model_dir / "best_model.onnx"
            self.model_path = cand1 if cand1.exists() else (cand2 if cand2.exists() else cand1)

        self._session: Any = None
        self._input_name: str | None = None
        self._load_error: str | None = None

    def available(self) -> bool:
        """Return True if ONNX runtime is installed and model file exists."""
        return self.model_path.exists() and self._ensure_session() is not None

    def _ensure_session(self) -> Any:
        if self._session is not None:
            return self._session

        if not self.model_path.exists():
            return None

        try:
            import onnxruntime as ort

            # Set thread options for efficient multi-core CPU inference
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 2
            opts.inter_op_num_threads = 1
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            self._session = ort.InferenceSession(str(self.model_path), sess_options=opts, providers=["CPUExecutionProvider"])
            self._input_name = self._session.get_inputs()[0].name
            logger.info("Dhwani Multilingual Deepfake ONNX model loaded successfully from %s", self.model_path)
            return self._session
        except Exception as exc:
            self._load_error = str(exc)
            logger.warning("Failed to load Dhwani ONNX model from %s: %s", self.model_path, exc)
            self._session = None
            return None

    def analyze(self, samples: np.ndarray, sample_rate: int = 16000) -> dict[str, Any]:
        """Analyze speech samples and compute deepfake / synthetic cloning probability.

        Args:
            samples: 1D numpy array of audio samples.
            sample_rate: sampling frequency (resampled/verified at 16kHz).

        Returns:
            dict with fake_probability, bonafide_probability, verdict, and metadata.
        """
        if samples is None or len(samples) < 2000:
            return {
                "available": False,
                "error": "Audio clip too short (< 2000 samples)",
                "fake_probability": 0.0,
                "verdict": "UNKNOWN",
            }

        session = self._ensure_session()
        if session is None:
            return {
                "available": False,
                "error": self._load_error or "Dhwani ONNX model not loaded or weights missing",
                "fake_probability": 0.0,
                "verdict": "UNAVAILABLE",
            }

        import librosa

        # Ensure audio is 16kHz mono float32 for Wav2Vec2-XLS-R
        if sample_rate != SAMPLE_RATE and len(samples) > 0:
            y = librosa.resample(samples.astype(np.float32), orig_sr=sample_rate, target_sr=SAMPLE_RATE)
        else:
            y = samples.astype(np.float32)

        total_len = len(y)
        window_probs: list[float] = []

        if total_len <= WINDOW_SAMPLES:
            # Normalize active speech first, then pad
            var = float(np.var(y))
            if var > 1e-7:
                y_norm = (y - np.mean(y)) / np.sqrt(var + 1e-5)
            else:
                y_norm = y
            pad_len = WINDOW_SAMPLES - total_len
            w = np.pad(y_norm, (0, pad_len), mode="constant")
            input_data = w.astype(np.float32).reshape(1, WINDOW_SAMPLES)
            logits = session.run(None, {self._input_name: input_data})[0]
            shifted = logits - np.max(logits, axis=1, keepdims=True)
            exp_l = np.exp(shifted)
            probs = exp_l / np.sum(exp_l, axis=1, keepdims=True)
            window_probs.append(float(probs[0][1]))
        else:
            # Multi-window evaluation with 50% overlap
            step = WINDOW_SAMPLES // 2
            offsets = list(range(0, total_len - WINDOW_SAMPLES + 1, step))
            if len(offsets) > 6:
                indices = np.linspace(0, len(offsets) - 1, 6, dtype=int)
                offsets = [offsets[i] for i in indices]

            for off in offsets:
                w = y[off : off + WINDOW_SAMPLES]
                prob = self._infer_single_window(w)
                window_probs.append(prob)

        if not window_probs:
            return {
                "available": True,
                "fake_probability": 0.0,
                "bonafide_probability": 1.0,
                "verdict": "BONAFIDE",
            }

        mean_prob = float(np.mean(window_probs))
        max_prob = float(np.max(window_probs))
        combined_prob = float(0.60 * max_prob + 0.40 * mean_prob)

        verdict = (
            "CRITICAL_SYNTHETIC"
            if combined_prob >= 0.70
            else ("BORDERLINE_SYNTHETIC" if combined_prob >= 0.40 else "AUTHENTIC_HUMAN")
        )

        return {
            "available": True,
            "fake_probability": round(combined_prob, 4),
            "bonafide_probability": round(1.0 - combined_prob, 4),
            "peak_window_fake_probability": round(max_prob, 4),
            "mean_window_fake_probability": round(mean_prob, 4),
            "windows_evaluated": len(window_probs),
            "verdict": verdict,
            "architecture": "Wav2Vec2-XLS-R-300M + AASIST (ONNX)",
            "languages_supported": ["English", "Hindi", "Tamil", "Telugu", "Malayalam"],
        }

    def _infer_single_window(self, w: np.ndarray) -> float:
        """Run single 48,000-sample window through the ONNX inference session."""
        var = float(np.var(w))
        if var > 1e-7:
            norm_w = (w - np.mean(w)) / np.sqrt(var + 1e-5)
        else:
            norm_w = w
        input_data = norm_w.astype(np.float32).reshape(1, WINDOW_SAMPLES)

        logits = self._session.run(None, {self._input_name: input_data})[0]
        # Softmax with numerical stability
        shifted = logits - np.max(logits, axis=1, keepdims=True)
        exp_logits = np.exp(shifted)
        probs = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)
        return float(probs[0][1])  # Index 1 = Fake / Spoof


def download_dhwani_model(dest_path: Path | None = None) -> Path:
    """Download the Dhwani ONNX model from Hugging Face into data/models/."""
    from huggingface_hub import hf_hub_download

    settings = get_settings()
    target_path = dest_path or (settings.model_dir / "dhwani_multilingual.onnx")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if target_path.exists() and target_path.stat().st_size > 1_000_000_000:
        logger.info("Dhwani model already exists at %s", target_path)
        return target_path

    logger.info("Downloading Dhwani Multilingual Deepfake model from %s...", DHWANI_HF_REPO)
    downloaded = hf_hub_download(
        repo_id=DHWANI_HF_REPO,
        filename=DHWANI_HF_FILENAME,
        local_dir=str(target_path.parent),
    )
    downloaded_path = Path(downloaded)
    if downloaded_path != target_path:
        import shutil
        shutil.move(str(downloaded_path), str(target_path))

    logger.info("Dhwani model successfully saved to %s", target_path)
    return target_path
