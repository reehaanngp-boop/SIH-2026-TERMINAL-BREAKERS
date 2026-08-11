"""Service layer for police cases."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import CaseNotFoundError, EvidenceNotFoundError, ValidationError
from app.db.models import Case, Evidence, Person
from app.schemas.police import CaseCreate, CaseUpdate
from app.services import audit


def next_case_number(db: Session) -> str:
    """Build the next case number: ``DR-YYYY-NNNN`` (per-year sequence)."""
    year = datetime.now(timezone.utc).year
    prefix = f"DR-{year}-"
    row = db.execute(
        select(func.max(Case.case_number)).where(Case.case_number.like(f"{prefix}%"))
    ).scalar()
    seq = (int(row.rsplit("-", 1)[1]) + 1) if row else 1
    return f"{prefix}{seq:04d}"


def create_case(db: Session, data: CaseCreate, actor: str | None = None) -> Case:
    case = Case(
        case_number=next_case_number(db),
        title=data.title.strip(),
        description=data.description,
        priority=data.priority or "normal",
        officer_name=data.officer_name,
        officer_badge=data.officer_badge,
        victim_name=data.victim_name,
        victim_phone=data.victim_phone,
        suspect_name=data.suspect_name,
        suspect_phone=data.suspect_phone,
        notes=data.notes,
    )
    db.add(case)
    db.flush()
    audit.log_event(db, action="case_event", case_id=case.id, actor=actor, detail=f"Case {case.case_number} created")
    db.commit()
    db.refresh(case)
    return case


def list_cases(db: Session, *, search: str = "", status: str | None = None) -> list[Case]:
    stmt = select(Case)
    if status:
        stmt = stmt.where(Case.status == status)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Case.case_number.ilike(like),
                Case.title.ilike(like),
                Case.officer_name.ilike(like),
                Case.victim_name.ilike(like),
                Case.victim_phone.ilike(like),
                Case.suspect_name.ilike(like),
                Case.suspect_phone.ilike(like),
            )
        )
    stmt = stmt.order_by(Case.created_at.desc())
    return list(db.execute(stmt).scalars().unique().all())


def get_case(db: Session, case_id: str) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise CaseNotFoundError(f"Case {case_id} not found.")
    return case


def update_case(db: Session, case_id: str, data: CaseUpdate, actor: str | None = None) -> Case:
    case = get_case(db, case_id)
    changes: list[str] = []
    for field in ("title", "description", "priority", "officer_name", "officer_badge",
                  "victim_name", "victim_phone", "suspect_name", "suspect_phone", "notes"):
        value = getattr(data, field)
        if value is None:
            continue
        if getattr(data, field, None) is not None and value != getattr(case, field):
            changes.append(field)
        setattr(case, field, value)
    case.updated_at = datetime.now(timezone.utc)
    if changes:
        audit.log_event(db, action="case_event", case_id=case.id, actor=actor,
                        detail=f"Updated fields: {', '.join(changes)}")
    db.commit()
    db.refresh(case)
    return case


def set_status(db: Session, case_id: str, status: str, actor: str | None = None) -> Case:
    if status not in {"open", "investigating", "closed"}:
        raise ValidationError(f"Unknown status '{status}'.")
    case = get_case(db, case_id)
    old = case.status
    case.status = status
    case.updated_at = datetime.now(timezone.utc)
    if status == "closed":
        case.closed_at = datetime.now(timezone.utc)
    elif old == "closed":
        case.closed_at = None
    db.flush()
    audit.log_event(db, action="status_changed", case_id=case.id, actor=actor,
                    detail=f"Status changed {old} -> {status}")
    db.commit()
    db.refresh(case)
    return case


def add_note(db: Session, case_id: str, note: str, actor: str | None = None) -> Case:
    case = get_case(db, case_id)
    if not note or not note.strip():
        raise ValidationError("Note cannot be empty.")
    stamped = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}] {note.strip()}"
    case.notes = (case.notes + "\n" + stamped) if case.notes else stamped
    case.updated_at = datetime.now(timezone.utc)
    db.flush()
    audit.log_event(db, action="note_added", case_id=case.id, actor=actor, detail=note.strip())
    db.commit()
    db.refresh(case)
    return case


def delete_case(db: Session, case_id: str) -> None:
    case = get_case(db, case_id)
    db.delete(case)
    db.commit()


def link_evidence(db: Session, case: Case, evidence: Evidence, actor: str | None = None) -> Evidence:
    evidence.case_id = case.id
    db.flush()
    audit.log_event(db, action="linked_to_case", evidence_id=evidence.id, case_id=case.id,
                    actor=actor, detail=f"Linked to {case.case_number}")
    db.commit()
    return evidence


def unlink_evidence(db: Session, evidence: Evidence, actor: str | None = None) -> Evidence:
    case_id = evidence.case_id
    evidence.case_id = None
    db.flush()
    audit.log_event(db, action="unlinked_from_case", evidence_id=evidence.id, case_id=case_id,
                    actor=actor)
    db.commit()
    return evidence


def attach_person(db: Session, case: Case, person: Person) -> Case:
    if person not in case.persons:
        case.persons.append(person)
        db.commit()
    db.refresh(case)
    return case


def detach_person(db: Session, case: Case, person: Person) -> Case:
    if person in case.persons:
        case.persons.remove(person)
        db.commit()
    db.refresh(case)
    return case
