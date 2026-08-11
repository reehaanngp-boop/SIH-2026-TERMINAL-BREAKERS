"""Persons-of-interest endpoints (PIN-gated), incl. voice-print enrolment."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.serializers import build_person_out
from app.config import get_settings
from app.core.dependencies import require_auth
from app.db.database import get_db
from app.detectors.audio.audio_utils import load_audio_16k
from app.schemas.police import (
    LinkPersonRequest,
    PersonCreate,
    PersonOut,
    PersonUpdate,
    VoicePrintCreateResult,
)
from app.services import case_service, person_service
from app.services.media import save_upload

router = APIRouter(prefix="/people", tags=["people"])
settings = get_settings()


@router.get("", response_model=list[PersonOut], summary="List persons (search/filter by role)")
def list_persons(
    search: str = "",
    role: str | None = None,
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> list[PersonOut]:
    return [build_person_out(db, p) for p in person_service.list_persons(db, search=search, role=role)]


@router.post("", response_model=PersonOut, status_code=201, summary="Add a person of interest")
def create_person(
    data: PersonCreate,
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> PersonOut:
    return build_person_out(db, person_service.create_person(db, data))


@router.get("/{person_id}", response_model=PersonOut, summary="Person detail with voice prints")
def get_person(
    person_id: str,
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> PersonOut:
    return build_person_out(db, person_service.get_person(db, person_id))


@router.patch("/{person_id}", response_model=PersonOut, summary="Update a person")
def update_person(
    person_id: str,
    data: PersonUpdate,
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> PersonOut:
    return build_person_out(db, person_service.update_person(db, person_id, data))


@router.delete("/{person_id}", status_code=204, summary="Delete a person")
def delete_person(
    person_id: str,
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> None:
    person_service.delete_person(db, person_id)


@router.post("/{person_id}/enroll-voice", response_model=VoicePrintCreateResult, summary="Enrol a voice sample for the person")
async def enroll_voice(
    person_id: str,
    file: UploadFile = File(..., description="Clean voice sample of the person"),
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> VoicePrintCreateResult:
    person = person_service.get_person(db, person_id)
    path, _, _ = save_upload(file, settings)
    audio = load_audio_16k(str(path))
    print_ = person_service.enroll_voice(db, person, audio, saved_path=str(path))
    return VoicePrintCreateResult(
        voice_print_id=print_.id,
        person_id=person.id,
        label=print_.label,
        duration_seconds=print_.duration_seconds,
        message=f"Voice print stored for {person.name}.",
    )


@router.post("/{person_id}/link", response_model=PersonOut, summary="Link a person to a case")
def link_person(
    person_id: str,
    data: LinkPersonRequest,
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> PersonOut:
    person = person_service.get_person(db, person_id)
    case = case_service.get_case(db, data.case_id)
    person_service.link_to_case(db, person, case)
    return build_person_out(db, person)


@router.delete("/{person_id}/link", response_model=PersonOut, summary="Unlink a person from a case")
def unlink_person(
    person_id: str,
    data: LinkPersonRequest,
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> PersonOut:
    person = person_service.get_person(db, person_id)
    case = case_service.get_case(db, data.case_id)
    person_service.unlink_from_case(db, person, case)
    return build_person_out(db, person)
