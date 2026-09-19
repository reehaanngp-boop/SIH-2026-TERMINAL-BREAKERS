"""Video deepfake analysis (frame-level, CPU-friendly).

The analyser pairs two independent signals:

* **MesoNet (MesoInception-4)** — a tiny CNN (28k params, Apache-2.0) trained
  on FaceForensics-style data to classify a *face crop* as real (0) or
  manipulated (1). Weights live in ``data/models/mesonet/mesoInception_DF.pth``
  (converted from the official Keras ``MesoInception_DF.h5``). It is loaded
  lazily and scored per sampled frame; when it is missing the detector falls
  back to heuristics alone (see ``mesonet_available()``).
* **Heuristics** — face presence via OpenCV's bundled Haar cascade (no model
  download), plus *temporal flicker* (variance of frame-to-frame difference in
  the face region; deepfakes tend to shimmer around mouth/edges).

Both produce a suspicion score in [0, 1]; the model-backed score takes priority
when present. The ``score``/``label`` contract is stable: the risk engine caps
the video contribution at 0.4 and emits at most a ``video-warning``, so a
model-backed verdict can never push a benign video call to "high".
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.config import get_settings
from app.detectors.base import BaseDetector

_FACE_MIN_FRACTION = 0.05  # smallest face, as fraction of frame dimension
_MESO_SIZE = 256  # MesoNet input resolution (square RGB crop)


class VideoDeepfakeDetector(BaseDetector):
    name = "video"
    description = "Deepfake manipulation cues via frame-level analysis (OpenCV + MesoNet)"

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self._cascade: Any = None
        self._cascade_error: str | None = None
        self._mesonet: Any = None
        self._mesonet_error: str | None = None

    def _ensure_cascade(self) -> Any:
        if self._cascade is not None or self._cascade_error:
            return self._cascade
        try:
            # OpenCV 5.0 removed CascadeClassifier from the top-level namespace.
            # Try the legacy class path; fall back to None on AttributeError.
            cascade_cls = getattr(cv2, "CascadeClassifier", None)
            if cascade_cls is None:
                self._cascade_error = "CascadeClassifier removed in OpenCV 5 (heuristics-only mode)"
                return None
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self._cascade = cascade_cls(cascade_path)
            if self._cascade.empty():
                self._cascade_error = "cascade file could not be loaded"
                self._cascade = None
        except Exception as exc:
            self._cascade_error = str(exc)
        return self._cascade

    def _mesonet_path(self) -> Path:
        return self.settings.model_dir / "mesonet" / "mesoInception_DF.pth"

    def _ensure_mesonet(self) -> Any:
        """Lazy, cached MesoNet loader. Returns None (heuristics-only) on any failure."""
        if self._mesonet is not None or self._mesonet_error:
            return self._mesonet
        try:
            if importlib.util.find_spec("torch") is None:
                self._mesonet_error = "torch not installed"
                return None
            from app.detectors.video.mesonet_model import load_mesonet

            path = self._mesonet_path()
            if not path.exists():
                self._mesonet_error = f"weights missing at {path.name}"
                return None
            model = load_mesonet(str(path))
            if model is None:
                self._mesonet_error = "weights could not be loaded"
            self._mesonet = model
        except Exception as exc:  # noqa: BLE001
            self._mesonet_error = str(exc)
        return self._mesonet

    def mesonet_available(self) -> bool:
        return self._ensure_mesonet() is not None

    def available(self) -> bool:
        """Always available — temporal heuristics need no cascade."""
        return True

    def describe(self) -> dict[str, Any]:
        d = super().describe()
        d["engine"] = "mesonet" if self.mesonet_available() else "heuristics"
        d["mesonet_available"] = self.mesonet_available()
        if not self.mesonet_available() and self._mesonet_error:
            d["mesonet_error"] = self._mesonet_error
        return d

    @staticmethod
    def _prepare_face_crop(bgr: np.ndarray, size: int = _MESO_SIZE) -> np.ndarray:
        """Pad a BGR face crop to a square, then resize to 256x256 RGB in [0,1]."""
        h, w = bgr.shape[:2]
        side = max(h, w)
        padded = np.zeros((side, side, 3), dtype=np.uint8)
        y0, x0 = (side - h) // 2, (side - w) // 2
        padded[y0 : y0 + h, x0 : x0 + w] = bgr
        rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        rgb = cv2.resize(rgb, (size, size), interpolation=cv2.INTER_AREA)
        return rgb.astype(np.float32) / 255.0

    def analyze(self, video_path: str) -> dict[str, Any]:
        # Ensure cascade is attempted (best-effort face detection)
        cascade = self._ensure_cascade()
        mesonet = self._ensure_mesonet()
        meso_engine = "mesonet" if mesonet is not None else "heuristics"
        score_crop = None
        if mesonet is not None:
            from app.detectors.video.mesonet_model import score_crop  # lazy torch import

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return self._result("error", detail="Could not open video file", engine=meso_engine)

        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration = total / fps if fps > 0 else 0.0

        interval = max(1, int(self.settings.video_frame_interval))
        max_frames = self.settings.video_max_frames

        frame_metrics: list[dict[str, float]] = []
        duplicates = 0
        prev_crop: np.ndarray | None = None
        frame_no = 0
        read = 0

        try:
            while read < total:
                if frame_no % interval != 0:
                    if not cap.grab():
                        break
                    frame_no += 1
                    continue

                ok, frame = cap.read()
                if not ok:
                    break
                frame_no += 1
                read += 1
                if len(frame_metrics) >= max_frames:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                h, w = gray.shape

                # Face detection — skipped if cascade unavailable (OpenCV 5+).
                if cascade is not None:
                    faces = cascade.detectMultiScale(
                        gray,
                        scaleFactor=1.1,
                        minNeighbors=5,
                        minSize=(
                            max(20, int(w * _FACE_MIN_FRACTION)),
                            max(20, int(h * _FACE_MIN_FRACTION)),
                        ),
                    )
                else:
                    # No face detector: treat centre crop as the ROI.
                    cw, ch = w // 3, h // 3
                    x0, y0 = cw, ch
                    faces = [(x0, y0, cw, ch)]

                if len(faces) == 0:
                    continue

                # Analyse the largest face region.
                fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                face = gray[fy : fy + fh, fx : fx + fw]
                if face.size == 0:
                    continue
                crop = cv2.resize(face, (64, 64))

                sharpness = float(cv2.Laplacian(crop, cv2.CV_64F).var())
                m = {"sharpness": sharpness}

                if score_crop is not None:
                    face_color = frame[fy : fy + fh, fx : fx + fw]
                    if face_color.size:
                        meso_crop = self._prepare_face_crop(face_color)
                        m["meso_score"] = score_crop(mesonet, meso_crop)

                if prev_crop is not None:
                    diff = float(np.mean(np.abs(crop.astype(np.float32) - prev_crop.astype(np.float32))) / 255.0)
                    m["frame_diff"] = diff
                    if diff < 0.015:
                        duplicates += 1

                frame_metrics.append(m)
                prev_crop = crop
        finally:
            cap.release()

        n = len(frame_metrics)
        if n == 0:
            return self._result(
                "available",
                score=None,
                label="no-face",
                detail="No face was detected in the analysed frames, so deepfake cues could not be computed.",
                metrics={"frames_analysed": read, "frames_with_face": 0,
                         "duration_seconds": round(duration, 1), "video_engine": meso_engine},
                engine=meso_engine,
            )

        sharpness = np.array([m["sharpness"] for m in frame_metrics])
        diffs = np.array([m.get("frame_diff", 0.0) for m in frame_metrics if "frame_diff" in m])

        metrics: dict[str, Any] = {
            "frames_analysed": read,
            "frames_with_face": n,
            "duration_seconds": round(duration, 1),
            "mean_sharpness": round(float(sharpness.mean()), 1),
            "sharpness_cv": round(float(sharpness.std() / (sharpness.mean() + 1e-6)), 3),
            "duplicate_frames": duplicates,
            "duplicate_ratio": round(float(duplicates / n), 3),
            "video_engine": meso_engine,
        }
        if len(diffs):
            metrics["mean_frame_diff"] = round(float(diffs.mean()), 4)
            metrics["frame_diff_cv"] = round(float(diffs.std() / (diffs.mean() + 0.01)), 3)
            metrics["frame_diff_range"] = round(float(diffs.max() - diffs.min()), 4)

        # MesoNet per-frame scores (only when the converted weights are present).
        meso_scores = np.array([m["meso_score"] for m in frame_metrics if "meso_score" in m])
        if len(meso_scores):
            metrics["meso_mean"] = round(float(meso_scores.mean()), 4)
            metrics["meso_max"] = round(float(meso_scores.max()), 4)
            metrics["meso_frames_high"] = round(float((meso_scores >= 0.5).mean()), 3)

        # Heuristic scoring. Only *erratic* temporal change in the face region
        # (flicker) is treated as a suspicious cue. Duplication and
        # sharpness-stability are reported for explainability but deliberately
        # NOT scored: near-identical consecutive crops and steady sharpness are
        # the NORMAL look of a webcam/video call where a person sits still —
        # scoring them flagged benign calls as "edited".
        flicker = (
            float(np.clip((metrics["frame_diff_cv"] - 0.6) / 1.5, 0, 1))
            if "frame_diff_cv" in metrics
            else None
        )
        dup = float(np.clip(metrics["duplicate_ratio"] / 0.5, 0, 1))
        sharp = float(np.clip((metrics["sharpness_cv"] - 0.15) / 0.6, 0, 1)) if metrics["sharpness_cv"] > 0 else None

        score = float(flicker) if flicker is not None else 0.0
        if len(meso_scores):
            # Weighted blend of per-frame confidence: the average (typical frame),
            # the max (worst/strongest manipulated frame) and the fraction of
            # frames above the 0.5 decision threshold. Never below the flicker cue.
            meso_score = float(np.clip(
                0.5 * meso_scores.mean() + 0.3 * meso_scores.max() + 0.2 * (meso_scores >= 0.5).mean(), 0, 1))
            metrics["meso_score"] = round(meso_score, 3)
            score = max(score, meso_score)

        metrics.update({"flicker_risk": round(flicker, 3) if flicker is not None else None,
                        "dup_risk": round(dup, 3),
                        "sharpness_risk": round(sharp, 3) if sharp is not None else None})

        label = "likely-edited" if score >= 0.5 else "no-strong-manipulation-cues"
        engine_note = (
            f"Scored per-face-crop with MesoNet (mean {metrics['meso_mean']}, "
            f"max {metrics['meso_max']}). "
            if len(meso_scores)
            else "No MesoNet weights available — heuristic cues only. "
        )
        detail = (
            f"{engine_note}Analysed {n} frames containing faces across {read} sampled frames "
            f"({duration:.0f}s clip). Duplicate-ratio {metrics['duplicate_ratio']}, "
            f"flicker {metrics.get('frame_diff_cv')}, sharpness-CV {metrics['sharpness_cv']}."
        )
        return self._result("available", score=score, label=label, detail=detail,
                            metrics=metrics, engine=meso_engine)
