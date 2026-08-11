"""Application exceptions and FastAPI error handlers."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class DigiRakshaError(Exception):
    """Base application error."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "error"

    def __init__(self, message: str, *, status_code: int | None = None, code: str | None = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class UnsupportedMediaError(DigiRakshaError):
    code = "unsupported_media"


class ValidationError(DigiRakshaError):
    code = "validation_error"


class JobNotFoundError(DigiRakshaError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "job_not_found"


class MemberNotFoundError(DigiRakshaError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "member_not_found"


class EnrollmentError(DigiRakshaError):
    code = "enrollment_error"


class NotFoundError(DigiRakshaError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class AuthError(DigiRakshaError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "auth_required"


class InvalidCredentialsError(DigiRakshaError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "invalid_pin"


class SetupRequiredError(DigiRakshaError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "setup_required"


class AlreadySetupError(DigiRakshaError):
    status_code = status.HTTP_409_CONFLICT
    code = "already_setup"


class LockedOutError(DigiRakshaError):
    status_code = status.HTTP_423_LOCKED
    code = "locked_out"


class CaseNotFoundError(DigiRakshaError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "case_not_found"


class EvidenceNotFoundError(DigiRakshaError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "evidence_not_found"


class PersonNotFoundError(DigiRakshaError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "person_not_found"


class ReportError(DigiRakshaError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "report_error"


def register_exception_handlers(app: FastAPI) -> None:
    """Attach JSON handlers for DigiRakshaError so clients get structured errors."""

    @app.exception_handler(DigiRakshaError)
    async def _digiraksha_error_handler(request: Request, exc: DigiRakshaError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
