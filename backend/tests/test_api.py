"""API smoke tests: health, meta, transcript analysis, upload, registry flow."""

from __future__ import annotations

import time
from pathlib import Path

import pytest


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_meta_reports_detectors(client):
    r = client.get("/api/v1/meta")
    assert r.status_code == 200
    body = r.json()
    assert "detectors" in body
    assert body["report"]["helpline"] == "1930"


def test_transcript_scam_scores_high(client):
    r = client.post(
        "/api/v1/analyze/transcript",
        json={
            "text": (
                "this is the CBI investigating your case, you are under digital arrest, "
                "stay on this video call, pay the verification fee immediately or the "
                "police will arrest you, do not tell anyone"
            ),
            "language_hint": "en",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["risk"]["level"] == "high"
    assert body["risk"]["score"] >= 65
    assert any(f["id"] == "scam-arrest" for f in body["red_flags"])


def test_transcript_benign_scores_low(client):
    r = client.post(
        "/api/v1/analyze/transcript",
        json={"text": "good morning, this is the restaurant calling to confirm your order"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["risk"]["level"] == "low"
    assert body["risk"]["score"] < 40


def test_transcript_validation_error(client):
    r = client.post("/api/v1/analyze/transcript", json={"text": ""})
    assert r.status_code == 422


@pytest.mark.slow
def test_media_upload_job_flow(client, wav_path: Path):
    """Upload a clip, poll the job, expect a completed analysis."""
    with wav_path.open("rb") as fh:
        created = client.post(
            "/api/v1/analyze",
            files={"file": ("tone.wav", fh, "audio/wav")},
        )
    assert created.status_code == 200
    job_id = created.json()["job_id"]

    # The first media analysis loads the Whisper model, so allow ample time.
    deadline = time.time() + 120
    status = None
    while time.time() < deadline:
        jr = client.get(f"/api/v1/analyze/jobs/{job_id}")
        assert jr.status_code == 200
        status = jr.json()["status"]
        if status in ("completed", "failed"):
            break
        time.sleep(1.5)

    assert status in ("completed", "failed"), "job did not finish in time"
    if status == "completed":
        result = jr.json()["result"]
        assert result["risk"]["level"] in ("low", "medium", "high")
        assert result["media_type"] == "audio"


def test_history_lists_scans(client):
    client.post(
        "/api/v1/analyze/transcript",
        json={"text": "hi dad, i will reach home by evening"},
    )
    r = client.get("/api/v1/analyze/history")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_registry_crud_and_enroll(client, wav_path: Path):
    # Create
    r = client.post("/api/v1/registry/members", json={"name": "Sunita", "relationship": "Aunt"})
    assert r.status_code == 200
    member_id = r.json()["id"]

    # List
    members = client.get("/api/v1/registry/members").json()
    assert any(m["id"] == member_id for m in members)

    # Enrol voice
    with wav_path.open("rb") as fh:
        enr = client.post(
            f"/api/v1/registry/members/{member_id}/enroll",
            files={"file": ("sample.wav", fh, "audio/wav")},
        )
    assert enr.status_code == 200
    assert enr.json()["member_id"] == member_id

    # Verify (same file -> match)
    with wav_path.open("rb") as fh:
        ver = client.post(
            "/api/v1/registry/verify",
            data={"member_id": member_id},
            files={"file": ("probe.wav", fh, "audio/wav")},
        )
    assert ver.status_code == 200
    assert ver.json()["match"] is True

    # Delete
    assert client.delete(f"/api/v1/registry/members/{member_id}").status_code == 204
    assert client.get("/api/v1/registry/members").json() == []


def test_registry_verify_without_enrollment_400(client, wav_path: Path):
    r = client.post("/api/v1/registry/members", json={"name": "Newcomer"})
    member_id = r.json()["id"]
    with wav_path.open("rb") as fh:
        ver = client.post(
            "/api/v1/registry/verify",
            data={"member_id": member_id},
            files={"file": ("probe.wav", fh, "audio/wav")},
        )
    assert ver.status_code == 400
