"""Unit tests for the risk aggregation engine (pure, no models)."""

from __future__ import annotations

from app.core.risk_engine import assess


def _text_signal(category: str, conf: float) -> dict:
    return {
        "name": "text",
        "status": "available",
        "available": True,
        "score": conf,
        "label": category,
        "detail": f"top category {category}",
        "metrics": {"category": category, "top_probability": conf, "confident": True},
    }


def _voice_signal(score: float, engine: str = "aasist") -> dict:
    return {
        "name": "voice",
        "status": "available",
        "available": True,
        "score": score,
        "label": "spoof",
        "detail": "",
        "metrics": {},
        "engine": engine,
    }


def test_benign_text_scores_low():
    res = assess(
        media_type="text",
        scam=_text_signal("benign", 0.9),
    )
    assert res["risk"]["level"] == "low"
    assert res["risk"]["score"] < 40
    assert any(f["id"] == "text-benign" for f in res["red_flags"])


def test_digital_arrest_script_scores_high():
    res = assess(
        media_type="text",
        scam=_text_signal("digital_arrest", 0.95),
    )
    assert res["risk"]["level"] == "high"
    assert res["risk"]["score"] >= 65
    ids = [f["id"] for f in res["red_flags"]]
    assert "scam-arrest" in ids
    # High-risk next steps include reporting channels.
    step_ids = [s["id"] for s in res["next_steps"]]
    assert "report-1930" in step_ids and "no-arrest-fee" in step_ids


def test_low_confidence_scam_is_not_confident():
    # Below the 0.35 floor the classifier reports "uncertain", so no flag.
    res = assess(media_type="text", scam=_text_signal("benign", 0.2))
    assert "text-benign" in [f["id"] for f in res["red_flags"]]


def test_voice_spoof_escalates_score():
    benign = assess(media_type="audio", scam=_text_signal("benign", 0.9))
    spoofed = assess(
        media_type="audio",
        scam=_text_signal("benign", 0.9),
        voice=_voice_signal(0.85),
    )
    assert spoofed["risk"]["score"] > benign["risk"]["score"]
    assert any(f["id"] == "voice-ai-likely" for f in spoofed["red_flags"])


def test_voice_plus_scam_two_criticals_escalates():
    res = assess(
        media_type="audio",
        scam=_text_signal("otp_phishing", 0.9),
        voice=_voice_signal(0.9),
    )
    assert res["risk"]["level"] == "high"
    # Both critical flags present -> escalation multiplier applied.
    assert any(f["id"] == "voice-ai-likely" for f in res["red_flags"])
    assert any(f["id"] == "scam-otp" for f in res["red_flags"])


def test_heuristics_only_voice_is_not_critical():
    """Without the AASIST model, a high heuristic score must not emit an
    AI-clone critical flag nor drive the verdict high on its own."""
    res = assess(
        media_type="audio",
        scam=_text_signal("benign", 0.9),
        voice=_voice_signal(0.9, engine="heuristics"),
    )
    ids = [f["id"] for f in res["red_flags"]]
    assert "voice-ai-likely" not in ids
    assert "voice-cannot-check" in ids
    assert res["risk"]["level"] != "high"


def test_no_signals_returns_low():
    res = assess(media_type="text")
    assert res["risk"]["level"] == "low"
    assert res["risk"]["score"] == 5.0


def test_video_signal_no_longer_scores():
    """Frame-level video heuristics are advisory only: they must not move the
    risk verdict (steady webcam/video calls used to false-positive)."""
    video = {
        "name": "video",
        "status": "available",
        "available": True,
        "score": 0.9,
        "label": "likely-edited",
        "detail": "",
        "metrics": {},
    }
    res = assess(media_type="video", video=video)
    assert res["risk"]["level"] == "low"
    assert res["risk"]["score"] == 5.0
    assert not any(f["id"] in ("video-warning", "video-edited") for f in res["red_flags"])


def test_missing_detectors_do_not_break():
    """Detectors that report unavailable contribute nothing."""
    res = assess(
        media_type="audio",
        asr={"name": "asr", "status": "unavailable", "available": False, "score": None, "label": None, "detail": None, "metrics": {}},
    )
    assert res["risk"]["score"] == 5.0
