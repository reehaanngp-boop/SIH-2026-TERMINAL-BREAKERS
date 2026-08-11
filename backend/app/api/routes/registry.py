"""Family Safe-Voice Registry endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.exceptions import ValidationError
from app.db.database import get_db
from app.detectors.audio.audio_utils import load_audio_16k
from app.schemas.registry import (
    EnrollmentOut,
    FamilyMemberCreate,
    FamilyMemberOut,
    VerifyResult,
)
from app.services import registry_service
from app.services.media import save_upload

router = APIRouter(prefix="/registry", tags=["registry"])
settings = get_settings()


@router.post("/members", response_model=FamilyMemberOut, summary="Register a trusted family member")
def create_member(data: FamilyMemberCreate, db: Session = Depends(get_db)) -> FamilyMemberOut:
    member = registry_service.create_member(db, data)
    return _to_out(member)


@router.get("/members", response_model=list[FamilyMemberOut], summary="List registered family members")
def list_members(db: Session = Depends(get_db)) -> list[FamilyMemberOut]:
    return [_to_out(m) for m in registry_service.list_members(db)]


@router.delete("/members/{member_id}", status_code=204, summary="Remove a family member and their voices")
def delete_member(member_id: str, db: Session = Depends(get_db)) -> None:
    registry_service.delete_member(db, member_id)


@router.post(
    "/members/{member_id}/enroll",
    response_model=EnrollmentOut,
    summary="Enrol a voice sample for a family member",
)
async def enroll(
    member_id: str,
    file: UploadFile = File(..., description="Voice sample (recording or voice note)"),
    db: Session = Depends(get_db),
) -> EnrollmentOut:
    path, _, _ = save_upload(file, settings)
    member = registry_service.get_member(db, member_id)
    audio = load_audio_16k(str(path))
    enrollment = registry_service.enroll_voice(db, member, audio, saved_path=str(path))
    return EnrollmentOut(
        enrollment_id=enrollment.id,
        member_id=member.id,
        created_at=enrollment.created_at.isoformat(),
        duration_seconds=enrollment.duration_seconds,
    )


@router.post("/verify", response_model=VerifyResult, summary="Verify a voice note against a family member")
async def verify(
    member_id: str = Form(...),
    file: UploadFile = File(..., description="The suspicious voice note to verify"),
    db: Session = Depends(get_db),
) -> VerifyResult:
    path, _, _ = save_upload(file, settings)
    member = registry_service.get_member(db, member_id)
    audio = load_audio_16k(str(path))
    result: dict[str, Any] = registry_service.verify_voice(db, member, audio)
    if result.get("match") is None:
        if result.get("reason") == "incompatible":
            raise ValidationError(
                "This member's voice was enrolled with an older speaker model. "
                "Re-enrol the voice sample to verify with the new model.",
                status_code=409,
                code="re_enroll_required",
            )
        raise ValidationError(
            "This member has no enrolled voice samples yet. Enrol one before verifying.",
            status_code=400,
            code="no_enrollment",
        )
    return VerifyResult(
        member_id=result["member_id"],
        member_name=result["member_name"],
        match=result["match"],
        similarity=result["similarity"] if result["similarity"] is not None else 0.0,
        threshold=result["threshold"],
        guidance=result["guidance"],
    )


def _to_out(member) -> FamilyMemberOut:
    return FamilyMemberOut(
        id=member.id,
        name=member.name,
        relationship=member.relationship,
        phone=member.phone,
        note=member.note,
        created_at=member.created_at.isoformat(),
        enrollments_count=len(member.enrollments),
    )
