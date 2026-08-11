"""Voice authenticity / anti-spoofing detection.

Two engines are combined:

* **AASIST** (optional): a pretrained graph-attention anti-spoofing model from
  the ASVspoof challenge. Weights live at ``data/models/aasist.pth`` and are
  loaded lazily. If torch or the checkpoint are absent this engine is skipped.
* **Statistical artifact analysis** (always available): hand-crafted acoustic
  features (pause regularity, pitch flatness, spectral flatness, bandwidth)
  that are typically abnormal in synthetic/cloned speech.

AASIST dominates the combined score when present (weight 0.75); the heuristics
provide a transparent fallback and corroboration. Both scores are always
exposed in ``metrics`` so results stay explainable.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from app.config import get_settings
from app.detectors.audio.audio_utils import AudioData
from app.detectors.base import BaseDetector

# AASIST reports a fixed 4 s input window; we analyse up to two windows (start
# and middle) and average, keeping CPU inference time bounded.
AASIST_WINDOW = 64600
MAX_WINDOWS = 2

# Weights for the heuristic feature risks (renormalised if some are missing).
# ``band`` was dropped: telephony audio is inherently narrow-band, so low
# spectral rolloff is *expected* for a real phone call — treating it as a
# synthetic cue caused systematic false positives. Gap/pitch carry the weight;
# flatness is a weak corroborator.
_HEUR_WEIGHTS = {"gap": 0.45, "pitch": 0.45, "flatness": 0.1}

SPEECH_RMS_THRESHOLD = 0.012  # ~ -38 dBFS, below this a frame counts as silent


class VoiceSpoofDetector(BaseDetector):
    name = "voice"
    description = "AI-generated / cloned voice detection (AASIST + artifact analysis)"

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.checkpoint_path = self.settings.model_dir / "aasist.pth"
        self._model: Any = None
        self._aasist_error: str | None = None

    # -- availability -------------------------------------------------------
    def available(self) -> bool:
        """Always available — heuristics need no model."""
        return True

    def _has_aasist(self) -> bool:
        if not self.settings.enable_aasist:
            return False
        return self.checkpoint_path.exists()

    def _ensure_aasist(self) -> Any:
        if self._model is not None:
            return self._model
        if not self._has_aasist():
            return None
        try:
            import torch  # noqa: F401  (guard import)

            from app.detectors.audio.aasist_model import load_aasist

            self._model = load_aasist(str(self.checkpoint_path), device="cpu")
            return self._model
        except Exception as exc:
            self._aasist_error = str(exc)
            self._model = None
            return None

    # -- main entry ---------------------------------------------------------
    def analyze(self, audio: AudioData) -> dict[str, Any]:
        x = audio.samples
        if x is None or len(x) < 2000:
            return self._result(
                "available",
                score=None,
                label="audio-too-short",
                detail="The clip is too short for voice analysis.",
                metrics={"length": 0 if x is None else len(x)},
            )

        speech_ratio = self._speech_ratio(x)
        metrics: dict[str, Any] = {"speech_ratio": round(float(speech_ratio), 3)}

        # No intelligible speech -> nothing to authenticate.
        if speech_ratio < 0.02:
            return self._result(
                "available",
                score=None,
                label="no-speech",
                detail="No clear speech detected in the clip; voice authenticity cannot be assessed.",
                metrics=metrics,
            )

        aasist_score = self._aasist_score(x)
        heur_score, heur_metrics = self._heuristics_score(x)
        metrics.update(heur_metrics)

        if aasist_score is None:
            metrics["aasist"] = None
            score = heur_score
            return self._result(
                "available",
                score=score,
                label="likely-ai-generated" if score is not None and score >= 0.5 else "likely-natural",
                detail=(
                    "No deepfake-voice model is loaded; verdict relies on statistical "
                    "artifact analysis only and should be treated as low-confidence."
                    + (f" ({self._aasist_error})" if self._aasist_error else "")
                ),
                metrics=metrics,
                engine="heuristics",
            )

        metrics["aasist"] = round(float(aasist_score), 3)
        score = 0.75 * aasist_score + 0.25 * heur_score
        return self._result(
            "available",
            score=score,
            label="likely-ai-generated" if score >= 0.5 else "likely-natural",
            detail=(
                "AASIST anti-spoofing model: %.0f%% synthetic-speech likelihood. "
                "Corroborated by artifact analysis (%.0f%%)." % (aasist_score * 100, heur_score * 100)
            ),
            metrics=metrics,
            engine="aasist",
        )

    # -- AASIST -------------------------------------------------------------
    def _aasist_score(self, x: np.ndarray) -> float | None:
        model = self._ensure_aasist()
        if model is None:
            return None
        try:
            import torch

            windows = self._make_windows(x)
            probs = []
            with torch.no_grad():
                for w in windows:
                    t = torch.from_numpy(w.astype(np.float32)).reshape(1, -1)
                    _, logits = model(t)
                    p = torch.softmax(logits, dim=1)
                    probs.append(float(p[0, 1]))  # index 1 == spoof
            return float(np.mean(probs))
        except Exception as exc:
            self._aasist_error = str(exc)
            return None

    def _make_windows(self, x: np.ndarray) -> list[np.ndarray]:
        n = len(x)
        windows = []
        if n <= AASIST_WINDOW:
            windows.append(np.pad(x, (0, AASIST_WINDOW - n)))
            return windows
        # Start window + middle window when long enough.
        windows.append(x[:AASIST_WINDOW])
        mid = (n - AASIST_WINDOW) // 2
        if mid >= AASIST_WINDOW // 2:
            windows.append(x[mid : mid + AASIST_WINDOW])
        return windows[:MAX_WINDOWS]

    # -- statistical heuristics ---------------------------------------------
    @staticmethod
    def _speech_ratio(x: np.ndarray, frame_len: int = 1024, hop: int = 512) -> float:
        n_frames = max(1, (len(x) - frame_len) // hop)
        if n_frames <= 1:
            return float(np.abs(x).mean() > SPEECH_RMS_THRESHOLD)
        rms = np.array(
            [
                np.sqrt(np.mean(x[i : i + frame_len] ** 2))
                for i in range(0, len(x) - frame_len, hop)
            ]
        )
        if len(rms) == 0:
            return 0.0
        return float(np.mean(rms > SPEECH_RMS_THRESHOLD))

    @staticmethod
    def _gap_durations(voiced: np.ndarray) -> np.ndarray:
        """Length (in frames) of silent runs between voiced runs."""
        padded = np.concatenate([[0], voiced.astype(int), [0]])
        diff = np.diff(padded)
        starts = np.where(diff == 1)[0]
        ends = np.where(diff == -1)[0]
        if len(starts) < 2 or len(starts) != len(ends):
            return np.array([])
        return (starts[1:] - ends[:-1]).astype(float)

    def _heuristics_score(self, x: np.ndarray) -> tuple[float | None, dict]:
        import librosa

        metrics: dict[str, Any] = {}
        risks: dict[str, float] = {}

        # 1. Pause-timing regularity — synthetic speech has unnaturally regular gaps.
        frame_len, hop = 1024, 512
        rms = librosa.feature.rms(y=x, frame_length=frame_len, hop_length=hop)[0]
        voiced = rms > SPEECH_RMS_THRESHOLD
        gaps = self._gap_durations(voiced)
        if len(gaps) >= 3:
            cv = float(np.std(gaps) / max(np.mean(gaps), 1e-6))
            metrics["gap_cv"] = round(cv, 3)
            # Only *very* regular pauses are suspect — TTS is far more periodic
            # than humans. cv < ~0.5 starts to count as anomalous.
            risks["gap"] = float(np.clip((0.5 - cv) / 0.35, 0, 1))
            metrics["gap_risk"] = round(risks["gap"], 3)

        # 2. Pitch flatness — cloned voices often have monotonous F0.
        try:
            f0 = librosa.yin(x, fmin=70, fmax=400, sr=16000)
            f0_v = f0[~np.isnan(f0)]
            if len(f0_v) > 20:
                spread = float(np.std(np.log2(f0_v / 110.0)))  # semitones around A2
                metrics["f0_std_semitones"] = round(spread, 3)
                # Flag only strongly monotone F0 (spread < ~1.6 semitones).
                # Monotone-but-human speakers are common on real calls.
                risks["pitch"] = float(np.clip((1.6 - spread) / 1.4, 0, 1))
                metrics["pitch_risk"] = round(risks["pitch"], 3)
        except Exception:
            pass

        # 3. Spectral flatness — noise-like spectra are common in TTS codecs.
        try:
            flat = float(librosa.feature.spectral_flatness(y=x, hop_length=hop).mean())
            metrics["spectral_flatness"] = round(flat, 3)
            # Require clearly noise-like spectra (flat > ~0.25); normal phone
            # codecs sit well below this.
            risks["flatness"] = float(np.clip((flat - 0.25) / 0.25, 0, 1))
            metrics["flatness_risk"] = round(risks["flatness"], 3)
        except Exception:
            pass

        # 4. Bandwidth (metrics only — NOT scored). Telephony audio is narrow-band
        # by design, so a low spectral rolloff is expected for real phone calls,
        # not a synthetic cue. We keep the number for explainability.
        try:
            roll = float(librosa.feature.spectral_rolloff(y=x, sr=16000, roll_percent=0.85).mean())
            metrics["rolloff85_hz"] = round(roll, 0)
        except Exception:
            pass

        if not risks:
            return None, metrics
        # Agreement gate: a single elevated feature is usually a codec or
        # speaker artifact (monotone delivery, noisy line), not synthetic
        # speech. Require at least two independent features to agree before
        # trusting the aggregate; otherwise report a near-baseline score.
        suspects = [r for r in risks.values() if r > 0.5]
        metrics["n_features"] = len(risks)
        metrics["agreement"] = len(suspects)
        if len(suspects) < 2:
            return 0.2, metrics
        total_w = sum(_HEUR_WEIGHTS[k] for k in risks)
        score = float(sum(risks[k] * _HEUR_WEIGHTS[k] for k in risks) / total_w)
        return score, metrics
