"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app import APP_NAME, __version__
from app.config import get_settings

router = APIRouter(tags=["system"])
settings = get_settings()


@router.get("/health", summary="Liveness probe")
def health() -> dict:
    return {
        "status": "ok",
        "app": APP_NAME,
        "version": __version__,
        "api_version": "v1",
    }
