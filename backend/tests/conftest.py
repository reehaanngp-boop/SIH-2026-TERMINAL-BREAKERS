"""Test fixtures: isolated SQLite database + HTTP client.

The DATABASE_URL override must be set BEFORE any app module is imported, so it
lives at module top level. Each test then starts from an empty schema.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

# -- Point the app at a throwaway SQLite file before importing it -------------
_TMP = Path(tempfile.mkdtemp(prefix="digiraksha_tests_"))
os_environ_patch = __import__("os").environ
os_environ_patch["DATABASE_URL"] = f"sqlite:///{(_TMP / 'test.db').as_posix()}"

import pytest as _pytest  # noqa: F401  (keep import ordering explicit)

from fastapi.testclient import TestClient  # noqa: E402

from app.db.database import Base, engine  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db():
    """Start every test from an empty, freshly-created schema."""
    from app.db import models  # noqa: F401  (register tables)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers(client):
    """Set up the PIN gate and return valid Bearer headers for police routes.

    The default config enables auth, so police routes are 401 without these.
    """
    status = client.get("/api/v1/auth/status").json()
    if status["setup_required"]:
        resp = client.post("/api/v1/auth/setup", json={"officer_name": "Inspector Test", "pin": "1234"})
        assert resp.status_code == 200
    resp = client.post("/api/v1/auth/login", json={"pin": "1234"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['token']}"}


@pytest.fixture()
def wav_path() -> Path:
    """A short real-speech sample (SAPI 'David' voice) — the enrollment voice.

    ECAPA-TDNN is a *speech* model, so pure tones/noise are out-of-distribution
    and all cluster together (~0.6 cosine). Real speech fixtures are required to
    test speaker separation meaningfully.
    """
    return Path(__file__).parent / "fixtures" / "speaker_david.wav"


@pytest.fixture()
def noise_path() -> Path:
    """A different speaker (SAPI 'Zira' voice, same sentence) — must NOT match."""
    return Path(__file__).parent / "fixtures" / "speaker_zira.wav"
