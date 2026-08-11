"""Speech-to-text via Whisper (faster-whisper, CPU-friendly CTranslate2)."""

from __future__ import annotations

from typing import Any

import numpy as np

from app.config import get_settings
from app.detectors.base import BaseDetector

# "small" gives good accuracy on Indian languages; "base" is faster and lighter.
_SUPPORTED_SIZES = ("tiny", "base", "small", "medium", "large-v3")


class AsrDetector(BaseDetector):
    """Transcribe call audio/video in its original language.

    The model is loaded lazily on first use so that importing the app never
    downloads anything. Transcription applies a VAD filter so silence is not
    transcribed, and returns per-segment confidence for explainability.
    """

    name = "asr"
    description = "Speech-to-text via OpenAI Whisper (faster-whisper)"

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self._model: Any = None
        self._load_error: str | None = None
        self._available: bool | None = None  # cached availability (no network)

    # -- lifecycle ----------------------------------------------------------
    def available(self) -> bool:
        """Cheap availability check — never triggers a model download."""
        if self._model is not None:
            return True
        if self._available is not None:
            return self._available
        self._available = self._ensure_model(local_only=True) is not None
        return self._available

    def _ensure_model(self, local_only: bool = False) -> Any:
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel

            size = self.settings.whisper_model_size
            if size not in _SUPPORTED_SIZES:
                size = "small"
            self._model = WhisperModel(
                size,
                device=self.settings.whisper_device,
                compute_type=self.settings.whisper_compute_type,
                local_files_only=local_only,
            )
            return self._model
        except Exception as exc:  # pragma: no cover - depends on environment
            self._load_error = str(exc)
            return None

    # -- analysis -----------------------------------------------------------
    def transcribe(self, wav_path: str, language: str | None = None) -> dict[str, Any]:
        model = self._ensure_model()
        if model is None:
            return self._result(
                "unavailable",
                detail=f"Whisper model could not be loaded: {self._load_error}",
            )
        try:
            segments, info = model.transcribe(
                str(wav_path),
                language=language or self.settings.whisper_language,
                vad_filter=True,
                beam_size=5,
                without_timestamps=False,
            )
            segs = list(segments)
            text = " ".join(s.text.strip() for s in segs).strip()
            avg_logprob = (
                float(np.mean([s.avg_logprob for s in segs])) if segs else None
            )
            return self._result(
                score=None,
                label="transcribed" if text else "no-speech",
                detail=f"Language {info.language} ({info.language_probability:.2f}), "
                f"{len(segs)} segment(s)",
                metrics={
                    "segments": len(segs),
                    "avg_logprob": avg_logprob,
                    "language": info.language,
                    "language_probability": float(info.language_probability),
                    "audio_duration": float(info.duration),
                },
                transcript=text,
                language=info.language,
            )
        except Exception as exc:
            return self._result("error", detail=f"Transcription failed: {exc}")
