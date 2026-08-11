"""Builders turning ORM rows into the police-suite response schemas."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Evidence, EvidenceEvent, Person, Scan, VoicePrint
from app.schemas.police import (
    CaseDetailOut,
    CaseListItem,
    EvidenceEventOut,
    EvidenceOut,
    PersonOut,
    VoicePrintOut,
)


def _dt(value) -> str | None:
    return value.isoformat() if value else None


def build_evidence_out(db: Session, e: Evidence) -> EvidenceOut:
    scan = db.get(Scan, e.scan_id) if e.scan_id else None
    return EvidenceOut(
        id=e.id,
        case_id=e.case_id,
        case_number=e.case.case_number if e.case else None,
        filename=e.filename,
        original_filename=e.original_filename,
        media_type=e.media_type,
        size_bytes=e.size_bytes,
        sha256=e.sha256,
        scan_id=e.scan_id,
        risk_level=scan.risk_level if scan else None,
        risk_score=scan.risk_score if scan else None,
        uploaded_at=_dt(e.uploaded_at),
        uploaded_by=e.uploaded_by,
        note=e.note,
        events=[build_event_out(ev) for ev in e.events],
    )


def build_event_out(ev: EvidenceEvent) -> EvidenceEventOut:
    return EvidenceEventOut(
        id=ev.id,
        action=ev.action,
        actor=ev.actor,
        detail=ev.detail,
        created_at=_dt(ev.created_at),
    )


def build_voiceprint_out(vp: VoicePrint) -> VoicePrintOut:
    return VoicePrintOut(
        id=vp.id,
        label=vp.label,
        owner_kind=vp.owner_kind,
        owner_id=vp.owner_id,
        duration_seconds=vp.duration_seconds,
        created_at=_dt(vp.created_at),
    )


def voice_prints_for(db: Session, person_id: str) -> list[VoicePrint]:
    return list(
        db.execute(
            select(VoicePrint)
            .where(VoicePrint.owner_kind == "person", VoicePrint.owner_id == person_id)
            .order_by(VoicePrint.created_at)
        )
        .scalars()
        .all()
    )


def build_person_out(db: Session, p: Person) -> PersonOut:
    return PersonOut(
        id=p.id,
        name=p.name,
        role=p.role,
        phone=p.phone,
        id_type=p.id_type,
        id_number=p.id_number,
        address=p.address,
        notes=p.notes,
        created_at=_dt(p.created_at),
        updated_at=_dt(p.updated_at),
        case_ids=[c.id for c in p.cases],
        voice_prints=[build_voiceprint_out(vp) for vp in voice_prints_for(db, p.id)],
    )


def build_case_list_item(c) -> CaseListItem:
    return CaseListItem(
        id=c.id,
        case_number=c.case_number,
        title=c.title,
        status=c.status,
        priority=c.priority,
        officer_name=c.officer_name,
        victim_name=c.victim_name,
        suspect_name=c.suspect_name,
        evidence_count=len(c.evidence),
        person_count=len(c.persons),
        created_at=_dt(c.created_at),
    )


def build_case_detail(db: Session, c) -> CaseDetailOut:
    item = build_case_list_item(c)
    return CaseDetailOut(
        **item.model_dump(),
        description=c.description,
        officer_badge=c.officer_badge,
        victim_phone=c.victim_phone,
        suspect_phone=c.suspect_phone,
        notes=c.notes,
        updated_at=_dt(c.updated_at),
        closed_at=_dt(c.closed_at),
        evidence=[build_evidence_out(db, e) for e in c.evidence],
        persons=[build_person_out(db, p) for p in c.persons],
        events=[build_event_out(ev) for ev in _case_events(db, c)],
    )


def _case_events(db: Session, c) -> list[EvidenceEvent]:
    evidence_ids = [e.id for e in c.evidence]
    stmt = (
        select(EvidenceEvent)
        .where(
            or_(
                EvidenceEvent.case_id == c.id,
                EvidenceEvent.evidence_id.in_(evidence_ids) if evidence_ids else False,
            )
        )
        .order_by(EvidenceEvent.created_at)
    )
    return list(db.execute(stmt).scalars().unique().all())
