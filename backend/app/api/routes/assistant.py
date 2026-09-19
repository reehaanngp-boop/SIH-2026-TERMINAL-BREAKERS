"""AI Assistant & Cyber Copilot API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Case, Scan
from app.services.llm_analysis import (
    chat_with_copilot,
    draft_complaint_ai,
    llm_model,
    llm_ready,
    quick_triage_ai,
)

router = APIRouter(prefix="/assistant", tags=["assistant"])


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' | 'assistant' | 'system'")
    content: str = Field(..., description="Message text")


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1)
    scan_id: str | None = Field(None, description="Optional scan ID to provide scan context to the AI")
    case_id: str | None = Field(None, description="Optional police case ID to provide case context")
    model: str | None = Field(None, description="Optional OpenRouter model override")


class ChatResponse(BaseModel):
    status: str
    model: str
    reply: str
    suggestions: list[str] = []
    error: str | None = None


class QuickCheckRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class DraftComplaintRequest(BaseModel):
    victim_name: str = "Citizen Complainant"
    suspect_phone: str | None = None
    suspect_upi: str | None = None
    scam_type: str = "Digital Arrest / Cyber Impersonation Scam"
    amount_lost: str | None = "0"
    date_time: str | None = None
    transcript: str | None = None
    scan_id: str | None = None


@router.get("/status", summary="Probe AI assistant status and model availability")
def assistant_status(x_openrouter_key: str | None = Header(None)) -> dict[str, Any]:
    ready, reason = llm_ready(api_key=x_openrouter_key)
    return {
        "available": ready,
        "active_model": llm_model(),
        "reason": reason if not ready else "OpenRouter AI Assistant ready",
    }


@router.post("/chat", response_model=ChatResponse, summary="Chat with DigiRaksha AI Copilot")
def assistant_chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    x_openrouter_key: str | None = Header(None),
) -> ChatResponse:
    scan_context: dict[str, Any] = {}

    if req.scan_id:
        scan = db.get(Scan, req.scan_id)
        if scan and scan.result_json:
            scan_context = scan.result_json

    if req.case_id:
        case = db.get(Case, req.case_id)
        if case:
            scan_context["case"] = {
                "case_number": case.case_number,
                "title": case.title,
                "complainant": case.complainant_name,
                "status": case.status,
                "notes": case.notes,
            }

    res = chat_with_copilot(
        [m.model_dump() for m in req.messages],
        scan_context=scan_context if scan_context else None,
        model=req.model,
        api_key=x_openrouter_key,
    )
    return ChatResponse(
        status=res.get("status", "ok"),
        model=res.get("model", llm_model()),
        reply=res.get("reply", ""),
        suggestions=res.get("suggestions", []),
        error=res.get("error"),
    )


@router.post("/quick-check", summary="Fast triage of suspicious text/SMS/WhatsApp message")
def assistant_quick_check(
    req: QuickCheckRequest,
    x_openrouter_key: str | None = Header(None),
) -> dict[str, Any]:
    return quick_triage_ai(req.text, api_key=x_openrouter_key)


@router.post("/draft-fir", summary="Generate a ready-to-file Cyber Crime Complaint for 1930 / FIR")
def assistant_draft_fir(
    req: DraftComplaintRequest,
    db: Session = Depends(get_db),
    x_openrouter_key: str | None = Header(None),
) -> dict[str, Any]:
    data = req.model_dump()
    if req.scan_id:
        scan = db.get(Scan, req.scan_id)
        if scan:
            data["transcript"] = scan.transcript
            data["risk_level"] = scan.risk_level
            data["risk_score"] = scan.risk_score

    return draft_complaint_ai(data, api_key=x_openrouter_key)
