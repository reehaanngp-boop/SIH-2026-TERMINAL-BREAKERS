"""Tests for the PDF case report."""

from __future__ import annotations


def test_pdf_report_generated(client, auth_headers):
    cid = client.post("/api/v1/cases", json={"title": "Digital arrest case", "victim_name": "Meera"}, headers=auth_headers).json()["id"]

    resp = client.get(f"/api/v1/reports/{cid}/pdf", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")
    assert resp.content[:4] == b"%PDF"

    # exporting logs a chain-of-custody event
    detail = client.get(f"/api/v1/cases/{cid}", headers=auth_headers).json()
    assert any(ev["action"] == "report_exported" for ev in detail["events"])


def test_pdf_report_missing_case(client, auth_headers):
    assert client.get("/api/v1/reports/nope/pdf", headers=auth_headers).status_code == 404


def test_export_cases_csv(client, auth_headers):
    client.post("/api/v1/cases", json={"title": "C"}, headers=auth_headers)
    resp = client.get("/api/v1/export/cases", headers=auth_headers)
    assert resp.status_code == 200
    text = resp.content.decode("utf-8-sig")
    assert "case_number" in text


def test_export_scans_csv(client, auth_headers):
    client.post("/api/v1/analyze/transcript", json={"text": "hello, this is a normal message"})
    resp = client.get("/api/v1/export/scans", headers=auth_headers)
    assert resp.status_code == 200
    text = resp.content.decode("utf-8-sig")
    assert "scan_id" in text
