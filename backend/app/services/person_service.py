"""Service layer for persons-of-interest and their voice prints."""

from __future__ import annotations

import numpy as np
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import PersonNotFoundError, ValidationError
from app.db.models import Case, Person, VoicePrint
from app.schemas.police import PersonCreate, PersonUpdate


def create_person(db: Session, data: PersonCreate) -> Person:
    person = Person(
        name=data.name.strip(),
        role=data.role or "unknown",
        phone=data.phone,
        id_type=data.id_type,
        id_number=data.id_number,
        address=data.address,
        notes=data.notes,
    )
    if data.case_ids:
        cases = list(db.execute(select(Case).where(Case.id.in_(data.case_ids))).scalars().unique().all())
        person.cases = cases
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


def list_persons(db: Session, *, search: str = "", role: str | None = None) -> list[Person]:
    stmt = select(Person)
    if role:
        stmt = stmt.where(Person.role == role)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(Person.name.ilike(like), Person.phone.ilike(like), Person.id_number.ilike(like))
        )
    stmt = stmt.order_by(Person.created_at.desc())
    return list(db.execute(stmt).scalars().unique().all())


def get_person(db: Session, person_id: str) -> Person:
    person = db.get(Person, person_id)
    if person is None:
        raise PersonNotFoundError(f"Person {person_id} not found.")
    return person


def update_person(db: Session, person_id: str, data: PersonUpdate) -> Person:
    person = get_person(db, person_id)
    for field in ("name", "role", "phone", "id_type", "id_number", "address", "notes"):
        value = getattr(data, field)
        if value is not None:
            setattr(person, field, value)
    db.commit()
    db.refresh(person)
    return person


def delete_person(db: Session, person_id: str) -> None:
    person = get_person(db, person_id)
    db.delete(person)
    db.commit()


def link_to_case(db: Session, person: Person, case: Case) -> Person:
    if case not in person.cases:
        person.cases.append(case)
        db.commit()
    db.refresh(person)
    return person


def unlink_from_case(db: Session, person: Person, case: Case) -> Person:
    if case in person.cases:
        person.cases.remove(case)
        db.commit()
    db.refresh(person)
    return person


def enroll_voice(
    db: Session,
    person: Person,
    audio,
    saved_path: str,
    label: str | None = None,
) -> VoicePrint:
    """Compute the speaker embedding for a clip and store it as the person's voice print."""
    from app.detectors.audio.speaker_verify import compute_embedding

    if getattr(audio, "samples", None) is None or len(audio.samples) < 1024:
        raise ValidationError("Voice sample is too short to enrol.")
    try:
        embedding = compute_embedding(audio)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc

    print_ = VoicePrint(
        label=label or person.name,
        owner_kind="person",
        owner_id=person.id,
        file_path=saved_path,
        duration_seconds=round(float(getattr(audio, "duration", 0.0)), 2),
        embedding=[float(x) for x in np.asarray(embedding).tolist()],
    )
    db.add(print_)
    db.commit()
    db.refresh(print_)
    return print_
