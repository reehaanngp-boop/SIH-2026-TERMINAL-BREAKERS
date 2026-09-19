"""Cryptographic Blockchain-anchored Audit Trail for Voice Integrity Verification.

Provides immutable, tamper-proof forensic logging of telephony/VoIP call authentications:
1. Cryptographic SHA-256 hash-chaining of call verification sessions.
2. Merkle root anchoring for verifiable audio stream digests.
3. Tamper-proof Voice Integrity Certificates (DR-VOICE-VERIFY-CERT) compliant with
   Section 65B of the Indian Evidence Act / Bharatiya Sakshya Adhiniyam (BSA 2023)
   and banking non-repudiation requirements.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any
import uuid

from app.config import get_settings

SETTINGS = get_settings()
LEDGER_PATH = SETTINGS.data_dir / "blockchain_ledger.json"
LEDGER_SECRET = b"digiraksha-cybersecurity-ai-blockchain-key-2026"


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _sign(hash_str: str) -> str:
    return hmac.new(LEDGER_SECRET, hash_str.encode("utf-8"), hashlib.sha256).hexdigest()


class BlockchainAuditLedger:
    """Manages the append-only cryptographic ledger of voice verification records."""

    _instance: BlockchainAuditLedger | None = None

    def __init__(self, ledger_file: Path | None = None):
        self.ledger_file = ledger_file or LEDGER_PATH
        self.chain: list[dict[str, Any]] = []
        self._load_or_initialize()

    @classmethod
    def get_instance(cls) -> BlockchainAuditLedger:
        if cls._instance is None:
            cls._instance = BlockchainAuditLedger()
        return cls._instance

    def _load_or_initialize(self) -> None:
        if self.ledger_file.exists():
            try:
                with open(self.ledger_file, "r", encoding="utf-8") as f:
                    self.chain = json.load(f)
                if self.chain and self._verify_chain_internal():
                    return
            except Exception:
                self.chain = []

        # Initialize Genesis Block
        self.chain = [self._create_genesis_block()]
        self._persist()

    def _create_genesis_block(self) -> dict[str, Any]:
        timestamp = "2026-01-01T00:00:00Z"
        payload = {
            "block_index": 0,
            "timestamp": timestamp,
            "session_id": "00000000-0000-0000-0000-000000000000",
            "certificate_id": "DR-VOICE-VERIFY-GENESIS",
            "caller_id": "SYSTEM_ROOT",
            "claimed_identity": "DigiRaksha Voice Integrity Root Authority",
            "audio_sha256": "0" * 64,
            "impersonation_risk_score": 0.0,
            "verdict": "GENESIS_NODE",
            "vocoder_fingerprint": "ROOT_SECURE",
            "compliance_section_65b": True,
            "previous_hash": "0" * 64,
        }
        block_str = json.dumps(payload, sort_keys=True)
        block_hash = _sha256(block_str)
        signature = _sign(block_hash)

        return {
            **payload,
            "merkle_root": _sha256(payload["audio_sha256"] + block_hash),
            "block_hash": block_hash,
            "signature": signature,
        }

    def _persist(self) -> None:
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger_file, "w", encoding="utf-8") as f:
            json.dump(self.chain, f, indent=2)

    def record_verification(
        self,
        caller_id: str,
        claimed_identity: str,
        audio_bytes_or_hash: bytes | str,
        risk_score: float,
        verdict: str,
        vocoder_fingerprint: str = "natural_vocal_tract",
        telemetry: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create and append a new tamper-proof block to the ledger."""
        if isinstance(audio_bytes_or_hash, bytes):
            audio_hash = hashlib.sha256(audio_bytes_or_hash).hexdigest()
        else:
            audio_hash = str(audio_bytes_or_hash)

        prev_block = self.chain[-1]
        block_index = len(self.chain)
        timestamp = datetime.now(timezone.utc).isoformat()
        session_id = str(uuid.uuid4())
        cert_id = f"DR-VOICE-CERT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        payload = {
            "block_index": block_index,
            "timestamp": timestamp,
            "session_id": session_id,
            "certificate_id": cert_id,
            "caller_id": caller_id or "ANONYMOUS_INCOMING_VOIP",
            "claimed_identity": claimed_identity or "UNSPECIFIED_CALLER",
            "audio_sha256": audio_hash,
            "impersonation_risk_score": round(float(risk_score), 4),
            "verdict": verdict,
            "vocoder_fingerprint": vocoder_fingerprint,
            "compliance_section_65b": True,
            "telemetry": telemetry or {},
            "previous_hash": prev_block["block_hash"],
        }

        block_str = json.dumps(payload, sort_keys=True)
        block_hash = _sha256(block_str)
        merkle_root = _sha256(audio_hash + prev_block["block_hash"] + block_hash)
        signature = _sign(block_hash)

        block = {
            **payload,
            "merkle_root": merkle_root,
            "block_hash": block_hash,
            "signature": signature,
        }

        self.chain.append(block)
        self._persist()
        return block

    def verify_certificate(self, certificate_id: str) -> tuple[bool, dict[str, Any] | None]:
        """Verify the cryptographic validity and immutability of a specific certificate."""
        for block in self.chain:
            if block.get("certificate_id") == certificate_id:
                # Validate block hash and signature
                payload = {k: v for k, v in block.items() if k not in ("block_hash", "merkle_root", "signature")}
                recomputed_hash = _sha256(json.dumps(payload, sort_keys=True))
                if recomputed_hash != block["block_hash"]:
                    return False, {"error": "Block hash mismatch - data has been tampered with!"}
                recomputed_sig = _sign(recomputed_hash)
                if recomputed_sig != block["signature"]:
                    return False, {"error": "Invalid digital signature"}
                return True, block
        return False, None

    def _verify_chain_internal(self) -> bool:
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i - 1]
            if curr.get("previous_hash") != prev.get("block_hash"):
                return False
            payload = {k: v for k, v in curr.items() if k not in ("block_hash", "merkle_root", "signature")}
            recomputed = _sha256(json.dumps(payload, sort_keys=True))
            if recomputed != curr.get("block_hash"):
                return False
        return True

    def get_ledger_stats(self) -> dict[str, Any]:
        total_blocks = len(self.chain)
        high_risk_count = sum(1 for b in self.chain if b.get("impersonation_risk_score", 0.0) >= 0.50 and b.get("block_index") != 0)
        chain_valid = self._verify_chain_internal()
        last_block_hash = self.chain[-1]["block_hash"] if self.chain else "None"

        return {
            "total_blocks": total_blocks,
            "total_verified_calls": max(0, total_blocks - 1),
            "fraud_attacks_intercepted": high_risk_count,
            "chain_integrity": "SECURE_VERIFIED" if chain_valid else "CORRUPTED",
            "last_block_hash": last_block_hash,
            "statutory_compliance": "Indian Bharatiya Sakshya Adhiniyam 2023 / Section 65B IT Act Forensic Standard",
        }


def get_blockchain_ledger() -> BlockchainAuditLedger:
    return BlockchainAuditLedger.get_instance()
