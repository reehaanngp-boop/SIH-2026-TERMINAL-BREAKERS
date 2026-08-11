"""Tests for cross-evidence voice matching."""

from __future__ import annotations


def test_match_ranks_enrolled_speaker(client, auth_headers, wav_path, noise_path):
    pid = client.post("/api/v1/people", json={"name": "Caller X"}, headers=auth_headers).json()["id"]
    with wav_path.open("rb") as fh:
        client.post(f"/api/v1/people/{pid}/enroll-voice", files={"file": ("sample.wav", fh, "audio/wav")}, headers=auth_headers)

    with wav_path.open("rb") as fh:
        resp = client.post("/api/v1/voice-match", files={"file": ("unknown.wav", fh, "audio/wav")}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["matches"]
    top = body["matches"][0]
    assert top["match"] is True
    assert top["owner_id"] == pid
    assert top["owner_ref"] and "Caller X" in top["owner_ref"]

    # a different signal (noise) must not match the enrolled tone
    with noise_path.open("rb") as fh:
        resp = client.post("/api/v1/voice-match", files={"file": ("noise.wav", fh, "audio/wav")}, headers=auth_headers)
    assert resp.json()["matches"][0]["match"] is False


def test_match_empty_returns_empty(client, auth_headers, wav_path):
    with wav_path.open("rb") as fh:
        resp = client.post("/api/v1/voice-match", files={"file": ("a.wav", fh, "audio/wav")}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["matches"] == []
