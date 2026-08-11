"""Phone intelligence endpoints (PIN-gated)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_auth
from app.db.database import get_db
from app.schemas.police import (
    PhoneLookupResult,
    PhoneRecordOut,
    PhoneReportRequest,
    PhoneStatusUpdate,
)
from app.services import phone_service

router = APIRouter(prefix="/phone", tags=["phone"])


def _record_out(record, linked_cases: list[str] | None = None) -> PhoneRecordOut:
    return PhoneRecordOut(
        id=record.id,
        phone=record.phone,
        status=record.status,
        count=record.count,
        first_seen=record.first_seen.isoformat() if record.first_seen else "",
        last_seen=record.last_seen.isoformat() if record.last_seen else "",
        notes=record.notes,
        linked_cases=linked_cases or [],
    )


@router.get("", response_model=list[PhoneRecordOut], summary="List reported numbers")
def list_reported(
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> list[PhoneRecordOut]:
    return [_record_out(r) for r in phone_service.list_reported(db)]


@router.get("/{phone_number}", response_model=PhoneLookupResult, summary="Look up a number (status + linked cases)")
def lookup(
    phone_number: str,
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> PhoneLookupResult:
    record, linked = phone_service.lookup(db, phone_number)
    if record is None:
        return PhoneLookupResult(found=False, record=None, message="No reports on record for this number.")
    return PhoneLookupResult(
        found=True,
        record=_record_out(record, linked),
        message=f"Number reported {record.count} time(s).",
    )


@router.post("/report", response_model=PhoneRecordOut, status_code=201, summary="Report a suspicious number")
def report(
    data: PhoneReportRequest,
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> PhoneRecordOut:
    record = phone_service.report(db, data.phone, data.notes)
    return _record_out(record, phone_service.linked_case_titles(db, record.phone))


@router.patch("/{record_id}/status", response_model=PhoneRecordOut, summary="Update a number's status")
def update_status(
    record_id: str,
    data: PhoneStatusUpdate,
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> PhoneRecordOut:
    record = phone_service.set_status(db, record_id, data.status)
    return _record_out(record, phone_service.linked_case_titles(db, record.phone))
