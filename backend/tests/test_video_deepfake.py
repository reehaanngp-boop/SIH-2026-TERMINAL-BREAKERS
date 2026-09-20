"""Tests for the video deepfake detector (MesoNet + heuristic fallback).

The weight-conversion path is validated independently by
``scripts/convert_mesonet_weights.py`` (numpy reference vs torch); these tests
cover the detector's *integration* behaviour: graceful fallback when the model
is missing, correct crop preprocessing and score emission when it is present,
and the risk-engine invariant that a model-backed video verdict can never push
the overall risk to high or emit anything stronger than a warning.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.core import risk_engine
from app.detectors.video.deepfake import VideoDeepfakeDetector


def _fresh_detector() -> VideoDeepfakeDetector:
    det = VideoDeepfakeDetector()
    det._mesonet = None
    det._mesonet_error = None
    return det


def _mesonet_present() -> bool:
    return _fresh_detector().mesonet_available()


def test_missing_weights_falls_back_to_heuristics(tmp_path):
    det = _fresh_detector()
    # Point at a weights file that does not exist.
    det._mesonet_path = lambda: tmp_path / "does_not_exist.pth"  # type: ignore[method-assign]
    assert det._ensure_mesonet() is None
    assert det.mesonet_available() is False
    d = det.describe()
    assert d["engine"] == "heuristics"
    assert d["mesonet_available"] is False
    assert "mesonet_error" in d


def test_mesonet_loads_and_scores_crop():
    if not _mesonet_present():
        pytest.skip("MesoNet weights not present on this machine")
    det = _fresh_detector()
    model = det._ensure_mesonet()
    assert model is not None

    # Non-square RGB patch -> 256x256x3 float crop in [0, 1].
    rng = np.random.default_rng(0)
    patch = rng.integers(0, 255, size=(100, 80, 3)).astype(np.uint8)
    crop = det._prepare_face_crop(patch)
    assert crop.shape == (256, 256, 3)
    assert crop.dtype == np.float32
    assert crop.min() >= 0.0 and crop.max() <= 1.0

    from app.detectors.video.mesonet_model import score_crop

    score = score_crop(model, crop)
    assert 0.0 <= score <= 1.0


def test_describe_reports_mesonet_when_present():
    if not _mesonet_present():
        pytest.skip("MesoNet weights not present on this machine")
    det = _fresh_detector()
    d = det.describe()
    assert d["engine"] == "mesonet"
    assert d["mesonet_available"] is True


def test_video_risk_no_longer_scores():
    """Frame-level video heuristics are advisory only: a maximum model-backed
    video score must not move the overall risk verdict at all."""
    video = {
        "status": "available",
        "score": 1.0,
        "engine": "mesonet",
        "metrics": {"meso_score": 1.0},
    }
    out = risk_engine.assess(media_type="video", video=video)
    assert out["risk"]["level"] == "low"
    assert out["risk"]["score"] == 5.0
    assert out["red_flags"] == []
