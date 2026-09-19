"""Unit tests for Vocoder Analyzer, Blockchain Audit Trail, and Stream API."""

import numpy as np
from fastapi.testclient import TestClient

from app.core.blockchain_ledger import BlockchainAuditLedger
from app.detectors.audio.vocoder_analyzer import VocoderAnalyzer
from app.main import create_app
from app.sdk.banking_gate import DigiRakshaBankingGate


def test_vocoder_analyzer_basic():
    analyzer = VocoderAnalyzer(sample_rate=16000)
    # Generate 1 second of synthetic sinusoidal audio
    t = np.linspace(0, 1.0, 16000, endpoint=False)
    x = 0.5 * np.sin(2 * np.pi * 440 * t).astype(np.float32)

    res = analyzer.analyze_spectral_artifacts(x)
    assert "vocoder_anomaly_score" in res
    assert "phase_inconsistency" in res
    assert "spectral_cutoff_hz" in res
    assert "telephony_mode" in res
    assert 0.0 <= res["vocoder_anomaly_score"] <= 1.0


def test_blockchain_ledger_tamper_proof(tmp_path):
    ledger_file = tmp_path / "test_ledger.json"
    ledger = BlockchainAuditLedger(ledger_file=ledger_file)

    # Check Genesis Block
    assert len(ledger.chain) == 1
    genesis = ledger.chain[0]
    assert genesis["block_index"] == 0
    assert genesis["certificate_id"] == "DR-VOICE-VERIFY-GENESIS"

    # Record Call Verification
    block1 = ledger.record_verification(
        caller_id="+91 99880 12345",
        claimed_identity="CEO Rajesh Nair",
        audio_bytes_or_hash=b"fake-audio-bytes-1",
        risk_score=0.88,
        verdict="CRITICAL_FRAUD_ATTEMPT",
        vocoder_fingerprint="neural_vocoder_hifigan_or_xtts",
    )
    assert len(ledger.chain) == 2
    assert block1["block_index"] == 1
    assert block1["previous_hash"] == genesis["block_hash"]

    # Verify Certificate
    valid, verified_block = ledger.verify_certificate(block1["certificate_id"])
    assert valid is True
    assert verified_block["verdict"] == "CRITICAL_FRAUD_ATTEMPT"

    # Tampering test: modify risk_score and verify failure
    tampered_payload = dict(block1)
    tampered_payload["impersonation_risk_score"] = 0.05
    ledger.chain[1] = tampered_payload
    is_valid, _ = ledger.verify_certificate(block1["certificate_id"])
    assert is_valid is False  # Tampering detected!


def test_api_stream_simulation():
    app = create_app()
    client = TestClient(app)

    # Simulate Cloned CEO Scenario
    res_clone = client.post(
        "/api/v1/stream/simulate",
        json={
            "scenario": "cloned_ceo",
            "claimed_identity": "CEO Priya Sharma",
            "caller_id": "+91 99880 12345",
        },
    )
    assert res_clone.status_code == 200
    data_clone = res_clone.json()
    assert data_clone["scenario"] == "cloned_ceo"
    assert "certificate_id" in data_clone
    assert len(data_clone["timeline"]) > 0

    # Simulate Genuine CXO Scenario
    res_genuine = client.post(
        "/api/v1/stream/simulate",
        json={
            "scenario": "genuine_cxo",
            "claimed_identity": "CFO Rajesh Nair",
            "caller_id": "+91 98200 55443",
        },
    )
    assert res_genuine.status_code == 200
    data_genuine = res_genuine.json()
    assert data_genuine["scenario"] == "genuine_cxo"
    assert data_genuine["overall_verdict"] == "AUTHENTIC_HUMAN"


def test_api_blockchain_endpoints():
    app = create_app()
    client = TestClient(app)

    # Get Stats
    stats_res = client.get("/api/v1/blockchain/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "total_blocks" in stats
    assert stats["chain_integrity"] == "SECURE_VERIFIED"

    # Get Ledger
    ledger_res = client.get("/api/v1/blockchain/ledger")
    assert ledger_res.status_code == 200
    ledger_data = ledger_res.json()
    assert ledger_data["status"] == "success"
    assert len(ledger_data["blocks"]) >= 1


def test_banking_gate_sdk():
    gate = DigiRakshaBankingGate(api_base_url="http://127.0.0.1:8000")
    assert gate.wire_transfer_limit_inr == 500000.0
    assert gate.high_risk_threshold == 0.45

    # Test intercept_wire_transfer with fallback simulation
    decision = gate.intercept_wire_transfer(
        caller_audio_path="test_sample.wav",
        transfer_amount_inr=2500000.0,
        beneficiary_account="HDFC0001234-998877",
        caller_claimed_identity="Rajesh Sharma (CFO)",
    )
    assert "status" in decision
    assert "action" in decision
    assert "reason" in decision
    assert "blockchain_cert_id" in decision
    assert decision["beneficiary_account"] == "HDFC0001234-998877"
    assert decision["transfer_amount_inr"] == 2500000.0

