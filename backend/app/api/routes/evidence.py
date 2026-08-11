"""Evidence vault endpoints (PIN-gated): ingest, hash integrity, download."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.serializers import build_evidence_out
from app.config import get_settings
from app.core.dependencies import require_auth
from app.core.exceptions import EvidenceNotFoundError, ValidationError
from app.db.database import get_db
from app.schemas.police import (
    EvidenceListOut,
    EvidenceNoteUpdate,
    EvidenceOut,
    HashVerifyResult,
    LinkEvidenceRequest,
)
from app.services import case_service, evidence_service

router = APIRouter(prefix="/evidence", tags=["evidence"])
settings = get_settings()


@router.post("", response_model=EvidenceOut, status_code=201, summary="Ingest an evidence file")
async def upload_evidence(
    file: UploadFile = File(..., description="Audio/video evidence"),
    case_id: str | None = Form(default=None),
    note: str | None = Form(default=None),
    actor: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> EvidenceOut:
    path, media_type, original, sha, size = evidence_service.save_evidence_file(file, settings)
    evidence = evidence_service.create_evidence(
        db,
        filename=path.name,
        original_filename=original,
        media_type=media_type,
        size_bytes=size,
        sha256=sha,
        stored_path=str(path),
        case_id=case_id or None,
        uploaded_by=actor,
        note=note,
        actor=actor,
    )
    return build_evidence_out(db, evidence)


@router.get("", response_model=EvidenceListOut, summary="List evidence (search/filter)")
def list_evidence(
    search: str = "",
    media_type: str | None = None,
    risk_level: str | None = None,
    case_id: str | None = None,
    limit: int = 200,
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> EvidenceListOut:
    items = evidence_service.list_evidence(
        db, search=search, media_type=media_type, risk_level=risk_level, case_id=case_id, limit=limit
    )
    return EvidenceListOut(items=[build_evidence_out(db, e) for e in items], total=len(items))


@router.get("/{evidence_id}", response_model=EvidenceOut, summary="Evidence detail with chain of custody")
def get_evidence(
    evidence_id: str,
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> EvidenceOut:
    return build_evidence_out(db, evidence_service.get_evidence(db, evidence_id))


@router.get("/{evidence_id}/verify", response_model=HashVerifyResult, summary="Recompute SHA-256 to verify integrity")
def verify_hash(
    evidence_id: str,
    actor: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> HashVerifyResult:
    evidence = evidence_service.get_evidence(db, evidence_id)
    matches, current = evidence_service.verify_hash(db, evidence, actor=actor)
    return HashVerifyResult(
        evidence_id=evidence.id,
        matches=matches,
        sha256=current,
        message=("Hash verified — file matches the record." if matches else "Hash MISMATCH — file differs from the record."),
    )


@router.get("/{evidence_id}/download", summary="Download the original evidence bytes")
def download_evidence(
    evidence_id: str,
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> FileResponse:
    evidence = evidence_service.get_evidence(db, evidence_id)
    path = Path(evidence.stored_path)
    if not path.exists():
        raise EvidenceNotFoundError(f"Evidence file for {evidence_id} is missing from disk.")
    return FileResponse(
        path,
        filename=evidence.original_filename,
        media_type="application/octet-stream",
    )


@router.patch("/{evidence_id}/note", response_model=EvidenceOut, summary="Update the evidence note")
def update_note(
    evidence_id: str,
    data: EvidenceNoteUpdate,
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> EvidenceOut:
    evidence = evidence_service.update_note(db, evidence_service.get_evidence(db, evidence_id), data.note)
    return build_evidence_out(db, evidence)


@router.patch("/{evidence_id}/link", response_model=EvidenceOut, summary="Link evidence to a case")
def link_evidence(
    evidence_id: str,
    data: LinkEvidenceRequest,
    actor: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> EvidenceOut:
    evidence = evidence_service.get_evidence(db, evidence_id)
    case = case_service.get_case(db, data.case_id)
    case_service.link_evidence(db, case, evidence, actor=actor)
    return build_evidence_out(db, evidence)


@router.delete("/{evidence_id}/link", response_model=EvidenceOut, summary="Unlink evidence from its case")
def unlink_evidence(
    evidence_id: str,
    actor: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> EvidenceOut:
    evidence = evidence_service.get_evidence(db, evidence_id)
    if not evidence.case_id:
        raise ValidationError("Evidence is not linked to any case.")
    case_service.unlink_evidence(db, evidence, actor=actor)
    return build_evidence_out(db, evidence)


@router.delete("/{evidence_id}", status_code=204, summary="Delete evidence and its stored file")
def delete_evidence(
    evidence_id: str,
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> None:
    evidence_service.delete_evidence(db, evidence_service.get_evidence(db, evidence_id))
