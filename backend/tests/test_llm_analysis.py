"""Unit tests for the OpenRouter LLM second-opinion layer.

All network calls are monkeypatched — no API key or internet needed. The
module reads ``settings`` as a module-level reference, so tests swap it with a
fresh ``Settings`` instance (patching ``app.services.llm_analysis.settings``).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from app.config import Settings
from app.core.risk_engine import assess
from app.services.llm_analysis import (
    _norm_verdict,
    _parse_verdict,
    _post_json,
    analyze_transcript_ai,
)
from app.services.pipeline import AnalysisPipeline


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


def _ai_verdict(*, is_scam: bool, confidence: float, category: str | None = None) -> dict:
    return {
        "status": "ok",
        "model": "test-model",
        "verdict": {
            "is_scam": is_scam,
            "confidence": confidence,
            "scam_category": category,
            "key_indicators": ["test indicator"],
            "explanation": {"en": "english", "hi": "हिंदी"},
        },
    }


# ---------------------------------------------------------------------------
# analyze_transcript_ai — availability + parsing
# ---------------------------------------------------------------------------

def test_disabled_returns_none(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis.settings",
        Settings(enable_llm_analysis=False, openrouter_api_key=None),
    )
    assert (
        analyze_transcript_ai(
            "This is a sufficiently long transcript for the disabled-path test."
        )
        is None
    )


def test_missing_key_returns_none(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis.settings",
        Settings(enable_llm_analysis=True, openrouter_api_key=None),
    )
    assert analyze_transcript_ai("A long transcript that would otherwise be analysed.") is None


def test_short_transcript_returns_none(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis.settings",
        Settings(enable_llm_analysis=True, openrouter_api_key="sk-test"),
    )
    assert analyze_transcript_ai("hi") is None


def test_enabled_parses_verdict(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis.settings",
        Settings(enable_llm_analysis=True, openrouter_api_key="sk-test"),
    )
    raw = json.dumps(
        {
            "is_scam": True,
            "confidence": 0.92,
            "scam_category": "digital_arrest",
            "key_indicators": ["threats of arrest", "verification fee"],
            "explanation_en": "The caller uses the digital-arrest script.",
            "explanation_hi": "कॉलर डिजिटल अरेस्ट स्क्रिप्ट का उपयोग कर रहा है।",
        }
    )
    monkeypatch.setattr("app.services.llm_analysis._post_json", lambda payload: raw)

    out = analyze_transcript_ai(
        "This is CBI. You are under digital arrest. Pay the verification fee now."
    )
    assert out is not None
    assert out["status"] == "ok"
    assert out["model"] == "poolside/laguna-s-2.1:free"
    assert out["verdict"]["is_scam"] is True
    assert out["verdict"]["confidence"] == pytest.approx(0.92)
    assert out["verdict"]["scam_category"] == "digital_arrest"
    assert out["verdict"]["key_indicators"]
    assert out["verdict"]["explanation"]["en"]
    assert out["verdict"]["explanation"]["hi"]


def test_transport_failure_returns_none(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis.settings",
        Settings(enable_llm_analysis=True, openrouter_api_key="sk-test"),
    )

    def boom(payload):
        raise RuntimeError("network down")

    monkeypatch.setattr("app.services.llm_analysis._post_json", boom)
    assert analyze_transcript_ai("A sufficiently long transcript for the failure test.") is None


def test_bad_reply_returns_none(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis.settings",
        Settings(enable_llm_analysis=True, openrouter_api_key="sk-test"),
    )
    monkeypatch.setattr("app.services.llm_analysis._post_json", lambda payload: "not json at all")
    assert analyze_transcript_ai("A sufficiently long transcript for the bad-reply test.") is None


# ---------------------------------------------------------------------------
# _parse_verdict / _norm_verdict
# ---------------------------------------------------------------------------

def test_parse_verdict_plain_json():
    obj = {
        "is_scam": True,
        "confidence": 0.9,
        "scam_category": "fake_courier",
        "key_indicators": ["parcel trap"],
        "explanation_en": "e",
        "explanation_hi": "h",
    }
    v = _parse_verdict(json.dumps(obj))
    assert v is not None and v["is_scam"] is True
    assert v["scam_category"] == "fake_courier"


def test_parse_verdict_fenced():
    raw = '```json\n{"is_scam": false, "confidence": 0.1, "key_indicators": []}\n```'
    v = _parse_verdict(raw)
    assert v is not None and v["is_scam"] is False
    assert v["confidence"] == pytest.approx(0.1)


def test_parse_verdict_with_prose():
    raw = 'Sure! Here you go: {"is_scam": true, "confidence": 0.85} and nothing else.'
    v = _parse_verdict(raw)
    assert v is not None and v["is_scam"] is True


def test_parse_verdict_garbage():
    assert _parse_verdict("no json here") is None
    assert _parse_verdict("") is None


def test_norm_clamps_confidence_and_indicators():
    v = _norm_verdict({"is_scam": True, "confidence": 5.0, "key_indicators": "not-a-list"})
    assert v["confidence"] == 1.0
    assert v["key_indicators"] == []


# ---------------------------------------------------------------------------
# _post_json — 429 backoff
# ---------------------------------------------------------------------------

class _SeqUrlOpen:
    """urlopen double that raises 429 the first N calls, then returns a reply."""

    def __init__(self, fail_first: int):
        self.n = 0
        self.fail_first = fail_first

    def __call__(self, *a, **k):
        self.n += 1
        if self.n <= self.fail_first:
            raise urllib.error.HTTPError("url", 429, "rate limited", {}, None)
        return _OkResp()


class _OkResp:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b'{"choices":[{"message":{"content":"{\\"is_scam\\": true}"}}]}'


def test_post_json_retries_on_429(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _SeqUrlOpen(fail_first=2))
    out = _post_json({"model": "x"})
    assert out is not None and '"is_scam": true' in out


def test_post_json_gives_up_after_retries(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _SeqUrlOpen(fail_first=99))
    assert _post_json({"model": "x"}) is None


# ---------------------------------------------------------------------------
# risk_engine.ai — escalation, never downgrade
# ---------------------------------------------------------------------------

def test_ai_corroboration_escalates_benign():
    res = assess(
        media_type="text",
        scam=_text_signal("benign", 0.9),
        ai=_ai_verdict(is_scam=True, confidence=0.95, category="digital_arrest"),
    )
    assert res["risk"]["level"] == "high"
    assert res["risk"]["score"] >= 65
    assert any(f["id"] == "ai-llm-corrob" for f in res["red_flags"])


def test_ai_low_confidence_does_not_escalate():
    base = assess(media_type="text", scam=_text_signal("benign", 0.9))
    low = assess(
        media_type="text",
        scam=_text_signal("benign", 0.9),
        ai=_ai_verdict(is_scam=True, confidence=0.5),
    )
    assert low["risk"]["score"] == base["risk"]["score"]
    assert not any(f["id"] == "ai-llm-corrob" for f in low["red_flags"])


def test_ai_benign_does_not_downgrade():
    res = assess(
        media_type="text",
        scam=_text_signal("digital_arrest", 0.95),
        ai=_ai_verdict(is_scam=False, confidence=0.99),
    )
    assert res["risk"]["level"] == "high"
    assert any(f["id"] == "scam-arrest" for f in res["red_flags"])


def test_ai_unavailable_status_has_no_effect():
    res = assess(
        media_type="text",
        scam=_text_signal("benign", 0.9),
        ai={"status": "unavailable", "model": None, "verdict": None},
    )
    assert res["risk"]["score"] == 5.0
    assert not any(f["id"] == "ai-llm-corrob" for f in res["red_flags"])


# ---------------------------------------------------------------------------
# pipeline wiring
# ---------------------------------------------------------------------------

class _FakeScam:
    def classify(self, text):  # noqa: ARG002  (test double)
        return {
            "name": "text",
            "status": "available",
            "available": True,
            "score": 0.2,
            "label": "benign",
            "detail": "benign",
            "metrics": {"category": "benign", "top_probability": 0.2, "confident": False},
        }


class _FakeDetectors:
    def __init__(self):
        self.scam = _FakeScam()


def test_pipeline_ai_scam_attaches_and_escalates(monkeypatch):
    # pipeline.py binds analyze_transcript_ai into its own namespace at import.
    monkeypatch.setattr(
        "app.services.pipeline.analyze_transcript_ai",
        lambda *a, **k: _ai_verdict(is_scam=True, confidence=0.95, category="digital_arrest"),
    )
    pipe = AnalysisPipeline(detectors=_FakeDetectors())
    res = pipe.analyze_transcript(
        "You are under digital arrest from the CBI, stay on this call and pay the verification fee immediately.",
        "en",
    )
    assert res["ai_analysis"] is not None
    assert res["ai_analysis"]["verdict"]["is_scam"] is True
    assert any(f["id"] == "ai-llm-corrob" for f in res["red_flags"])
    assert res["risk"]["level"] == "high"


def test_pipeline_ai_none_leaves_verdict_unchanged(monkeypatch):
    monkeypatch.setattr("app.services.pipeline.analyze_transcript_ai", lambda *a, **k: None)
    pipe = AnalysisPipeline(detectors=_FakeDetectors())
    res = pipe.analyze_transcript(
        "Hello, just checking in about the groceries and the weather today.",
        "en",
    )
    assert res["ai_analysis"] is None
    assert res["risk"]["level"] == "low"
    assert res["risk"]["score"] == 5.0
