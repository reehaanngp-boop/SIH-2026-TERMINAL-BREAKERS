"""Phone-intelligence ledger: reported numbers and case links."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.db.models import Case, Person, ReportedNumber


def _normalize(phone: str) -> str:
    """Reduce a phone number to one canonical form for lookups.

    Callers store numbers in inconsistent formats (``+919988012345``,
    ``919988012345``, ``09988012345``, ``9988012345``). Comparing them
    verbatim silently misses matches, so we drop non-digits, then strip the
    Indian country code ``91`` and the legacy trunk ``0`` prefix. Every path
    (report, lookup, case/person linking) normalizes through this same
    function, which is what makes the ledger consistent.
    """
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) >= 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits


def _risk_level(record) -> str:
    """Derive a human-facing risk tier from ledger state."""
    if record.status == "verified_fraud":
        return "high"
    if record.status == "cleared":
        return "low"
    if record.count >= 3:
        return "high"
    if record.count >= 2:
        return "medium"
    return "monitored"


def linked_case_titles(db: Session, phone: str) -> list[str]:
    """Case titles that reference this number directly or via a person."""
    p = _normalize(phone)
    titles: set[str] = set()
    for case in db.execute(select(Case)).scalars().unique().all():
        if (case.victim_phone and _normalize(case.victim_phone) == p) or (
            case.suspect_phone and _normalize(case.suspect_phone) == p
        ):
            titles.add(case.case_number)
    for person in db.execute(select(Person)).scalars().unique().all():
        if person.phone and _normalize(person.phone) == p:
            for case in person.cases:
                titles.add(case.case_number)
    return sorted(titles)


def lookup(db: Session, phone: str) -> tuple[ReportedNumber | None, list[str]]:
    p = _normalize(phone)
    record = db.execute(select(ReportedNumber).where(ReportedNumber.phone == p)).scalars().first()
    return record, linked_case_titles(db, phone)


def list_reported(db: Session) -> list[ReportedNumber]:
    return list(db.execute(select(ReportedNumber).order_by(ReportedNumber.last_seen.desc())).scalars().all())


def report(db: Session, phone: str, notes: str | None = None) -> ReportedNumber:
    p = _normalize(phone)
    if len(p) < 5:
        raise ValidationError("Please enter a valid phone number.")
    record = db.execute(select(ReportedNumber).where(ReportedNumber.phone == p)).scalars().first()
    now = datetime.now(timezone.utc)
    if record is None:
        record = ReportedNumber(phone=p, status="reported", count=1, notes=notes)
        db.add(record)
    else:
        record.count += 1
        record.last_seen = now
        if notes:
            record.notes = notes
    db.commit()
    db.refresh(record)
    return record


def set_status(db: Session, phone_id: str, status: str) -> ReportedNumber:
    if status not in {"reported", "verified_fraud", "cleared"}:
        raise ValidationError(f"Unknown status '{status}'.")
    record = db.get(ReportedNumber, phone_id)
    if record is None:
        raise NotFoundError(f"Reported number {phone_id} not found.")
    record.status = status
    db.commit()
    db.refresh(record)
    return record
