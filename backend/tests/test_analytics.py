"""Tests for the analytics dashboard."""

from __future__ import annotations


def test_analytics_counts(client, auth_headers):
    client.post("/api/v1/cases", json={"title": "C1"}, headers=auth_headers)
    client.post("/api/v1/cases", json={"title": "C2"}, headers=auth_headers)
    client.post("/api/v1/analyze/transcript", json={"text": "Your account is frozen, share the OTP immediately"})

    body = client.get("/api/v1/analytics", headers=auth_headers).json()
    assert body["stats"]["cases"] == 2
    assert body["stats"]["scans"] >= 1
    assert body["stats"]["reported_numbers"] == 0
    assert len(body["scans_last_14d"]) == 14
    assert any(r["level"] == "high" and r["count"] >= 1 for r in body["risk_levels"])


def test_analytics_recent_high_risk(client, auth_headers):
    client.post("/api/v1/analyze/transcript", json={"text": "Police here, you are under digital arrest, pay now"})
    body = client.get("/api/v1/analytics", headers=auth_headers).json()
    assert body["recent_high_risk"]
