"""Tests for the AI Assistant / Copilot endpoints and service."""

from __future__ import annotations

import json
from app.services.llm_analysis import chat_with_copilot, draft_complaint_ai, quick_triage_ai


def test_assistant_status_endpoint(client):
    resp = client.get("/api/v1/assistant/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "available" in data
    assert "active_model" in data


def test_assistant_chat_endpoint_mocked(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis._post_json",
        lambda payload, api_key=None: "Digital Arrest is completely fake. Under Indian Law, police never conduct arrests over video call.",
    )
    resp = client.post(
        "/api/v1/assistant/chat",
        json={"messages": [{"role": "user", "content": "Is digital arrest real under Indian law?"}]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "Digital Arrest" in data["reply"]
    assert len(data["suggestions"]) > 0


def test_assistant_chat_offline_fallback(client, monkeypatch):
    def raise_err(payload, api_key=None):
        raise RuntimeError("No network")

    monkeypatch.setattr("app.services.llm_analysis._post_json", raise_err)
    resp = client.post(
        "/api/v1/assistant/chat",
        json={"messages": [{"role": "user", "content": "I got a call from CBI saying digital arrest"}]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "offline_fallback"
    assert "DIGITAL ARREST IS 100% FAKE" in data["reply"]


def test_assistant_quick_check_endpoint(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis._post_json",
        lambda payload, api_key=None: json.dumps(
            {
                "is_scam": True,
                "scam_category": "digital_arrest",
                "confidence": 0.95,
                "summary_en": "CBI impersonation scam.",
                "summary_hi": "सीबीआई प्रतिरूपण घोटाला।",
                "urgency_level": "critical",
                "recommended_action": "Do not pay. Call 1930.",
            }
        ),
    )
    resp = client.post(
        "/api/v1/assistant/quick-check",
        json={"text": "This is CBI officer. You are under digital arrest. Pay 50000."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["is_scam"] is True
    assert data["data"]["scam_category"] == "digital_arrest"


def test_assistant_draft_fir_endpoint(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_analysis._post_json",
        lambda payload, api_key=None: "# Formal Cyber Crime Complaint\n\nTo the Cyber Police Station...\nSection 66D IT Act",
    )
    resp = client.post(
        "/api/v1/assistant/draft-fir",
        json={
            "victim_name": "Rohan Sharma",
            "suspect_phone": "+91-9876543210",
            "amount_lost": "25000",
            "scam_type": "Digital Arrest Scam",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "complaint_markdown" in data
    assert "Section 66D" in data["complaint_markdown"]
