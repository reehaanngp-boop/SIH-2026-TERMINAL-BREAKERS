"""Cross-evidence voice matching (PIN-gated)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.dependencies import require_auth
from app.core.exceptions import ValidationError
from app.db.database import get_db
from app.detectors.audio.audio_utils import load_audio_16k
from app.schemas.police import VoiceMatchResult
from app.services import voice_match_service
from app.services.media import save_upload

router = APIRouter(prefix="/voice-match", tags=["voice-match"])
settings = get_settings()


@router.post("", response_model=VoiceMatchResult, summary="Match an unknown clip against all known voices")
async def voice_match(
    file: UploadFile = File(..., description="Unknown call/clip to identify the speaker on"),
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> VoiceMatchResult:
    path, _, _ = save_upload(file, settings)
    audio = load_audio_16k(str(path))
    result = voice_match_service.match_voice(db, audio)
    if "error" in result:
        raise ValidationError(result["error"])
    return VoiceMatchResult(**result)
