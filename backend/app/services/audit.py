"""Audit log helper: one unified chain-of-custody timeline for cases and evidence."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import EvidenceEvent


def log_event(
    db: Session,
    *,
    action: str,
    case_id: str | None = None,
    evidence_id: str | None = None,
    actor: str | None = None,
    detail: str | None = None,
) -> EvidenceEvent:
    """Append an event to the audit timeline. Does not commit — the caller does."""
    event = EvidenceEvent(
        action=action,
        case_id=case_id,
        evidence_id=evidence_id,
        actor=actor,
        detail=detail,
    )
    db.add(event)
    return event
