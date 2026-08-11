"""Shared schema types for the DigiRaksha API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RiskLevel = Literal["low", "medium", "high"]
MediaType = Literal["audio", "video", "text"]
SignalStatus = Literal["available", "unavailable", "error"]

HELPLINE_NUMBER = "1930"
REPORT_PORTAL = "https://cybercrime.gov.in"
I4C_SITE = "https://i4c.mha.gov.in"


class LocalizedText(BaseModel):
    """Text available in multiple languages."""

    en: str
    hi: str = ""


class RedFlag(BaseModel):
    """A specific, explainable concern raised by one or more detectors."""

    id: str = Field(..., description="Stable identifier, e.g. 'voice-ai-likely'")
    category: str = Field(..., description="e.g. 'voice', 'video', 'text'")
    severity: Literal["info", "warning", "critical"] = "warning"
    title: LocalizedText
    detail: LocalizedText


class NextStep(BaseModel):
    """An actionable step the user should take."""

    id: str
    kind: Literal["call", "visit", "verify", "report", "generic"]
    title: LocalizedText
    detail: LocalizedText
    href: str | None = None


class RiskVerdict(BaseModel):
    """Overall risk assessment."""

    level: RiskLevel
    score: float = Field(..., ge=0, le=100, description="0-100 risk percentage")
    label: LocalizedText


class DetectorSignal(BaseModel):
    """Result of a single detector module.

    ``label``/``detail`` are short English summaries; user-facing, localised
    explanations live in ``RedFlag``/``NextStep`` objects.
    """

    name: str
    status: SignalStatus
    available: bool = False
    score: float | None = Field(None, ge=0, le=1, description="0-1 likelihood of the fraud signal")
    label: str | None = None
    detail: str | None = None
    metrics: dict = Field(default_factory=dict)
    engine: str | None = Field(None, description="e.g. 'aasist' vs 'heuristics' for voice; 'joblib' for text")


class ReportInfo(BaseModel):
    helpline: str = HELPLINE_NUMBER
    portal: str = REPORT_PORTAL
    i4c: str = I4C_SITE
