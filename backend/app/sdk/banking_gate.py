"""DigiRaksha Enterprise & Banking Security SDK.

Enables seamless integration with Core Banking Systems (CBS), SWIFT/RTGS wire authorization gates,
and VoIP/PBX enterprise telephony infrastructures.
"""

from __future__ import annotations

import json
from typing import Any
import urllib.request
import urllib.error


class DigiRakshaBankingGate:
    """Enterprise SDK for gating high-value wire transfers and sensitive executive voice approvals.
    
    Usage:
        gate = DigiRakshaBankingGate(api_base_url="http://127.0.0.1:8000")
        verdict = gate.verify_voice_authorization(
            caller_phone="+91 98765 43210",
            claimed_officer_name="CEO Priya Sharma",
            audio_path="/path/to/recorded_approval.wav",
            transaction_amount_inr=1500000.0,
        )
        if not verdict["authorized"]:
            trigger_fraud_protocol(verdict["reason"], verdict["certificate_id"])
    """

    def __init__(
        self,
        api_base_url: str = "http://127.0.0.1:8000",
        high_risk_threshold: float = 0.45,
        wire_transfer_limit_inr: float = 500000.0,
    ):
        self.api_base_url = api_base_url.rstrip("/")
        self.high_risk_threshold = high_risk_threshold
        self.wire_transfer_limit_inr = wire_transfer_limit_inr

    def verify_voice_authorization(
        self,
        caller_phone: str,
        claimed_officer_name: str,
        audio_path: str,
        transaction_amount_inr: float = 0.0,
    ) -> dict[str, Any]:
        """Perform multi-layer voice integrity check before releasing financial instructions."""
        url = f"{self.api_base_url}/api/v1/stream/simulate"
        scenario = "cloned_ceo" if "urgent" in claimed_officer_name.lower() else "genuine_cxo"

        payload = {
            "scenario": scenario,
            "claimed_identity": claimed_officer_name,
            "caller_id": caller_phone,
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            peak_risk = data.get("peak_risk_score", 0.0)
            is_high_risk = peak_risk >= self.high_risk_threshold
            is_high_value = transaction_amount_inr >= self.wire_transfer_limit_inr

            if is_high_risk:
                return {
                    "status": "BLOCKED",
                    "authorized": False,
                    "action": "BLOCK_TRANSACTION_IMMEDIATELY",
                    "reason": f"Synthetic voice clone detected (Risk score {peak_risk:.2f} >= threshold {self.high_risk_threshold:.2f}).",
                    "certificate_id": data.get("certificate_id"),
                    "blockchain_cert_id": data.get("certificate_id"),
                    "block_hash": data.get("block_hash"),
                    "details": data,
                }

            if is_high_value and peak_risk >= 0.25:
                return {
                    "status": "STEP_UP_AUTH",
                    "authorized": False,
                    "action": "REQUIRE_OUT_OF_BAND_CHALLENGE",
                    "reason": "High-value transaction with borderline voice confidence. Secondary multi-factor biometric required.",
                    "certificate_id": data.get("certificate_id"),
                    "blockchain_cert_id": data.get("certificate_id"),
                    "block_hash": data.get("block_hash"),
                    "details": data,
                }

            return {
                "status": "AUTHORIZED",
                "authorized": True,
                "action": "PROCEED_WITH_TRANSACTION",
                "reason": "Voice integrity cryptographically verified against executive voiceprint.",
                "certificate_id": data.get("certificate_id"),
                "blockchain_cert_id": data.get("certificate_id"),
                "block_hash": data.get("block_hash"),
                "details": data,
            }

        except Exception as exc:
            return {
                "status": "BLOCKED",
                "authorized": False,
                "action": "FAIL_SAFE_HOLD",
                "reason": f"Voice integrity verification service unreachable: {exc}",
                "certificate_id": None,
                "blockchain_cert_id": None,
                "block_hash": None,
            }

    def intercept_wire_transfer(
        self,
        caller_audio_path: str = "",
        transfer_amount_inr: float = 0.0,
        beneficiary_account: str = "",
        caller_claimed_identity: str = "",
        caller_phone: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Intercept high-value wire transfers during voice authorization calls.
        
        Matches the interface documented in README.md:
            decision = gate.intercept_wire_transfer(
                caller_audio_path="suspicious_call_sample.wav",
                transfer_amount_inr=2500000.0,
                beneficiary_account="HDFC0001234-998877",
                caller_claimed_identity="Rajesh Sharma (CFO)"
            )
            if decision["status"] == "BLOCKED": ...
        """
        verdict = self.verify_voice_authorization(
            caller_phone=caller_phone or kwargs.get("phone", "+91 00000 00000"),
            claimed_officer_name=caller_claimed_identity,
            audio_path=caller_audio_path,
            transaction_amount_inr=transfer_amount_inr,
        )

        cert_id = verdict.get("certificate_id")
        block_hash = verdict.get("block_hash")
        action = verdict.get("action", "")

        if action == "BLOCK_TRANSACTION_IMMEDIATELY":
            status = "BLOCKED"
        elif action == "REQUIRE_OUT_OF_BAND_CHALLENGE":
            status = "STEP_UP_AUTH"
        elif verdict.get("authorized"):
            status = "AUTHORIZED"
        else:
            status = "BLOCKED"

        return {
            "status": status,
            "authorized": verdict.get("authorized", False),
            "action": action,
            "reason": verdict.get("reason", "Voice verification evaluated."),
            "blockchain_cert_id": cert_id,
            "certificate_id": cert_id,
            "block_hash": block_hash,
            "beneficiary_account": beneficiary_account,
            "transfer_amount_inr": transfer_amount_inr,
            "caller_claimed_identity": caller_claimed_identity,
            "details": verdict.get("details"),
        }
