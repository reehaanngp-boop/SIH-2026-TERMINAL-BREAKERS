"""Schemas for the media-analysis API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import (
    DetectorSignal,
    LocalizedText,
    MediaType,
    NextStep,
    RedFlag,
    ReportInfo,
    RiskVerdict,
)


class AnalyzeRequest(BaseModel):
    """Analyse a raw transcript directly (no media file)."""

    text: str = Field(..., min_length=1, max_length=20000, description="The call transcript to analyse")
    language_hint: str | None = Field(
        None, description="Optional ISO-639-1 language hint for classification, e.g. 'en', 'hi'"
    )


class JobCreated(BaseModel):
    job_id: str
    status: str = "queued"
    detail: str | None = None


class JobStatus(BaseModel):
    job_id: str
    status: str  # queued|running|completed|failed
    progress: float = Field(0.0, ge=0, le=1)
    message: str | None = None


class AiVerdict(BaseModel):
    """Structured verdict from the OpenRouter LLM second opinion."""

    is_scam: bool
    confidence: float = 0.0
    scam_category: str | None = None
    key_indicators: list[str] = []
    explanation: LocalizedText | None = None


class AiAnalysis(BaseModel):
    """AI analysis block attached to a result (null when AI is unavailable)."""

    status: str  # ok | unavailable
    model: str | None = None
    error: str | None = None
    verdict: AiVerdict | None = None


class AnalysisResult(BaseModel):
    """Full result of a completed analysis."""

    scan_id: str
    status: str
    media_type: MediaType
    original_filename: str | None = None
    duration_seconds: float | None = None
    language: str | None = None
    transcript: str | None = None
    risk: RiskVerdict
    signals: dict[str, DetectorSignal]
    red_flags: list[RedFlag] = []
    next_steps: list[NextStep] = []
    report: ReportInfo = ReportInfo()
    ai_analysis: AiAnalysis | None = None


class ScanListItem(BaseModel):
    scan_id: str
    created_at: str
    status: str
    media_type: MediaType
    original_filename: str | None = None
    risk_level: str | None = None
    risk_score: float | None = None
    language: str | None = None
