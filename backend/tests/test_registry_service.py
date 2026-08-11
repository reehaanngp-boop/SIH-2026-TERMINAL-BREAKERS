"""Tests for the Family Safe-Voice Registry service (embedding based)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import EnrollmentError, MemberNotFoundError
from app.detectors.audio.audio_utils import load_audio_16k
from app.schemas.registry import FamilyMemberCreate
from app.services import registry_service


@pytest.fixture()
def db():
    from app.db.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_create_and_list_member(db):
    member = registry_service.create_member(
        db, FamilyMemberCreate(name="Priya", relationship="Mother", phone="9999999999")
    )
    assert member.id
    assert member.name == "Priya"
    names = [m.name for m in registry_service.list_members(db)]
    assert "Priya" in names


def test_get_missing_member_raises(db):
    with pytest.raises(MemberNotFoundError):
        registry_service.get_member(db, "does-not-exist")


def test_delete_member(db):
    member = registry_service.create_member(db, FamilyMemberCreate(name="Raj"))
    registry_service.delete_member(db, member.id)
    with pytest.raises(MemberNotFoundError):
        registry_service.get_member(db, member.id)


def test_enroll_and_verify_match(db, wav_path: Path):
    member = registry_service.create_member(db, FamilyMemberCreate(name="Anjali"))
    audio = load_audio_16k(str(wav_path))
    registry_service.enroll_voice(db, member, audio, saved_path=str(wav_path))

    # Same file -> same embedding -> high similarity.
    result = registry_service.verify_voice(db, member, load_audio_16k(str(wav_path)))
    assert result["match"] is True
    assert result["similarity"] is not None and result["similarity"] > 0.5
    assert "en" in result["guidance"]


def test_verify_mismatch(db, wav_path: Path, noise_path: Path):
    member = registry_service.create_member(db, FamilyMemberCreate(name="Vikram"))
    registry_service.enroll_voice(
        db, member, load_audio_16k(str(wav_path)), saved_path=str(wav_path)
    )

    # White noise is a completely different 'voice' -> mismatch.
    result = registry_service.verify_voice(db, member, load_audio_16k(str(noise_path)))
    assert result["match"] is False


def test_verify_reports_engine(db, wav_path: Path):
    member = registry_service.create_member(db, FamilyMemberCreate(name="Engine"))
    audio = load_audio_16k(str(wav_path))
    registry_service.enroll_voice(db, member, audio, saved_path=str(wav_path))
    result = registry_service.verify_voice(db, member, audio)
    assert result["engine"] in ("ecapa", "mfcc")
    assert result["reason"] is None


def test_verify_incompatible_old_embedding(db, wav_path: Path):
    """A member enrolled under the old 52-D engine must be told to re-enrol,
    never silently compared against a 192-D probe."""
    member = registry_service.create_member(db, FamilyMemberCreate(name="Old"))
    audio = load_audio_16k(str(wav_path))
    registry_service.enroll_voice(db, member, audio, saved_path=str(wav_path))
    # Force the stored embedding to the old 52-D shape, simulating a pre-upgrade row.
    for enrollment in member.enrollments:
        enrollment.embedding = [0.01] * 52
    db.commit()

    result = registry_service.verify_voice(db, member, audio)
    assert result["match"] is None
    assert result["reason"] == "incompatible"
    assert "re-record" in result["guidance"]["en"]


def test_verify_without_enrollment_returns_none(db, wav_path: Path):
    member = registry_service.create_member(db, FamilyMemberCreate(name="Meena"))
    result = registry_service.verify_voice(db, member, load_audio_16k(str(wav_path)))
    assert result["match"] is None
    assert "en" in result["guidance"]


def test_enroll_too_short_raises(db, tmp_path: Path):
    import numpy as np
    import soundfile as sf

    member = registry_service.create_member(db, FamilyMemberCreate(name="Short"))
    # 0.05 s of audio is too short for a reliable embedding.
    tiny = np.zeros(16000 // 20, dtype=np.float32)
    path = tmp_path / "tiny.wav"
    sf.write(path, tiny, 16000, subtype="PCM_16")
    with pytest.raises(EnrollmentError):
        registry_service.enroll_voice(db, member, load_audio_16k(str(path)))
