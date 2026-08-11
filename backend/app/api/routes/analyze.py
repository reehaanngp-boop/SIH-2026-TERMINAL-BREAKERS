"""Media & transcript analysis endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.exceptions import JobNotFoundError
from app.core.jobs import get_job_manager
from app.db.database import SessionLocal, get_db
from app.db.models import Scan
from app.schemas.analyze import (
    AnalysisResult,
    AnalyzeRequest,
    JobCreated,
    ScanListItem,
)
from app.schemas.common import DetectorSignal, NextStep, RedFlag, RiskVerdict
from app.services.media import save_upload
from app.services.pipeline import get_pipeline

router = APIRouter(prefix="/analyze", tags=["analyze"])
settings = get_settings()


def _utcnow():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


def build_result_model(result: dict, scan_id: str) -> AnalysisResult:
    """Validate + shape a pipeline result dict into the API response model."""
    media = result.get("media") or {}
    return AnalysisResult(
        scan_id=scan_id,
        status="completed",
        media_type=media.get("media_type", "audio"),
        original_filename=media.get("original_filename"),
        duration_seconds=media.get("duration_seconds"),
        language=result.get("language"),
        transcript=result.get("transcript"),
        risk=RiskVerdict(**result["risk"]),
        signals={k: DetectorSignal(**v) for k, v in result["signals"].items()},
        red_flags=[RedFlag(**rf) for rf in result.get("red_flags", [])],
        next_steps=[NextStep(**ns) for ns in result.get("next_steps", [])],
        ai_analysis=result.get("ai_analysis"),
    )


@router.post("/transcript", response_model=AnalysisResult, summary="Analyse a raw transcript")
def analyze_transcript(req: AnalyzeRequest, db: Session = Depends(get_db)) -> AnalysisResult:
    pipeline = get_pipeline()
    result = pipeline.analyze_transcript(req.text, req.language_hint)

    scan = Scan(
        status="completed",
        media_type="text",
        original_filename=None,
        transcript=req.text,
        risk_level=result["risk"]["level"],
        risk_score=result["risk"]["score"],
        result_json=result,
        finished_at=None,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return build_result_model(result, scan.id)


@router.post("", response_model=JobCreated, summary="Upload a call recording/clip for analysis")
async def analyze_upload(
    file: UploadFile = File(..., description="Audio or video clip (WhatsApp/Telegram/recording)"),
    db: Session = Depends(get_db),
) -> JobCreated:
    path, media_type, original = save_upload(file, settings)

    scan = Scan(status="queued", media_type=media_type, original_filename=original, file_path=str(path))
    db.add(scan)
    db.commit()
    db.refresh(scan)

    job_manager = get_job_manager()
    job_id = job_manager.submit(
        lambda progress: _run_scan(scan.id, media_type, str(path), original, progress),
        description="media analysis",
    )
    return JobCreated(job_id=job_id, status="queued", detail="Analysis started.")


def _run_scan(scan_id: str, media_type: str, path: str, original: str, progress: Any) -> dict:
    db = SessionLocal()
    try:
        scan = db.get(Scan, scan_id)
        scan.status = "running"
        scan.started_at = _utcnow()
        db.commit()

        pipeline = get_pipeline()
        result = pipeline.analyze_media(media_type, path, original, on_progress=progress)

        scan.status = "completed"
        scan.finished_at = _utcnow()
        scan.result_json = result
        scan.risk_level = result["risk"]["level"]
        scan.risk_score = result["risk"]["score"]
        scan.transcript = result.get("transcript")
        scan.language = result.get("language")
        scan.duration_seconds = (result.get("media") or {}).get("duration_seconds")
        db.commit()
        return {"scan_id": scan_id, "result": result}
    except Exception:
        scan = db.get(Scan, scan_id)
        scan.status = "failed"
        scan.error = _current_exc()
        db.commit()
        raise
    finally:
        db.close()


def _current_exc() -> str:
    import traceback

    return traceback.format_exc(limit=3)


@router.get("/jobs/{job_id}", summary="Poll an analysis job")
def job_status(job_id: str) -> dict[str, Any]:
    job = get_job_manager().get(job_id)
    if job is None:
        raise JobNotFoundError(f"Job {job_id} not found")
    snap = job.snapshot()
    if snap["status"] == "completed":
        payload = job.result  # {"scan_id":..., "result": {...}}
        return {
            "job_id": job_id,
            "status": "completed",
            "progress": 1.0,
            "result": build_result_model(payload["result"], payload["scan_id"]),
        }
    if snap["status"] == "failed":
        return {"job_id": job_id, "status": "failed", "progress": 1.0, "message": "Analysis failed", "error": snap["error"]}
    return {"job_id": job_id, "status": snap["status"], "progress": snap["progress"], "message": snap["message"]}


@router.get("/results/{scan_id}", response_model=AnalysisResult, summary="Fetch a completed analysis by scan id")
def get_result(scan_id: str, db: Session = Depends(get_db)) -> AnalysisResult:
    from app.core.exceptions import ValidationError

    scan = db.get(Scan, scan_id)
    if scan is None or not scan.result_json:
        raise ValidationError("Result not found or scan not completed", status_code=404)
    result = scan.result_json
    result.setdefault("media", {"media_type": scan.media_type, "original_filename": scan.original_filename})
    return build_result_model(result, scan.id)


@router.get("/history", response_model=list[ScanListItem], summary="Recent scan history")
def scan_history(db: Session = Depends(get_db), limit: int = 50) -> list[ScanListItem]:
    scans = db.execute(select(Scan).order_by(Scan.created_at.desc()).limit(max(1, min(limit, 200)))).scalars()
    return [
        ScanListItem(
            scan_id=s.id,
            created_at=s.created_at.isoformat() if s.created_at else "",
            status=s.status,
            media_type=s.media_type,
            original_filename=s.original_filename,
            risk_level=s.risk_level,
            risk_score=s.risk_score,
            language=s.language,
        )
        for s in scans
    ]
