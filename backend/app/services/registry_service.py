"""Family Safe-Voice Registry: enroll trusted voices and verify unknown ones.

The proactive feature of DigiRaksha: relatives record a short voice sample once.
When an "emergency" voice note arrives claiming to be from a family member, the
app compares it against the registered sample before the user acts on a money
request.

Verification is embedding-cosine similarity (see ``speaker_verify``). Results
are deliberately framed as "matches / does not match + guidance", never as an
absolute authentication, because speaker verification on short clips is not
error-free.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.exceptions import EnrollmentError, MemberNotFoundError
from app.db.models import FamilyMember, VoiceEnrollment
from app.detectors.audio.audio_utils import AudioData
from app.detectors.audio.speaker_verify import (
    best_match,
    compute_embedding,
    embedding_engine,
)
from app.schemas.registry import FamilyMemberCreate

settings = get_settings()


def create_member(db: Session, data: FamilyMemberCreate) -> FamilyMember:
    member = FamilyMember(
        name=data.name.strip(),
        relationship=(data.relationship or "").strip() or None,
        phone=(data.phone or "").strip() or None,
        note=(data.note or "").strip() or None,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def list_members(db: Session) -> list[FamilyMember]:
    return list(db.execute(select(FamilyMember).order_by(FamilyMember.created_at)).scalars())


def get_member(db: Session, member_id: str) -> FamilyMember:
    member = db.get(FamilyMember, member_id)
    if member is None:
        raise MemberNotFoundError(f"Family member {member_id} not found")
    return member


def delete_member(db: Session, member_id: str) -> None:
    member = get_member(db, member_id)
    db.delete(member)
    db.commit()


def enroll_voice(
    db: Session,
    member: FamilyMember,
    audio: AudioData,
    saved_path: str | None = None,
) -> VoiceEnrollment:
    """Compute an embedding for a voice sample and store it for a member."""
    try:
        embedding = compute_embedding(audio)
    except ValueError as exc:
        raise EnrollmentError(f"Could not enrol voice: {exc}") from exc

    enrollment = VoiceEnrollment(
        member_id=member.id,
        file_path=saved_path,
        duration_seconds=round(audio.duration, 2),
        embedding=[float(v) for v in embedding],
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


def verify_voice(
    db: Session,
    member: FamilyMember,
    audio: AudioData,
) -> dict[str, Any]:
    """Compare a voice note against a member's enrolled samples."""
    enrollments = [
        {"embedding": e.embedding}
        for e in member.enrollments
        if e.embedding is not None
    ]
    if not enrollments:
        return {
            "member_id": member.id,
            "member_name": member.name,
            "match": None,
            "similarity": None,
            "threshold": settings.verify_similarity_threshold,
            "engine": embedding_engine(),
            "reason": "no-enrollment",
            "guidance": _guidance("no-enrollment", member.name),
        }

    try:
        probe = compute_embedding(audio)
    except ValueError as exc:
        raise EnrollmentError(f"Could not analyse the voice note: {exc}") from exc

    # Enrollments created under an incompatible engine or legacy dummy format
    # cannot be reliably verified. Filter them out so the user is guided to re-enrol.
    dim = int(len(probe))
    compatible = [
        e for e in enrollments
        if len(e["embedding"]) == dim
        and not (len(e["embedding"]) == 52 and len(set(e["embedding"])) <= 1)
    ]
    if not compatible:
        return {
            "member_id": member.id,
            "member_name": member.name,
            "match": None,
            "similarity": None,
            "threshold": settings.verify_similarity_threshold,
            "engine": embedding_engine(),
            "reason": "incompatible",
            "guidance": _guidance("incompatible", member.name),
        }

    similarity, _ = best_match(probe, compatible)
    match = bool(similarity is not None and similarity >= settings.verify_similarity_threshold)
    return {
        "member_id": member.id,
        "member_name": member.name,
        "match": match,
        "similarity": round(similarity, 4) if similarity is not None else None,
        "threshold": settings.verify_similarity_threshold,
        "engine": embedding_engine(),
        "reason": None,
        "guidance": _guidance("match" if match else "mismatch", member.name),
    }


def member_to_dict(member: FamilyMember) -> dict:
    return {
        "id": member.id,
        "name": member.name,
        "relationship": member.relationship,
        "phone": member.phone,
        "note": member.note,
        "created_at": member.created_at.isoformat(),
        "enrollments_count": len(member.enrollments),
    }


# ---------------------------------------------------------------------------
# Localised guidance
# ---------------------------------------------------------------------------

def _guidance(outcome: str, name: str) -> dict[str, str]:
    if outcome == "match":
        return {
            "en": (
                f"The voice closely matches the registered sample of {name}. Even so, "
                f"still call {name} back on their known phone number before acting on "
                f"any urgent money request."
            ),
            "hi": (
                f"यह आवाज़ {name} के रजिस्टर्ड नमूने से मिलती-जुलती है। फिर भी किसी भी तत्काल "
                f"पैसे की माँग पर कार्रवाई से पहले {name} के जाने-पहचाने नंबर पर कॉल करके पुष्टि करें।"
            ),
        }
    if outcome == "mismatch":
        return {
            "en": (
                f"Warning: this voice does NOT match the registered voice of {name}. "
                f"An urgent money request claiming to be from {name} is highly suspicious — "
                f"verify immediately with {name} on their known number before doing anything."
            ),
            "hi": (
                f"चेतावनी: यह आवाज़ {name} की रजिस्टर्ड आवाज़ से मेल नहीं खाती। {name} की ओर से "
                f"तत्काल पैसे माँगने वाली बात अत्यधिक संदिग्ध है — कुछ भी करने से पहले {name} के "
                f"जाने-पहचाने नंबर पर तुरंत पुष्टि करें।"
            ),
        }
    if outcome == "incompatible":
        return {
            "en": (
                f"{name} has a registered voice sample from an older version of the app. "
                f"Please re-record {name}'s voice sample so it can be verified with the "
                f"new, more accurate speaker model."
            ),
            "hi": (
                f"{name} की रजिस्टर्ड वॉइस ऐप के पुराने संस्करण से है। कृपया {name} की आवाज़ का "
                f"नया नमूना दोबारा रिकॉर्ड करें ताकि इसे नए, अधिक सटीक स्पीकर मॉडल से जांचा जा सके।"
            ),
        }
    return {
        "en": (
            f"No registered voice sample exists for {name} yet. Record one now so future "
            f"voice notes can be verified before you act on money requests."
        ),
        "hi": (
            f"{name} के लिए अभी कोई रजिस्टर्ड वॉइस नमूना नहीं है। अभी एक रिकॉर्ड करें ताकि भविष्य "
            f"में पैसे की माँग से पहले वॉइस नोट का मिलान किया जा सके।"
        ),
    }
