"""Tests for the local PIN gate: setup, login, tokens, lockout, route gating."""

from __future__ import annotations

import time

from app.core.security import hash_pin, issue_token, verify_pin, verify_token


def test_pin_hash_roundtrip():
    stored = hash_pin("4821")
    assert stored != "4821"
    assert verify_pin("4821", stored)
    assert not verify_pin("0000", stored)
    # different salts -> different digests for the same pin
    assert hash_pin("4821") != stored


def test_token_issue_verify_and_expiry():
    secret = "s" * 32
    token = issue_token(secret)
    assert verify_token(secret, token, ttl_hours=12)
    assert not verify_token("another-secret", token, ttl_hours=12)
    assert not verify_token(secret, token[:-2] + "xx", ttl_hours=12)  # tampered
    old = issue_token(secret, int(time.time()) - 7200)
    assert not verify_token(secret, old, ttl_hours=1)  # issued 2h ago, ttl 1h
    assert not verify_token(secret, "not-a-token", ttl_hours=12)


def test_status_before_setup(client):
    body = client.get("/api/v1/auth/status").json()
    assert body["setup_required"] is True
    assert body["authenticated"] is False


def test_setup_login_and_status(client):
    resp = client.post("/api/v1/auth/setup", json={"officer_name": "Inspector Rao", "pin": "4321"})
    assert resp.status_code == 200
    token = resp.json()["token"]
    assert resp.json()["officer_name"] == "Inspector Rao"

    status = client.get("/api/v1/auth/status", headers={"Authorization": f"Bearer {token}"}).json()
    assert status["setup_required"] is False
    assert status["authenticated"] is True

    # wrong pin -> 401
    assert client.post("/api/v1/auth/login", json={"pin": "9999"}).status_code == 401
    # correct pin -> token
    resp = client.post("/api/v1/auth/login", json={"pin": "4321"})
    assert resp.status_code == 200
    assert resp.json()["token"]


def test_setup_twice_conflicts(client):
    client.post("/api/v1/auth/setup", json={"officer_name": "A", "pin": "1234"})
    resp = client.post("/api/v1/auth/setup", json={"officer_name": "B", "pin": "5678"})
    assert resp.status_code == 409


def test_change_pin(client, auth_headers):
    resp = client.post("/api/v1/auth/change-pin", json={"current_pin": "1234", "new_pin": "5678"}, headers=auth_headers)
    assert resp.status_code == 204
    assert client.post("/api/v1/auth/login", json={"pin": "5678"}).status_code == 200
    assert client.post("/api/v1/auth/login", json={"pin": "1234"}).status_code == 401


def test_lockout_after_repeated_failures(client):
    client.post("/api/v1/auth/setup", json={"officer_name": "A", "pin": "1234"})
    for _ in range(5):
        client.post("/api/v1/auth/login", json={"pin": "0000"})
    assert client.post("/api/v1/auth/login", json={"pin": "1234"}).status_code == 423


def test_police_routes_require_token(client):
    # before setup the gate returns 403 (setup_required)…
    assert client.get("/api/v1/cases").status_code == 403
    # …and after setup a missing/invalid token returns 401
    client.post("/api/v1/auth/setup", json={"officer_name": "A", "pin": "1234"})
    assert client.get("/api/v1/cases").status_code == 401
    assert client.get("/api/v1/analytics").status_code == 401
    assert client.get("/api/v1/export/cases").status_code == 401


def test_police_route_with_token(client, auth_headers):
    assert client.get("/api/v1/cases", headers=auth_headers).status_code == 200
