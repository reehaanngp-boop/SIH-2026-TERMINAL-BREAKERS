"""CSV export endpoints (PIN-gated). UTF-8 with BOM so Excel opens them cleanly."""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import require_auth
from app.db.database import get_db
from app.db.models import Case, Scan

router = APIRouter(prefix="/export", tags=["export"])


def _csv_response(rows: list[list], filename: str) -> Response:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerows(rows)
    data = "﻿" + buf.getvalue()  # UTF-8 BOM for Excel
    return Response(
        content=data.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/cases", summary="Export all cases as CSV")
def export_cases(
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> Response:
    rows = [[
        "case_number", "title", "status", "priority", "officer_name", "officer_badge",
        "victim_name", "victim_phone", "suspect_name", "suspect_phone",
        "created_at", "updated_at", "closed_at", "description", "notes",
    ]]
    for c in db.execute(select(Case).order_by(Case.created_at)).scalars().unique().all():
        rows.append([
            c.case_number, c.title, c.status, c.priority, c.officer_name or "", c.officer_badge or "",
            c.victim_name or "", c.victim_phone or "", c.suspect_name or "", c.suspect_phone or "",
            c.created_at.isoformat() if c.created_at else "", c.updated_at.isoformat() if c.updated_at else "",
            c.closed_at.isoformat() if c.closed_at else "", c.description or "", c.notes or "",
        ])
    return _csv_response(rows, "digiraksha-cases.csv")


@router.get("/scans", summary="Export scan/analysis history as CSV")
def export_scans(
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> Response:
    rows = [[
        "scan_id", "created_at", "status", "media_type", "original_filename",
        "duration_seconds", "risk_level", "risk_score", "language", "transcript",
    ]]
    for s in db.execute(select(Scan).order_by(Scan.created_at.desc())).scalars().unique().all():
        rows.append([
            s.id, s.created_at.isoformat() if s.created_at else "", s.status, s.media_type,
            s.original_filename or "", s.duration_seconds if s.duration_seconds is not None else "",
            s.risk_level or "", s.risk_score if s.risk_score is not None else "", s.language or "",
            (s.transcript or "").replace("\n", " "),
        ])
    return _csv_response(rows, "digiraksha-scan-history.csv")
