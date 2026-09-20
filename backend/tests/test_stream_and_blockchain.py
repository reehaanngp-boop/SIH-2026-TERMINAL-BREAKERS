"""Unit tests for Vocoder Analyzer, Blockchain Audit Trail, and Stream API."""

import numpy as np
from fastapi.testclient import TestClient

from app.core.blockchain_ledger import BlockchainAuditLedger
from app.detectors.audio.vocoder_analyzer import VocoderAnalyzer
from app.main import create_app


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


def test_api_stream_testing_endpoints_removed():
    """Threat-simulation and benchmark sample endpoints were removed.

    Unknown paths fall through to the SPA catch-all, so removal is asserted
    via method/status and content-type rather than a clean 404.
    """
    app = create_app()
    client = TestClient(app)

    res_simulate = client.post(
        "/api/v1/stream/simulate",
        json={"scenario": "cloned_ceo"},
    )
    assert res_simulate.status_code in (404, 405)

    res_audio = client.get("/api/v1/stream/scenario-audio/cloned_ceo")
    assert res_audio.headers.get("content-type", "") != "audio/wav"

    res_sample = client.get("/api/v1/stream/sample-file/ai_generated_voice.wav")
    assert res_sample.headers.get("content-type", "") != "audio/wav"


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

