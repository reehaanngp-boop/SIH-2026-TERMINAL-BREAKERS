"""Upload handling: validation, media-type detection and safe storage."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import Settings
from app.core.exceptions import UnsupportedMediaError, ValidationError

AUDIO_EXTENSIONS = {
    ".wav", ".mp3", ".m4a", ".aac", ".ogg", ".oga", ".flac", ".opus", ".amr", ".wma", ".caf", ".mka",
}
VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".webm", ".mov", ".avi", ".3gp", ".3g2", ".m4v", ".ts", ".wmv",
}
ALL_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS

MAX_READ_CHUNK = 1 << 20  # 1 MiB


def detect_media_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    raise UnsupportedMediaError(
        f"Unsupported file type '{ext or '(none)'}'. Supported: audio "
        f"({', '.join(sorted(AUDIO_EXTENSIONS))}) and video "
        f"({', '.join(sorted(VIDEO_EXTENSIONS))})."
    )


def save_upload(upload: UploadFile, settings: Settings) -> tuple[Path, str, str]:
    """Stream an upload to disk with size validation.

    Returns ``(path, media_type, original_filename)``.
    """
    original = upload.filename or "upload"
    media_type = detect_media_type(original)
    ext = Path(original).suffix.lower()

    max_bytes = settings.max_upload_mb * 1024 * 1024
    dest = settings.upload_dir / f"{uuid.uuid4().hex}{ext}"

    total = 0
    with dest.open("wb") as out:
        while True:
            chunk = upload.file.read(MAX_READ_CHUNK)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                dest.unlink(missing_ok=True)
                raise ValidationError(
                    f"File too large: {total / 1e6:.1f} MB exceeds the {settings.max_upload_mb} MB limit."
                )
            out.write(chunk)

    if total == 0:
        dest.unlink(missing_ok=True)
        raise ValidationError("Uploaded file is empty.")

    return dest, media_type, original
