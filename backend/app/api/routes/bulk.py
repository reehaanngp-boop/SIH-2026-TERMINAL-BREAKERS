"""Batch analysis endpoint (PIN-gated): upload multiple clips at once."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.routes.analyze import _run_scan
from app.config import get_settings
from app.core.dependencies import require_auth
from app.core.jobs import get_job_manager
from app.db.database import get_db
from app.db.models import Scan
from app.services.media import save_upload

router = APIRouter(prefix="/analyze", tags=["analyze"])
settings = get_settings()


@router.post("/bulk", summary="Analyse multiple files (returns one job id per file)")
async def bulk_analyze(
    files: list[UploadFile] = File(..., description="Audio/video clips to analyse"),
    _: str | None = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    if not files:
        return {"jobs": []}
    if len(files) > 20:
        from app.core.exceptions import ValidationError

        raise ValidationError("Batch is limited to 20 files at a time.")

    job_manager = get_job_manager()
    jobs = []
    for file in files:
        path, media_type, original = save_upload(file, settings)
        scan = Scan(status="queued", media_type=media_type, original_filename=original, file_path=str(path))
        db.add(scan)
        db.commit()
        db.refresh(scan)
        job_id = job_manager.submit(
            lambda progress, _scan_id=scan.id, _mt=media_type, _p=str(path), _orig=original: _run_scan(
                _scan_id, _mt, _p, _orig, progress
            ),
            description="bulk media analysis",
        )
        jobs.append({"job_id": job_id, "scan_id": scan.id, "filename": original})
    return {"jobs": jobs}
