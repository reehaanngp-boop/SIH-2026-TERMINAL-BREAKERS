"""Local access control: PBKDF2 PIN hashing + HMAC-SHA256 session tokens.

The PIN is only ever stored as a salted PBKDF2-HMAC-SHA256 digest; the HMAC
secret lives in the ``app_settings`` table so it survives restarts and is never
written to the frontend.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time

from sqlalchemy.orm import Session

from app.db.models import AppSetting

_ALGO = "pbkdf2"
_ITERATIONS = 120_000
_KEY_SECRET = "auth.secret"
_KEY_PIN = "auth.pin"
_KEY_OFFICER = "auth.officer_name"
_KEY_SETUP = "auth.setup_done"
_KEY_FAILED = "auth.failed_attempts"
_KEY_LOCKED = "auth.locked_until"


# ---------------------------------------------------------------------------
# Key/value helpers
# ---------------------------------------------------------------------------
def get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.get(AppSetting, key)
    return row.value if row else default


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.get(AppSetting, key)
    if row is None:
        db.add(AppSetting(key=key, value=value))
    else:
        row.value = value


def delete_setting(db: Session, key: str) -> None:
    row = db.get(AppSetting, key)
    if row is not None:
        db.delete(row)


# ---------------------------------------------------------------------------
# Server secret / tokens
# ---------------------------------------------------------------------------
def get_server_secret(db: Session) -> str:
    """Return (and lazily create) the HMAC signing secret for this install."""
    secret = get_setting(db, _KEY_SECRET)
    if not secret:
        secret = secrets.token_hex(32)
        set_setting(db, _KEY_SECRET, secret)
        db.commit()
    return secret


def issue_token(secret: str, issued_at: int | None = None) -> str:
    """HMAC-SHA256 signed token over ``digiraksha:<issued_at>``."""
    issued_at = issued_at or int(time.time())
    message = f"digiraksha:{issued_at}".encode()
    sig = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return f"{issued_at}.{sig}"


def verify_token(secret: str, token: str, ttl_hours: int) -> bool:
    """Return True if ``token`` is authentic and not older than ``ttl_hours``."""
    try:
        issued_at_str, sig = token.split(".", 1)
        issued_at = int(issued_at_str)
    except (ValueError, TypeError):
        return False
    expected = issue_token(secret, issued_at)
    if not hmac.compare_digest(expected, token):
        return False
    return (time.time() - issued_at) <= ttl_hours * 3600


# ---------------------------------------------------------------------------
# PIN
# ---------------------------------------------------------------------------
def hash_pin(pin: str, iterations: int = _ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, iterations)
    return f"{_ALGO}${iterations}${salt.hex()}${digest.hex()}"


def verify_pin(pin: str, stored: str) -> bool:
    try:
        algo, iterations_str, salt_hex, digest_hex = stored.split("$")
        if algo != _ALGO:
            return False
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        digest = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, iterations)
    return hmac.compare_digest(candidate, digest)


# ---------------------------------------------------------------------------
# High-level auth state
# ---------------------------------------------------------------------------
def setup_done(db: Session) -> bool:
    return get_setting(db, _KEY_SETUP) == "1"


def is_locked_out(db: Session) -> bool:
    locked_until = get_setting(db, _KEY_LOCKED, "")
    if not locked_until:
        return False
    try:
        return float(locked_until) > time.time()
    except ValueError:
        return False


def register_failed_attempt(db: Session, max_attempts: int) -> None:
    """Increment the failed-login counter and lock the app for 60s at the cap."""
    current = 0
    try:
        current = int(get_setting(db, _KEY_FAILED, "0"))
    except ValueError:
        current = 0
    current += 1
    set_setting(db, _KEY_FAILED, str(current))
    if current >= max_attempts:
        set_setting(db, _KEY_LOCKED, str(time.time() + 60))
        set_setting(db, _KEY_FAILED, "0")
    db.commit()


def clear_failed_attempts(db: Session) -> None:
    delete_setting(db, _KEY_FAILED)
    delete_setting(db, _KEY_LOCKED)
    db.commit()


def officer_name(db: Session) -> str:
    return get_setting(db, _KEY_OFFICER, "Officer")


def set_officer(db: Session, name: str) -> None:
    set_setting(db, _KEY_OFFICER, name)
    set_setting(db, _KEY_SETUP, "1")
    db.commit()
