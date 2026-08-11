"""Service layer for the evidence vault (hash-integrity, chain of custody)."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.core.exceptions import EvidenceNotFoundError, ValidationError
from app.db.models import Evidence, Scan
from app.services import audit
from app.services.media import detect_media_type

_CHUNK = 1 << 20  # 1 MiB


def save_evidence_file(upload: UploadFile, settings: Settings) -> tuple[Path, str, str, str, int]:
    """Stream an upload to disk while computing its SHA-256.

    Returns ``(path, media_type, original_filename, sha256, size_bytes)``.
    """
    original = upload.filename or "evidence"
    media_type = detect_media_type(original)
    ext = Path(original).suffix.lower()

    max_bytes = settings.max_upload_mb * 1024 * 1024
    dest = settings.upload_dir / f"ev-{uuid.uuid4().hex}{ext}"

    hasher = hashlib.sha256()
    total = 0
    with dest.open("wb") as out:
        while True:
            chunk = upload.file.read(_CHUNK)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                dest.unlink(missing_ok=True)
                raise ValidationError(
                    f"File too large: {total / 1e6:.1f} MB exceeds the {settings.max_upload_mb} MB limit."
                )
            out.write(chunk)
            hasher.update(chunk)

    if total == 0:
        dest.unlink(missing_ok=True)
        raise ValidationError("Uploaded file is empty.")

    return dest, media_type, original, hasher.hexdigest(), total


def create_evidence(
    db: Session,
    *,
    filename: str,
    original_filename: str,
    media_type: str | None,
    size_bytes: int | None,
    sha256: str,
    stored_path: str,
    case_id: str | None = None,
    scan_id: str | None = None,
    uploaded_by: str | None = None,
    note: str | None = None,
    actor: str | None = None,
) -> Evidence:
    if case_id:
        from app.core.exceptions import CaseNotFoundError
        from app.db.models import Case

        if db.get(Case, case_id) is None:
            raise CaseNotFoundError(f"Case {case_id} not found.")

    evidence = Evidence(
        case_id=case_id,
        filename=filename,
        original_filename=original_filename,
        media_type=media_type,
        size_bytes=size_bytes,
        sha256=sha256,
        stored_path=stored_path,
        scan_id=scan_id,
        uploaded_by=uploaded_by,
        note=note,
    )
    db.add(evidence)
    db.flush()
    audit.log_event(db, action="uploaded", evidence_id=evidence.id, case_id=case_id,
                    actor=actor or uploaded_by,
                    detail=f"{original_filename} ({media_type or 'unknown'}) sha256={sha256[:12]}…")
    db.commit()
    db.refresh(evidence)
    return evidence


def list_evidence(
    db: Session,
    *,
    search: str = "",
    media_type: str | None = None,
    risk_level: str | None = None,
    case_id: str | None = None,
    limit: int = 200,
) -> list[Evidence]:
    stmt = select(Evidence)
    if media_type:
        stmt = stmt.where(Evidence.media_type == media_type)
    if case_id:
        stmt = stmt.where(Evidence.case_id == case_id)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(Evidence.original_filename.ilike(like), Evidence.sha256.ilike(like), Evidence.note.ilike(like))
        )
    stmt = stmt.order_by(Evidence.uploaded_at.desc()).limit(max(1, min(limit, 500)))
    items = list(db.execute(stmt).scalars().unique().all())
    if risk_level:
        # risk lives on the linked scan; filter in Python (small sets).
        items = [e for e in items if _scan_risk(db, e.scan_id) == risk_level]
    return items


def _scan_risk(db: Session, scan_id: str | None) -> str | None:
    if not scan_id:
        return None
    scan = db.get(Scan, scan_id)
    return scan.risk_level if scan else None


def get_evidence(db: Session, evidence_id: str) -> Evidence:
    evidence = db.get(Evidence, evidence_id)
    if evidence is None:
        raise EvidenceNotFoundError(f"Evidence {evidence_id} not found.")
    return evidence


def verify_hash(db: Session, evidence: Evidence, actor: str | None = None) -> tuple[bool, str]:
    """Recompute the stored file's SHA-256 and compare against the record."""
    path = Path(evidence.stored_path)
    if not path.exists():
        audit.log_event(db, action="hash_verified", evidence_id=evidence.id, actor=actor,
                        detail="verification failed: file missing on disk")
        db.commit()
        return False, evidence.sha256
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            hasher.update(chunk)
    current = hasher.hexdigest()
    matches = current == evidence.sha256
    audit.log_event(db, action="hash_verified", evidence_id=evidence.id, actor=actor,
                    detail=f"sha256={current[:12]}… {'MATCH' if matches else 'MISMATCH'}")
    db.commit()
    return matches, current


def update_note(db: Session, evidence: Evidence, note: str | None) -> Evidence:
    evidence.note = note
    db.commit()
    db.refresh(evidence)
    return evidence


def delete_evidence(db: Session, evidence: Evidence) -> None:
    path = Path(evidence.stored_path)
    db.delete(evidence)
    db.commit()
    path.unlink(missing_ok=True)
