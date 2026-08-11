"""ORM models: scans, family members and voice enrollments."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Table, Text
# Aliased because the ``FamilyMember.relationship`` mapped column shadows the
# ``relationship()`` helper inside the class body.
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Scan(Base):
    """One analysis job: a suspicious audio/video clip or raw transcript."""

    __tablename__ = "scans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued|running|completed|failed
    media_type: Mapped[str] = mapped_column(String(16))  # audio|video|text
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    language: Mapped[str | None] = mapped_column(String(32), nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)

    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)  # low|medium|high
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class FamilyMember(Base):
    """A trusted person whose voice can be enrolled in the Safe-Voice Registry."""

    __tablename__ = "family_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120))
    relationship: Mapped[str | None] = mapped_column(String(60), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    enrollments: Mapped[list[VoiceEnrollment]] = orm_relationship(
        back_populates="member", cascade="all, delete-orphan", lazy="selectin"
    )


class VoiceEnrollment(Base):
    """A stored voice sample/embedding belonging to a family member."""

    __tablename__ = "voice_enrollments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    member_id: Mapped[str] = mapped_column(ForeignKey("family_members.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)

    member: Mapped[FamilyMember] = orm_relationship(back_populates="enrollments")


class AppSetting(Base):
    """Key/value store for runtime configuration (auth secret, PIN hash, etc.)."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


# Many-to-many between cases and persons.
case_persons = Table(
    "case_persons",
    Base.metadata,
    Column("case_id", ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True),
    Column("person_id", ForeignKey("persons.id", ondelete="CASCADE"), primary_key=True),
)


class Case(Base):
    """A police investigation built around scam evidence."""

    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_number: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open|investigating|closed
    priority: Mapped[str] = mapped_column(String(16), default="normal")  # low|normal|high|critical
    officer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    officer_badge: Mapped[str | None] = mapped_column(String(60), nullable=True)
    victim_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    victim_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    suspect_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    suspect_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    evidence: Mapped[list[Evidence]] = orm_relationship(
        back_populates="case", cascade="all, delete-orphan", lazy="selectin"
    )
    persons: Mapped[list[Person]] = orm_relationship(
        secondary=case_persons, back_populates="cases", lazy="selectin"
    )


class Evidence(Base):
    """A piece of digital evidence attached to a case."""

    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id", ondelete="SET NULL"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    media_type: Mapped[str | None] = mapped_column(String(16), nullable=True)  # audio|video|text
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256: Mapped[str] = mapped_column(String(64))
    stored_path: Mapped[str] = mapped_column(String(500))
    scan_id: Mapped[str | None] = mapped_column(ForeignKey("scans.id", ondelete="SET NULL"), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    uploaded_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    case: Mapped[Case | None] = orm_relationship(back_populates="evidence")
    scan: Mapped[Scan | None] = orm_relationship()
    events: Mapped[list[EvidenceEvent]] = orm_relationship(
        back_populates="evidence", cascade="all, delete-orphan", lazy="selectin", order_by="EvidenceEvent.created_at"
    )


class EvidenceEvent(Base):
    """A single chain-of-custody event for an evidence item."""

    __tablename__ = "evidence_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    evidence_id: Mapped[str | None] = mapped_column(ForeignKey("evidence.id", ondelete="CASCADE"), nullable=True)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=True)
    actor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    action: Mapped[str] = mapped_column(String(32))  # uploaded|analyzed|linked_to_case|hash_verified|report_exported|deleted|status_changed|note_added|case_event
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    evidence: Mapped[Evidence | None] = orm_relationship(back_populates="events")
    case: Mapped[Case | None] = orm_relationship()


class Person(Base):
    """A person of interest in investigations (victim/suspect/witness/informant)."""

    __tablename__ = "persons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), default="unknown")  # victim|suspect|witness|informant|unknown
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    id_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    id_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    cases: Mapped[list[Case]] = orm_relationship(
        secondary=case_persons, back_populates="persons", lazy="selectin"
    )


class VoicePrint(Base):
    """A voice embedding captured from a person or an evidence clip (for cross-call matching)."""

    __tablename__ = "voice_prints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    label: Mapped[str] = mapped_column(String(200))
    owner_kind: Mapped[str] = mapped_column(String(16))  # person|evidence
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ReportedNumber(Base):
    """Phone-intelligence ledger: numbers reported against and their status."""

    __tablename__ = "reported_numbers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    phone: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="reported")  # reported|verified_fraud|cleared
    count: Mapped[int] = mapped_column(Integer, default=1)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
