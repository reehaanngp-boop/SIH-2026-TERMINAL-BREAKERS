"""Detector registry and lazy initialisation.

Detectors are built once and cached. Heavy models (Whisper, AASIST, the scam
classifier) load lazily on first use, so the process starts quickly and runs
fine even when optional models are not present — the risk engine degrades
gracefully in that case.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.config import get_settings
from app.detectors.audio.asr import AsrDetector
from app.detectors.audio.voice_spoof import VoiceSpoofDetector
from app.detectors.text.scam_classifier import ScamClassifierDetector
from app.detectors.video.deepfake import VideoDeepfakeDetector


class DetectorManager:
    """Holds all detectors and exposes unified availability metadata."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.asr = AsrDetector(self.settings)
        self.voice = VoiceSpoofDetector(self.settings)
        self.video = VideoDeepfakeDetector(self.settings)
        self.scam = ScamClassifierDetector(self.settings)

    @property
    def detectors(self) -> dict[str, Any]:
        return {
            "asr": self.asr,
            "voice": self.voice,
            "video": self.video,
            "text": self.scam,
        }

    def describe(self) -> dict[str, dict]:
        """Availability + description for every detector (for /meta endpoint)."""
        from app.detectors.audio.speaker_verify import (
            ecapa_ready,
            embedding_engine,
        )

        out = {}
        for name, det in self.detectors.items():
            info = det.describe()
            if name == "voice":
                info["aasist_available"] = self.voice._has_aasist()
                info["engine"] = "aasist" if info["aasist_available"] else "heuristics"
            if name == "text":
                info["model_path"] = str(self.scam.model_path)
            out[name] = info
        # Speaker-verification engine used by the Safe-Voice Registry.
        out["speaker"] = {
            "name": "speaker",
            "description": "Speaker verification for the Family Safe-Voice Registry (ECAPA-TDNN embeddings)",
            "available": True,
            "engine": embedding_engine(),
            "ecapa_ready": ecapa_ready(),
            "threshold": self.settings.verify_similarity_threshold,
        }
        # AI second-opinion layer (OpenRouter LLM). Imported lazily so /meta
        # still works on a bare install. `available` reflects config only —
        # it does not force a network call.
        from app.services.llm_analysis import llm_model, llm_ready

        out["ai"] = {
            "name": "ai",
            "description": "LLM second opinion over the transcript (OpenRouter)",
            "available": llm_ready()[0],
            "engine": llm_model(),
        }
        return out


@lru_cache
def get_detectors() -> DetectorManager:
    return DetectorManager(get_settings())
