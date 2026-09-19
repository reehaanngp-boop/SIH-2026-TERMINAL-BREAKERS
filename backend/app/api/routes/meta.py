"""Application metadata endpoint (detector availability, report channels)."""

from __future__ import annotations

from fastapi import APIRouter

from app import APP_NAME, __version__
from app.detectors import get_detectors
from app.schemas.common import HELPLINE_NUMBER, I4C_SITE, REPORT_PORTAL
from app.services.llm_analysis import llm_model, llm_ready

router = APIRouter(tags=["system"])


@router.get("/meta", summary="App metadata, detector availability, and AI status")
def meta() -> dict:
    ai_avail, ai_reason = llm_ready()
    return {
        "app": APP_NAME,
        "version": __version__,
        "detectors": get_detectors().describe(),
        "ai": {
            "available": ai_avail,
            "model": llm_model(),
            "reason": ai_reason if not ai_avail else None,
        },
        "report": {
            "helpline": HELPLINE_NUMBER,
            "portal": REPORT_PORTAL,
            "i4c": I4C_SITE,
        },
    }
