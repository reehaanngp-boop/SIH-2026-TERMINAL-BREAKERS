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
    similarity: float = Field(..., ge=-1, le=1, description="best cosine similarity against the claimed member's enrolled samples")
    threshold: float
    separation: float | None = Field(None, description="best_similarity minus mean similarity against other enrolled speakers")
    cohort_mean_similarity: float | None = None
    confidence: float | None = Field(None, ge=0, le=1)
    confidence_level: str | None = None
    samples_compared: int | None = None
    engine: str | None = None
    reason: str | None = None
    guidance: dict  # LocalizedText-style guidance per outcome
