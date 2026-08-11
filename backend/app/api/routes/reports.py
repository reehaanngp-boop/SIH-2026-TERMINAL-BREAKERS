"""PDF case-report endpoint (PIN-gated)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.dependencies import require_auth
from app.db.database import get_db
from app.services import case_service, report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{case_id}/pdf", summary="Export a formal PDF case report")
def case_report(
    case_id: str,
    actor: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> FileResponse:
    case = case_service.get_case(db, case_id)
    path = report_service.build_case_report(db, case, actor=actor)
    return FileResponse(
        str(path),
        media_type="application/pdf",
        filename=f"{case.case_number}-report.pdf",
    )
