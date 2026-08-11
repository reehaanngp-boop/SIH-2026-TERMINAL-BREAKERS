"""Dashboard analytics endpoint (PIN-gated)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_auth
from app.db.database import get_db
from app.schemas.police import AnalyticsStats
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsStats, summary="Dashboard statistics")
def dashboard(
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> AnalyticsStats:
    return AnalyticsStats(**analytics_service.get_stats(db))
