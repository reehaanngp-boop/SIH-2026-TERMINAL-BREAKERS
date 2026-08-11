"""Tests for persons-of-interest and voice-print enrolment."""

from __future__ import annotations


def test_person_crud_and_case_link(client, auth_headers):
    cid = client.post("/api/v1/cases", json={"title": "C"}, headers=auth_headers).json()["id"]
    resp = client.post(
        "/api/v1/people",
        json={"name": "Ravi Kumar", "role": "suspect", "phone": "+919999999999", "case_ids": [cid]},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    pid = resp.json()["id"]
    assert cid in resp.json()["case_ids"]

    listing = client.get("/api/v1/people", params={"role": "suspect"}, headers=auth_headers).json()
    assert len(listing) == 1

    updated = client.patch(f"/api/v1/people/{pid}", json={"role": "victim"}, headers=auth_headers).json()
    assert updated["role"] == "victim"

    assert client.delete(f"/api/v1/people/{pid}", headers=auth_headers).status_code == 204


def test_enroll_voice_creates_print(client, auth_headers, wav_path):
    pid = client.post("/api/v1/people", json={"name": "Suspect A"}, headers=auth_headers).json()["id"]
    with wav_path.open("rb") as fh:
        resp = client.post(f"/api/v1/people/{pid}/enroll-voice", files={"file": ("sample.wav", fh, "audio/wav")}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["voice_print_id"]
    assert resp.json()["duration_seconds"] is not None

    detail = client.get(f"/api/v1/people/{pid}", headers=auth_headers).json()
    assert len(detail["voice_prints"]) == 1
    assert detail["voice_prints"][0]["owner_kind"] == "person"


def test_person_link_unlink_case(client, auth_headers):
    cid = client.post("/api/v1/cases", json={"title": "C"}, headers=auth_headers).json()["id"]
    pid = client.post("/api/v1/people", json={"name": "Witness B"}, headers=auth_headers).json()["id"]

    resp = client.post(f"/api/v1/people/{pid}/link", json={"case_id": cid}, headers=auth_headers)
    assert cid in resp.json()["case_ids"]

    resp = client.request("DELETE", f"/api/v1/people/{pid}/link", json={"case_id": cid}, headers=auth_headers)
    assert cid not in resp.json()["case_ids"]
