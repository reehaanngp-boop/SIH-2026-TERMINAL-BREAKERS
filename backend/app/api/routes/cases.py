"""Police case management endpoints (PIN-gated)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.serializers import build_case_detail, build_case_list_item
from app.core.dependencies import require_auth
from app.core.exceptions import ValidationError
from app.db.database import get_db
from app.db.models import Case, Evidence, Scan
from app.schemas.police import (
    CaseCreate,
    CaseDetailOut,
    CaseListItem,
    CaseStatusUpdate,
    CaseUpdate,
    NoteRequest,
)
from app.services import case_service, evidence_service, person_service

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=list[CaseListItem], summary="List cases (searchable/filterable)")
def list_cases(
    search: str = "",
    status: str | None = None,
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> list[CaseListItem]:
    return [build_case_list_item(c) for c in case_service.list_cases(db, search=search, status=status)]


@router.post("", response_model=CaseDetailOut, status_code=201, summary="Open a new case")
def create_case(
    data: CaseCreate,
    actor: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> CaseDetailOut:
    case = case_service.create_case(db, data, actor=actor)
    if data.scan_id:
        _attach_scan_as_evidence(db, case, data.scan_id, actor)
    return build_case_detail(db, case)


@router.post("/{case_id}/attach-scan/{scan_id}", response_model=CaseDetailOut, summary="Attach an existing analysis scan as evidence")
def attach_scan(
    case_id: str,
    scan_id: str,
    actor: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> CaseDetailOut:
    case = case_service.get_case(db, case_id)
    _attach_scan_as_evidence(db, case, scan_id, actor)
    return build_case_detail(db, case)


@router.get("/{case_id}", response_model=CaseDetailOut, summary="Case detail (evidence, persons, audit)")
def get_case(
    case_id: str,
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> CaseDetailOut:
    return build_case_detail(db, case_service.get_case(db, case_id))


@router.patch("/{case_id}", response_model=CaseDetailOut, summary="Update case fields")
def update_case(
    case_id: str,
    data: CaseUpdate,
    actor: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> CaseDetailOut:
    case = case_service.update_case(db, case_id, data, actor=actor)
    return build_case_detail(db, case)


@router.delete("/{case_id}", status_code=204, summary="Delete a case")
def delete_case(
    case_id: str,
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> None:
    case_service.delete_case(db, case_id)


@router.patch("/{case_id}/status", response_model=CaseDetailOut, summary="Transition case status")
def set_status(
    case_id: str,
    data: CaseStatusUpdate,
    actor: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> CaseDetailOut:
    case = case_service.set_status(db, case_id, data.status, actor=actor)
    return build_case_detail(db, case)


@router.post("/{case_id}/notes", response_model=CaseDetailOut, summary="Append a case note")
def add_note(
    case_id: str,
    data: NoteRequest,
    actor: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> CaseDetailOut:
    case = case_service.add_note(db, case_id, data.note, actor=actor)
    return build_case_detail(db, case)


@router.post("/{case_id}/evidence/{evidence_id}", response_model=CaseDetailOut, summary="Attach evidence to a case")
def link_evidence(
    case_id: str,
    evidence_id: str,
    actor: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> CaseDetailOut:
    case = case_service.get_case(db, case_id)
    evidence = evidence_service.get_evidence(db, evidence_id)
    case_service.link_evidence(db, case, evidence, actor=actor)
    return build_case_detail(db, case)


@router.delete("/{case_id}/evidence/{evidence_id}", response_model=CaseDetailOut, summary="Detach evidence from a case")
def unlink_evidence(
    case_id: str,
    evidence_id: str,
    actor: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> CaseDetailOut:
    case = case_service.get_case(db, case_id)
    evidence = evidence_service.get_evidence(db, evidence_id)
    if evidence.case_id != case.id:
        raise ValidationError("This evidence is not attached to the case.")
    case_service.unlink_evidence(db, evidence, actor=actor)
    return build_case_detail(db, case)


@router.post("/{case_id}/persons/{person_id}", response_model=CaseDetailOut, summary="Link a person to a case")
def link_person(
    case_id: str,
    person_id: str,
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> CaseDetailOut:
    case = case_service.get_case(db, case_id)
    person = person_service.get_person(db, person_id)
    case_service.attach_person(db, case, person)
    return build_case_detail(db, case)


@router.delete("/{case_id}/persons/{person_id}", response_model=CaseDetailOut, summary="Unlink a person from a case")
def unlink_person(
    case_id: str,
    person_id: str,
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> CaseDetailOut:
    case = case_service.get_case(db, case_id)
    person = person_service.get_person(db, person_id)
    case_service.detach_person(db, case, person)
    return build_case_detail(db, case)


def _attach_scan_as_evidence(db: Session, case: Case, scan_id: str, actor: str | None) -> None:
    """Turn an existing analysis scan into the case's first evidence item."""
    scan = db.get(Scan, scan_id)
    if scan is None:
        raise ValidationError(f"Scan {scan_id} not found.", status_code=404)
    path = scan.file_path
    if path and Path(path).exists():
        hasher = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                hasher.update(chunk)
        sha = hasher.hexdigest()
        size = Path(path).stat().st_size
        stored = path
    else:
        text = scan.transcript or ""
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        size = len(text.encode("utf-8"))
        stored = ""

    filename = scan.original_filename or f"scan-{scan.id}.txt"
    evidence_service.create_evidence(
        db,
        filename=filename,
        original_filename=filename,
        media_type=scan.media_type,
        size_bytes=size,
        sha256=sha,
        stored_path=stored,
        case_id=case.id,
        scan_id=scan.id,
        uploaded_by=actor,
        note="Imported from an existing analysis result.",
        actor=actor,
    )
