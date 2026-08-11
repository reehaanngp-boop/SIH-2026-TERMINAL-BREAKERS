"""Tests for the evidence vault: ingest, hash integrity, download, linking."""

from __future__ import annotations

from app.db.database import SessionLocal
from app.db.models import Evidence


def test_upload_evidence_computes_sha256(client, auth_headers, wav_path):
    with wav_path.open("rb") as fh:
        resp = client.post("/api/v1/evidence", files={"file": ("call.wav", fh, "audio/wav")}, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["sha256"]) == 64
    assert body["media_type"] == "audio"
    assert body["events"][0]["action"] == "uploaded"

    verify = client.get(f"/api/v1/evidence/{body['id']}/verify", headers=auth_headers).json()
    assert verify["matches"] is True


def test_tampered_file_detected(client, auth_headers, wav_path):
    with wav_path.open("rb") as fh:
        eid = client.post("/api/v1/evidence", files={"file": ("call.wav", fh, "audio/wav")}, headers=auth_headers).json()["id"]

    db = SessionLocal()
    stored_path = db.get(Evidence, eid).stored_path
    db.close()
    with open(stored_path, "ab") as fh:
        fh.write(b"tampered-bytes")

    verify = client.get(f"/api/v1/evidence/{eid}/verify", headers=auth_headers).json()
    assert verify["matches"] is False


def test_evidence_link_case_and_download(client, auth_headers, wav_path):
    cid = client.post("/api/v1/cases", json={"title": "C"}, headers=auth_headers).json()["id"]
    with wav_path.open("rb") as fh:
        eid = client.post("/api/v1/evidence", files={"file": ("call.wav", fh, "audio/wav")}, headers=auth_headers).json()["id"]

    resp = client.patch(f"/api/v1/evidence/{eid}/link", json={"case_id": cid}, headers=auth_headers)
    assert resp.json()["case_id"] == cid
    assert resp.json()["case_number"]

    case_detail = client.get(f"/api/v1/cases/{cid}", headers=auth_headers).json()
    assert len(case_detail["evidence"]) == 1
    assert any(ev["action"] == "linked_to_case" for ev in case_detail["events"])

    download = client.get(f"/api/v1/evidence/{eid}/download", headers=auth_headers)
    assert download.status_code == 200
    assert len(download.content) > 0

    unlink = client.delete(f"/api/v1/evidence/{eid}/link", headers=auth_headers)
    assert unlink.json()["case_id"] is None

    assert client.delete(f"/api/v1/evidence/{eid}", headers=auth_headers).status_code == 204


def test_evidence_list_filter(client, auth_headers, wav_path):
    with wav_path.open("rb") as fh:
        client.post("/api/v1/evidence", files={"file": ("a.wav", fh, "audio/wav")}, headers=auth_headers)
    resp = client.get("/api/v1/evidence", params={"media_type": "audio"}, headers=auth_headers).json()
    assert resp["total"] >= 1
    resp = client.get("/api/v1/evidence", params={"media_type": "video"}, headers=auth_headers).json()
    assert resp["total"] == 0


def test_evidence_note_update(client, auth_headers, wav_path):
    with wav_path.open("rb") as fh:
        eid = client.post("/api/v1/evidence", files={"file": ("a.wav", fh, "audio/wav")}, headers=auth_headers).json()["id"]
    resp = client.patch(f"/api/v1/evidence/{eid}/note", json={"note": "Original WhatsApp recording"}, headers=auth_headers)
    assert resp.json()["note"] == "Original WhatsApp recording"
