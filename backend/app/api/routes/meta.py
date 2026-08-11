"""Application metadata endpoint (detector availability, report channels)."""

from __future__ import annotations

from fastapi import APIRouter

from app import APP_NAME, __version__
from app.detectors import get_detectors
from app.schemas.common import HELPLINE_NUMBER, I4C_SITE, REPORT_PORTAL

router = APIRouter(tags=["system"])


@router.get("/meta", summary="App metadata and detector availability")
def meta() -> dict:
    return {
        "app": APP_NAME,
        "version": __version__,
        "detectors": get_detectors().describe(),
        "report": {
            "helpline": HELPLINE_NUMBER,
            "portal": REPORT_PORTAL,
            "i4c": I4C_SITE,
        },
    }
