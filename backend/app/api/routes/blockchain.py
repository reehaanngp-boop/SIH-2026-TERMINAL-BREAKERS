"""Blockchain Audit Trail and Certificate Verification API."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.blockchain_ledger import get_blockchain_ledger

router = APIRouter(prefix="/blockchain", tags=["blockchain"])


class RecordBlockRequest(BaseModel):
    caller_id: str = Field(..., description="Phone number or VoIP SIP URI")
    claimed_identity: str = Field(..., description="Purported identity, e.g. 'CEO Priya Sharma'")
    risk_score: float = Field(..., ge=0.0, le=1.0)
    verdict: str = Field(..., description="'AUTHENTIC_HUMAN', 'SUSPECTED_VOICE_CLONE', etc.")
    vocoder_fingerprint: str = Field("natural_vocal_tract")
    audio_hash: str | None = None
    telemetry: dict[str, Any] | None = None


@router.get("/ledger", summary="Get the complete immutable blockchain audit trail")
def get_ledger(limit: int = 50) -> dict[str, Any]:
    ledger = get_blockchain_ledger()
    # Return in reverse chronological order (newest first)
    blocks = ledger.chain[::-1][:limit]
    return {
        "status": "success",
        "count": len(blocks),
        "total_in_chain": len(ledger.chain),
        "blocks": blocks,
    }


@router.get("/stats", summary="Get blockchain statistics and integrity status")
def get_stats() -> dict[str, Any]:
    ledger = get_blockchain_ledger()
    return ledger.get_ledger_stats()


@router.get("/verify/{certificate_id}", summary="Cryptographically verify a Voice Integrity Certificate")
def verify_certificate(certificate_id: str) -> dict[str, Any]:
    ledger = get_blockchain_ledger()
    valid, block = ledger.verify_certificate(certificate_id)
    if not block:
        raise HTTPException(status_code=404, detail=f"Certificate '{certificate_id}' not found in blockchain ledger.")
    if not valid:
        raise HTTPException(status_code=400, detail="Certificate integrity compromised! Tampering detected.")

    return {
        "valid": True,
        "certificate_id": certificate_id,
        "status": "CRYPTOGRAPHICALLY_VERIFIED_TAMPER_PROOF",
        "block": block,
    }


@router.post("/record", summary="Manually log a verified call session to the blockchain ledger")
def record_block(req: RecordBlockRequest) -> dict[str, Any]:
    ledger = get_blockchain_ledger()
    audio_digest = req.audio_hash or ("dummy-" + str(req.risk_score))
    block = ledger.record_verification(
        caller_id=req.caller_id,
        claimed_identity=req.claimed_identity,
        audio_bytes_or_hash=audio_digest,
        risk_score=req.risk_score,
        verdict=req.verdict,
        vocoder_fingerprint=req.vocoder_fingerprint,
        telemetry=req.telemetry,
    )
    return {
        "status": "recorded",
        "block": block,
    }
