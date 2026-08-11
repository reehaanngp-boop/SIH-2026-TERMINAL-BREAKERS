"""Tests for case management endpoints."""

from __future__ import annotations


def test_create_and_get_case(client, auth_headers):
    resp = client.post(
        "/api/v1/cases",
        json={"title": "Digital Arrest call", "priority": "high", "victim_name": "Sita", "suspect_phone": "+919000000000"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["case_number"].startswith("DR-")
    assert body["status"] == "open"
    assert body["priority"] == "high"

    detail = client.get(f"/api/v1/cases/{body['id']}", headers=auth_headers).json()
    assert detail["victim_name"] == "Sita"


def test_case_numbers_increment_per_year(client, auth_headers):
    a = client.post("/api/v1/cases", json={"title": "A"}, headers=auth_headers).json()
    b = client.post("/api/v1/cases", json={"title": "B"}, headers=auth_headers).json()
    assert a["case_number"] != b["case_number"]
    assert int(a["case_number"].rsplit("-", 1)[1]) + 1 == int(b["case_number"].rsplit("-", 1)[1])


def test_case_status_transition(client, auth_headers):
    cid = client.post("/api/v1/cases", json={"title": "T"}, headers=auth_headers).json()["id"]
    resp = client.patch(f"/api/v1/cases/{cid}/status", json={"status": "investigating"}, headers=auth_headers)
    assert resp.json()["status"] == "investigating"
    resp = client.patch(f"/api/v1/cases/{cid}/status", json={"status": "closed"}, headers=auth_headers)
    body = resp.json()
    assert body["status"] == "closed"
    assert body["closed_at"] is not None


def test_case_notes_and_search(client, auth_headers):
    cid = client.post("/api/v1/cases", json={"title": "Courier scam"}, headers=auth_headers).json()["id"]
    client.post(f"/api/v1/cases/{cid}/notes", json={"note": "Victim submitted the recording."}, headers=auth_headers)

    results = client.get("/api/v1/cases", params={"search": "courier"}, headers=auth_headers).json()
    assert len(results) == 1

    detail = client.get(f"/api/v1/cases/{cid}", headers=auth_headers).json()
    assert "Victim submitted" in detail["notes"]
    assert any(ev["action"] == "note_added" for ev in detail["events"])


def test_create_case_from_scan(client, auth_headers):
    scan = client.post("/api/v1/analyze/transcript", json={"text": "Your son is in custody, pay the fine immediately"}).json()
    resp = client.post("/api/v1/cases", json={"title": "Kin emergency", "scan_id": scan["scan_id"]}, headers=auth_headers)
    assert resp.status_code == 201
    detail = resp.json()
    assert len(detail["evidence"]) == 1
    assert detail["evidence"][0]["scan_id"] == scan["scan_id"]


def test_attach_scan_to_existing_case(client, auth_headers):
    scan = client.post("/api/v1/analyze/transcript", json={"text": "You are under digital arrest, pay now"}).json()
    # Open a case WITHOUT a scan first, then attach the scan afterwards.
    case = client.post("/api/v1/cases", json={"title": "Existing case"}, headers=auth_headers).json()
    assert len(case["evidence"]) == 0

    resp = client.post(f"/api/v1/cases/{case['id']}/attach-scan/{scan['scan_id']}", headers=auth_headers)
    assert resp.status_code == 200
    detail = resp.json()
    assert len(detail["evidence"]) == 1
    assert detail["evidence"][0]["scan_id"] == scan["scan_id"]
    assert detail["evidence"][0]["sha256"]
    assert any(ev["action"] == "uploaded" for ev in detail["events"])


def test_attach_scan_unknown_scan(client, auth_headers):
    case = client.post("/api/v1/cases", json={"title": "X"}, headers=auth_headers).json()
    resp = client.post(f"/api/v1/cases/{case['id']}/attach-scan/does-not-exist", headers=auth_headers)
    assert resp.status_code == 404


def test_case_update_and_delete(client, auth_headers):
    cid = client.post("/api/v1/cases", json={"title": "C"}, headers=auth_headers).json()["id"]
    resp = client.patch(f"/api/v1/cases/{cid}", json={"victim_name": "Asha", "priority": "critical"}, headers=auth_headers)
    assert resp.json()["victim_name"] == "Asha"
    assert client.delete(f"/api/v1/cases/{cid}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/v1/cases/{cid}", headers=auth_headers).status_code == 404


def test_case_not_found(client, auth_headers):
    assert client.get("/api/v1/cases/nope", headers=auth_headers).status_code == 404
