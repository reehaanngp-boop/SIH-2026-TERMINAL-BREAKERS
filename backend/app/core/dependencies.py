"""FastAPI dependency protecting the police-suite routes."""

from __future__ import annotations

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import security
from app.core.exceptions import AuthError, InvalidCredentialsError, SetupRequiredError
from app.db.database import get_db

settings = get_settings()


def require_auth(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> str | None:
    """Gate the police routes behind the local PIN token; returns the actor name.

    When ``enable_auth`` is false (tests, embedded demo) every request passes and
    the configured officer name is returned for audit attribution. Otherwise the
    ``Authorization: Bearer <token>`` header is checked against the server secret;
    a 403 is returned before setup has run.
    """
    if not settings.enable_auth:
        return security.officer_name(db)

    if not security.setup_done(db):
        raise SetupRequiredError("App setup has not been completed yet.")

    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("Missing authentication token.")

    token = authorization.split(" ", 1)[1].strip()
    secret = security.get_server_secret(db)
    if not security.verify_token(secret, token, settings.token_ttl_hours):
        raise InvalidCredentialsError("Invalid or expired token.")
    return security.officer_name(db)
