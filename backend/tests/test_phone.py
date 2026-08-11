"""Tests for phone intelligence: report, lookup, status."""

from __future__ import annotations


def test_report_lookup_and_count(client, auth_headers):
    resp = client.post("/api/v1/phone/report", json={"phone": "9000001234", "notes": "Claimed to be police"}, headers=auth_headers)
    assert resp.status_code == 201
    rid = resp.json()["id"]

    lookup = client.get("/api/v1/phone/9000001234", headers=auth_headers).json()
    assert lookup["found"] is True
    assert lookup["record"]["count"] == 1

    client.post("/api/v1/phone/report", json={"phone": "9000001234"}, headers=auth_headers)
    lookup = client.get("/api/v1/phone/9000001234", headers=auth_headers).json()
    assert lookup["record"]["count"] == 2

    status = client.patch(f"/api/v1/phone/{rid}/status", json={"status": "verified_fraud"}, headers=auth_headers).json()
    assert status["status"] == "verified_fraud"


def test_lookup_unknown_number(client, auth_headers):
    lookup = client.get("/api/v1/phone/0000000000", headers=auth_headers).json()
    assert lookup["found"] is False


def test_linked_cases_from_number(client, auth_headers):
    client.post("/api/v1/cases", json={"title": "Fraud call", "suspect_phone": "919800000001"}, headers=auth_headers)
    client.post("/api/v1/phone/report", json={"phone": "919800000001"}, headers=auth_headers)
    lookup = client.get("/api/v1/phone/919800000001", headers=auth_headers).json()
    assert lookup["record"]["linked_cases"] == ["DR-2026-0001"]
