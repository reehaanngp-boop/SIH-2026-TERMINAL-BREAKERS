"""Schemas for the Family Safe-Voice Registry API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FamilyMemberCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    relationship: str | None = Field(None, max_length=60)
    phone: str | None = Field(None, max_length=30)
    note: str | None = Field(None, max_length=1000)


class FamilyMemberOut(FamilyMemberCreate):
    id: str
    created_at: str
    enrollments_count: int = 0


class EnrollmentOut(BaseModel):
    enrollment_id: str
    member_id: str
    created_at: str
    duration_seconds: float | None = None


class VerifyRequest(BaseModel):
    """Verify a voice note against a registered family member."""

    member_id: str
    claimed_name: str | None = Field(None, max_length=120)


class VerifyResult(BaseModel):
    member_id: str
    member_name: str
    match: bool
    similarity: float = Field(..., ge=-1, le=1, description="cosine similarity against the best enrolled sample")
    threshold: float
    guidance: dict  # LocalizedText-style guidance per outcome
