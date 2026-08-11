"""Schemas for the police case-solving suite (auth, cases, evidence, people, phones, analytics)."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class AuthStatus(BaseModel):
    setup_required: bool
    authenticated: bool
    officer_name: str | None = None


class SetupRequest(BaseModel):
    officer_name: str = Field(..., min_length=1, max_length=120)
    pin: str = Field(..., min_length=4, max_length=64)


class LoginRequest(BaseModel):
    pin: str = Field(..., min_length=1, max_length=64)


class LoginResult(BaseModel):
    token: str
    officer_name: str
    expires_in_hours: int


class ChangePinRequest(BaseModel):
    current_pin: str = Field(..., min_length=1, max_length=64)
    new_pin: str = Field(..., min_length=4, max_length=64)


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------
class CaseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=5000)
    priority: str = "normal"  # low|normal|high|critical
    officer_name: str | None = Field(None, max_length=120)
    officer_badge: str | None = Field(None, max_length=60)
    victim_name: str | None = Field(None, max_length=120)
    victim_phone: str | None = Field(None, max_length=30)
    suspect_name: str | None = Field(None, max_length=120)
    suspect_phone: str | None = Field(None, max_length=30)
    notes: str | None = Field(None, max_length=5000)
    scan_id: str | None = Field(None, description="Link an existing analysis result as the first evidence")


class CaseUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=5000)
    priority: str | None = None
    officer_name: str | None = None
    officer_badge: str | None = None
    victim_name: str | None = None
    victim_phone: str | None = None
    suspect_name: str | None = None
    suspect_phone: str | None = None
    notes: str | None = None


class CaseStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(open|investigating|closed)$")


class CaseListItem(BaseModel):
    id: str
    case_number: str
    title: str
    status: str
    priority: str
    officer_name: str | None = None
    victim_name: str | None = None
    suspect_name: str | None = None
    evidence_count: int = 0
    person_count: int = 0
    created_at: str


class CaseOut(CaseListItem):
    description: str | None = None
    officer_badge: str | None = None
    victim_phone: str | None = None
    suspect_phone: str | None = None
    notes: str | None = None
    updated_at: str | None = None
    closed_at: str | None = None


class CaseDetailOut(CaseOut):
    evidence: list[EvidenceOut] = []
    persons: list[PersonOut] = []
    events: list[EvidenceEventOut] = []


class NoteRequest(BaseModel):
    note: str = Field(..., min_length=1, max_length=3000)


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------
class EvidenceEventOut(BaseModel):
    id: str
    action: str
    actor: str | None = None
    detail: str | None = None
    created_at: str


class EvidenceOut(BaseModel):
    id: str
    case_id: str | None = None
    case_number: str | None = None
    filename: str
    original_filename: str
    media_type: str | None = None
    size_bytes: int | None = None
    sha256: str
    scan_id: str | None = None
    risk_level: str | None = None
    risk_score: float | None = None
    uploaded_at: str
    uploaded_by: str | None = None
    note: str | None = None
    events: list[EvidenceEventOut] = []


class EvidenceListOut(BaseModel):
    items: list[EvidenceOut]
    total: int


class HashVerifyResult(BaseModel):
    evidence_id: str
    matches: bool
    sha256: str
    message: str


class LinkEvidenceRequest(BaseModel):
    case_id: str


class EvidenceNoteUpdate(BaseModel):
    note: str | None = Field(None, max_length=2000)


# ---------------------------------------------------------------------------
# People / voice prints
# ---------------------------------------------------------------------------
class PersonCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    role: str = "unknown"  # victim|suspect|witness|informant|unknown
    phone: str | None = Field(None, max_length=30)
    id_type: str | None = Field(None, max_length=60)
    id_number: str | None = Field(None, max_length=120)
    address: str | None = Field(None, max_length=1000)
    notes: str | None = Field(None, max_length=3000)
    case_ids: list[str] = []


class PersonUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    phone: str | None = None
    id_type: str | None = None
    id_number: str | None = None
    address: str | None = None
    notes: str | None = None


class VoicePrintOut(BaseModel):
    id: str
    label: str
    owner_kind: str
    owner_id: str
    duration_seconds: float | None = None
    created_at: str


class PersonOut(BaseModel):
    id: str
    name: str
    role: str
    phone: str | None = None
    id_type: str | None = None
    id_number: str | None = None
    address: str | None = None
    notes: str | None = None
    created_at: str
    updated_at: str | None = None
    case_ids: list[str] = []
    voice_prints: list[VoicePrintOut] = []


class LinkPersonRequest(BaseModel):
    case_id: str


class VoicePrintCreateResult(BaseModel):
    voice_print_id: str
    person_id: str
    label: str
    duration_seconds: float | None = None
    message: str


# ---------------------------------------------------------------------------
# Voice matching
# ---------------------------------------------------------------------------
class VoiceMatchItem(BaseModel):
    label: str
    owner_kind: str
    owner_id: str
    owner_ref: str | None = None
    similarity: float
    match: bool


class VoiceMatchResult(BaseModel):
    matches: list[VoiceMatchItem]
    threshold: float
    query_duration_seconds: float | None = None


# ---------------------------------------------------------------------------
# Phone intelligence
# ---------------------------------------------------------------------------
class PhoneRecordOut(BaseModel):
    id: str
    phone: str
    status: str
    count: int
    first_seen: str
    last_seen: str
    notes: str | None = None
    linked_cases: list[str] = []


class PhoneLookupResult(BaseModel):
    found: bool
    record: PhoneRecordOut | None = None
    message: str


class PhoneReportRequest(BaseModel):
    phone: str = Field(..., min_length=5, max_length=30)
    notes: str | None = Field(None, max_length=1000)


class PhoneStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(reported|verified_fraud|cleared)$")


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
class StatCount(BaseModel):
    cases: int
    evidence: int
    scans: int
    reported_numbers: int
    high_risk_7d: int


class CategoryCount(BaseModel):
    category: str
    count: int


class RiskLevelCount(BaseModel):
    level: str
    count: int


class StatusCount(BaseModel):
    status: str
    count: int


class DayCount(BaseModel):
    date: str
    count: int


class AnalyticsStats(BaseModel):
    stats: StatCount
    scam_categories: list[CategoryCount]
    risk_levels: list[RiskLevelCount]
    cases_by_status: list[StatusCount]
    scans_last_14d: list[DayCount]
    recent_high_risk: list[dict]
