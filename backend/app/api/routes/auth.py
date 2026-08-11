"""Local PIN access control: setup, login, logout, change PIN."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import security
from app.core.exceptions import (
    AlreadySetupError,
    InvalidCredentialsError,
    LockedOutError,
    SetupRequiredError,
)
from app.db.database import get_db
from app.schemas.police import (
    AuthStatus,
    ChangePinRequest,
    LoginRequest,
    LoginResult,
    SetupRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.get("/status", response_model=AuthStatus, summary="Access-control status for the app shell")
def auth_status(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AuthStatus:
    """Report whether setup is needed and whether the presented token is valid.

    When ``enable_auth`` is disabled the gate is reported as open so the
    frontend skips the login screen entirely.
    """
    if not settings.enable_auth:
        return AuthStatus(setup_required=False, authenticated=True, officer_name=security.officer_name(db))

    if not security.setup_done(db):
        return AuthStatus(setup_required=True, authenticated=False, officer_name=None)

    authenticated = False
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        secret = security.get_server_secret(db)
        authenticated = security.verify_token(secret, token, settings.token_ttl_hours)

    return AuthStatus(
        setup_required=False,
        authenticated=authenticated,
        officer_name=security.officer_name(db),
    )


@router.post("/setup", response_model=LoginResult, summary="First-run setup: officer name + PIN")
def setup(data: SetupRequest, db: Session = Depends(get_db)) -> LoginResult:
    if not settings.enable_auth:
        raise AlreadySetupError("Access control is disabled; setup is not required.")
    if security.setup_done(db):
        raise AlreadySetupError("Setup has already been completed. Log in instead.")

    pin = data.pin
    if len(pin) < settings.pin_min_length:
        raise InvalidCredentialsError(
            f"PIN must be at least {settings.pin_min_length} characters long.",
            status_code=400,
            code="pin_too_short",
        )

    secret = security.get_server_secret(db)  # persist a secret for this install
    security.set_setting(db, "auth.pin", security.hash_pin(pin))
    security.set_officer(db, data.officer_name.strip())
    db.commit()

    token = security.issue_token(secret)
    return LoginResult(token=token, officer_name=data.officer_name.strip(), expires_in_hours=settings.token_ttl_hours)


@router.post("/login", response_model=LoginResult, summary="Log in with the local PIN")
def login(data: LoginRequest, db: Session = Depends(get_db)) -> LoginResult:
    if not settings.enable_auth:
        raise SetupRequiredError("Access control is disabled; login is not required.", status_code=400, code="auth_disabled")
    if not security.setup_done(db):
        raise SetupRequiredError("App setup has not been completed yet.")

    if security.is_locked_out(db):
        raise LockedOutError("Too many failed attempts. Try again in a minute.")

    stored = security.get_setting(db, "auth.pin")
    if not stored or not security.verify_pin(data.pin, stored):
        security.register_failed_attempt(db, settings.pin_max_attempts)
        raise InvalidCredentialsError("Incorrect PIN.")

    security.clear_failed_attempts(db)
    secret = security.get_server_secret(db)
    token = security.issue_token(secret)
    return LoginResult(token=token, officer_name=security.officer_name(db), expires_in_hours=settings.token_ttl_hours)


@router.post("/logout", status_code=204, summary="Discard the client-side session")
def logout(db: Session = Depends(get_db)) -> None:
    """Tokens are stateless HMAC values; logout simply discards them client-side."""
    security.clear_failed_attempts(db)


@router.post("/change-pin", status_code=204, summary="Change the local PIN")
def change_pin(data: ChangePinRequest, db: Session = Depends(get_db)) -> None:
    if not settings.enable_auth:
        raise SetupRequiredError("Access control is disabled.", status_code=400, code="auth_disabled")
    if not security.setup_done(db):
        raise SetupRequiredError("App setup has not been completed yet.")

    stored = security.get_setting(db, "auth.pin")
    if not stored or not security.verify_pin(data.current_pin, stored):
        raise InvalidCredentialsError("Current PIN is incorrect.")

    if len(data.new_pin) < settings.pin_min_length:
        raise InvalidCredentialsError(
            f"PIN must be at least {settings.pin_min_length} characters long.",
            status_code=400,
            code="pin_too_short",
        )

    security.set_setting(db, "auth.pin", security.hash_pin(data.new_pin))
    db.commit()
