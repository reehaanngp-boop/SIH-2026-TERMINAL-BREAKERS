"""Real-time live call stream WebSocket endpoint and telephony simulation."""

from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
import numpy as np
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import get_settings
from app.core.blockchain_ledger import get_blockchain_ledger
from app.detectors.audio.voice_spoof import VoiceSpoofDetector
from app.detectors.audio.speaker_verify import compute_embedding, cosine_similarity
from app.detectors.audio.audio_utils import AudioData, load_audio_16k

router = APIRouter(prefix="/stream", tags=["stream"])
SETTINGS = get_settings()

COERCIVE_KEYWORDS = [
    "transfer", "wire", "money", "urgent", "immediately", "neft", "rtgs",
    "digital arrest", "police", "customs", "cbi", "arrest", "court",
    "seizure", "narcotics", "otp", "password", "bank", "account",
    "override", "protocol", "confidential", "secret", "do not hang up"
]


class SimulationRequest(BaseModel):
    scenario: str  # "cloned_ceo", "digital_arrest", "genuine_cxo", "benign_call"
    claimed_identity: str | None = None
    caller_id: str | None = None


@router.websocket("/live-call")
async def live_call_websocket(websocket: WebSocket):
    """Real-time bi-directional streaming WebSocket for live telephony & VoIP call monitoring."""
    await websocket.accept()

    detector = VoiceSpoofDetector(SETTINGS)
    ledger = get_blockchain_ledger()

    sample_rate = 16000
    window_size = 32000  # 2.0 seconds sliding window
    hop_size = 8000      # 0.5 seconds evaluation hop
    audio_buffer = np.array([], dtype=np.float32)
    full_audio_stream = []

    caller_id = "INCOMING_VOIP_CALL"
    claimed_identity = "UNKNOWN_CALLER"
    session_active = True
    call_start_time = datetime.now(timezone.utc).isoformat()
    max_risk_observed = 0.0

    try:
        while session_active:
            message = await websocket.receive()

            if "text" in message:
                try:
                    data = json.loads(message["text"])
                except Exception:
                    continue

                # Accept both {type: "init"} (frontend) and {action: "start"} (legacy)
                msg_type = data.get("type") or data.get("action") or ""

                if msg_type in ("init", "start"):
                    caller_id = data.get("caller_id", caller_id)
                    claimed_identity = data.get("claimed_identity", claimed_identity)
                    await websocket.send_json({
                        "type": "session_started",
                        "caller_id": caller_id,
                        "claimed_identity": claimed_identity,
                        "window_seconds": 2.0,
                        "status": "SENTINEL_ACTIVE",
                    })
                    continue

                elif msg_type in ("stop", "end"):
                    # Finalize session and record to blockchain
                    final_verdict = (
                        "CRITICAL_FRAUD_ATTEMPT" if max_risk_observed >= 0.52
                        else ("BORDERLINE_SUSPICIOUS" if max_risk_observed >= 0.30 else "AUTHENTIC_HUMAN")
                    )

                    combined_audio = np.concatenate(full_audio_stream) if full_audio_stream else np.zeros(1600, dtype=np.float32)
                    audio_bytes = (combined_audio * 32767).astype(np.int16).tobytes()

                    block = ledger.record_verification(
                        caller_id=caller_id,
                        claimed_identity=claimed_identity,
                        audio_bytes_or_hash=audio_bytes,
                        risk_score=max_risk_observed,
                        verdict=final_verdict,
                        vocoder_fingerprint="streaming_session_analysis",
                        telemetry={"start_time": call_start_time, "duration_samples": len(combined_audio)},
                    )

                    await websocket.send_json({
                        "type": "session_summary",
                        "status": "COMPLETED",
                        "final_risk_score": max_risk_observed,
                        "verdict": final_verdict,
                        "certificate_id": block["certificate_id"],
                        "block_hash": block["block_hash"],
                        "merkle_root": block["merkle_root"],
                        "compliance": "Section 65B Bharatiya Sakshya Adhiniyam Tamper-Proof Audit Record",
                    })
                    break

                elif msg_type in ("audio_chunk", "audio"):
                    # Audio passed as base64-encoded PCM16
                    b64_audio = data.get("payload") or data.get("audio")
                    if b64_audio:
                        raw_bytes = base64.b64decode(b64_audio)
                        pcm_16 = np.frombuffer(raw_bytes, dtype=np.int16)
                        chunk_samples = pcm_16.astype(np.float32) / 32768.0
                    else:
                        continue
                else:
                    # Unknown control message — skip, do NOT fall through to audio processing
                    continue

            elif "bytes" in message:
                raw_bytes = message["bytes"]
                pcm_16 = np.frombuffer(raw_bytes, dtype=np.int16)
                chunk_samples = pcm_16.astype(np.float32) / 32768.0
            else:
                continue

            # Guard: ensure chunk_samples is assigned before audio processing
            if not isinstance(chunk_samples, np.ndarray) or len(chunk_samples) == 0:
                continue

            # Append to rolling buffer
            audio_buffer = np.concatenate([audio_buffer, chunk_samples])
            full_audio_stream.append(chunk_samples)

            # Process sliding window
            while len(audio_buffer) >= window_size:
                eval_window = audio_buffer[:window_size]
                audio_buffer = audio_buffer[hop_size:]  # Slide forward by hop_size

                # Analyze chunk with low latency
                telemetry = detector.analyze_live_chunk(eval_window, sr=sample_rate)
                current_risk = telemetry["dynamic_risk_score"]

                # Check Speaker Verification against claimed identity
                speaker_info = {"matched": True, "similarity": 0.85, "note": "No enrolled profile constraint"}
                if claimed_identity and claimed_identity != "UNKNOWN_CALLER":
                    try:
                        # Query Safe-Voice registry for this identity
                        from app.db.database import SessionLocal
                        from app.db.models import FamilyMember
                        db = SessionLocal()
                        try:
                            member = db.query(FamilyMember).filter(
                                (FamilyMember.name.ilike(f"%{claimed_identity}%")) |
                                (FamilyMember.relationship.ilike(f"%{claimed_identity}%"))
                            ).first()
                            if member and member.enrollments:
                                enrolled_embs = [
                                    np.asarray(e.embedding, dtype=np.float32)
                                    for e in member.enrollments
                                    if e.embedding is not None
                                ]
                                if enrolled_embs:
                                    probe_audio = AudioData(samples=eval_window, sr=sample_rate)
                                    try:
                                        probe_emb = compute_embedding(probe_audio)
                                    except Exception:
                                        probe_emb = None
                                    if probe_emb is not None:
                                        sims = [float(cosine_similarity(emb, probe_emb)) for emb in enrolled_embs]
                                        best_sim = max(sims)
                                        threshold = SETTINGS.verify_similarity_threshold
                                        is_match = best_sim >= threshold
                                        speaker_info = {
                                            "matched": is_match,
                                            "similarity": round(best_sim, 3),
                                            "threshold": threshold,
                                            "name": member.name,
                                            "relationship": member.relationship or "Enrolled Member",
                                        }
                                        if not is_match and current_risk > 0.20:
                                            current_risk = min(1.0, current_risk + 0.25)
                                    else:
                                        speaker_info = {
                                            "matched": False,
                                            "similarity": 0.0,
                                            "threshold": SETTINGS.verify_similarity_threshold,
                                            "name": member.name,
                                            "relationship": member.relationship or "Enrolled Member",
                                            "note": "Acoustic probe too short or degraded",
                                        }
                        finally:
                            db.close()
                    except Exception:
                        pass

                if current_risk > max_risk_observed:
                    max_risk_observed = current_risk

                # Build real-time response packet
                payload = {
                    "type": "telemetry",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "dynamic_risk_score": round(current_risk, 3),
                    "liveness_score": telemetry["liveness_score"],
                    "vocoder_anomaly": telemetry["vocoder_anomaly"],
                    "clone_score": telemetry.get("clone_score"),
                    "dhwani_fake_probability": telemetry.get("dhwani_fake_probability"),
                    "pitch_stability": telemetry["pitch_stability"],
                    "micro_jitter": telemetry["micro_jitter"],
                    "telephony_mode": telemetry["telephony_mode"],
                    "fingerprint": telemetry["fingerprint"],
                    "speaker_match": speaker_info,
                    "verdict": (
                        "CRITICAL_IMPERSONATION" if current_risk >= 0.52
                        else ("BORDERLINE_SUSPICIOUS" if current_risk >= 0.28 else "GENUINE_HUMAN")
                    ),
                    "alert": telemetry["alert"],
                    "recommended_action": (
                        "TERMINATE_AND_CHALLENGE_WITH_OUT_OF_BAND_AUTH" if current_risk >= 0.52
                        else ("VERIFY_VIA_CALLBACK" if current_risk >= 0.28 else "SAFE_PROCEED")
                    ),
                }

                await websocket.send_json(payload)

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        import traceback
        traceback.print_exc()
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass


@router.post("/simulate", summary="Simulate live telephony stream using pre-recorded scenarios")
def simulate_scenario(req: SimulationRequest) -> dict[str, Any]:
    """Provides instant simulation of live call streaming with realistic timeline telemetry."""
    detector = VoiceSpoofDetector(SETTINGS)
    ledger = get_blockchain_ledger()

    # Determine audio file for scenario
    sample_dir = SETTINGS.data_dir / "samples"
    test_dir = SETTINGS.data_dir.parent / "testing set"

    if req.scenario == "cloned_ceo":
        # Target: AI generated voice with executive impersonation
        audio_file = test_dir / "ai_generated_voice.wav"
        if not audio_file.exists():
            audio_file = sample_dir / "scam_courier.wav"
        caller = req.caller_id or "+91 99880 12345"
        claimed = req.claimed_identity or "CEO Rajesh Nair"
        scenario_title = "Executive Impersonation: Cloned CEO Demanding Urgent Wire Transfer"
    elif req.scenario == "digital_arrest":
        audio_file = sample_dir / "scam_digital_arrest.wav"
        caller = req.caller_id or "+91 80001 99999"
        claimed = req.claimed_identity or "DCP Cyber Crime Cell"
        scenario_title = "Government Impersonation: Fraudulent Digital Arrest Demand"
    elif req.scenario == "genuine_cxo":
        audio_file = test_dir / "natural_voice.wav"
        if not audio_file.exists():
            audio_file = sample_dir / "benign_family.wav"
        caller = req.caller_id or "+91 98200 55443"
        claimed = req.claimed_identity or "CFO Priya Sharma"
        scenario_title = "Authorized Executive: Genuine CFO Routine Authorization Call"
    else:
        audio_file = sample_dir / "benign_restaurant.wav"
        caller = req.caller_id or "+91 91234 56789"
        claimed = req.claimed_identity or "Customer Support"
        scenario_title = "Benign Telephony Conversation"

    if not audio_file.exists():
        raise HTTPException(status_code=404, detail=f"Reference sample audio file '{audio_file.name}' not found.")

    audio_data = load_audio_16k(audio_file)
    x = audio_data.samples
    sr = audio_data.sr

    # Generate sliding window chunks (every 1 second)
    chunk_len = int(sr * 2.0)
    hop = int(sr * 1.0)
    timeline = []
    max_risk = 0.0

    for i in range(0, len(x) - chunk_len + 1, hop):
        window = x[i : i + chunk_len]
        res = detector.analyze_live_chunk(window, sr=sr)
        risk = res["dynamic_risk_score"]
        if risk > max_risk:
            max_risk = risk

        sec_start = round(i / sr, 1)
        sec_end = round((i + chunk_len) / sr, 1)
        timeline.append({
            "timestamp_offset": f"{sec_start}s - {sec_end}s",
            "dynamic_risk_score": risk,
            "liveness_score": res["liveness_score"],
            "vocoder_anomaly": res["vocoder_anomaly"],
            "pitch_stability": res["pitch_stability"],
            "micro_jitter": res["micro_jitter"],
            "verdict": res["verdict"],
            "alert": res["alert"],
        })

    # Run full clip multi-layer combined engine analysis (Dhwani + Vocoder DSP + Acoustic Ensemble)
    full_res = detector.analyze(audio_data)
    if full_res.get("score") is not None and full_res["score"] > max_risk:
        max_risk = full_res["score"]

    # Record certificate in Blockchain Ledger
    final_verdict = "CRITICAL_FRAUD_ATTEMPT" if max_risk >= 0.52 else ("BORDERLINE_SUSPICIOUS" if max_risk >= 0.30 else "AUTHENTIC_HUMAN")
    block = ledger.record_verification(
        caller_id=caller,
        claimed_identity=claimed,
        audio_bytes_or_hash=hashlib.sha256(x.tobytes()).hexdigest(),
        risk_score=max_risk,
        verdict=final_verdict,
        vocoder_fingerprint="simulation_" + req.scenario,
        telemetry={
            "duration_seconds": round(len(x) / sr, 2),
            "scenario": req.scenario,
            "engine": full_res.get("engine"),
            "dhwani_fake_probability": full_res.get("metrics", {}).get("dhwani_fake_probability"),
        },
    )

    return {
        "scenario": req.scenario,
        "scenario_title": scenario_title,
        "caller_id": caller,
        "claimed_identity": claimed,
        "duration_seconds": round(len(x) / sr, 2),
        "peak_risk_score": max_risk,
        "overall_verdict": final_verdict,
        "engine": full_res.get("engine", "combined_hybrid_engine"),
        "full_analysis": full_res,
        "certificate_id": block["certificate_id"],
        "block_hash": block["block_hash"],
        "timeline": timeline,
    }


@router.get("/scenario-audio/{scenario}", summary="Stream reference WAV audio for simulated attack vectors")
def get_scenario_audio(scenario: str) -> FileResponse:
    """Returns the authentic reference audio file for a telephony scenario."""
    sample_dir = SETTINGS.data_dir / "samples"
    test_dir = SETTINGS.data_dir.parent / "testing set"

    if scenario == "cloned_ceo":
        audio_file = test_dir / "ai_generated_voice.wav"
        if not audio_file.exists():
            audio_file = sample_dir / "scam_courier.wav"
    elif scenario == "digital_arrest":
        audio_file = sample_dir / "scam_digital_arrest.wav"
    elif scenario == "genuine_cxo":
        audio_file = test_dir / "natural_voice.wav"
        if not audio_file.exists():
            audio_file = sample_dir / "benign_family.wav"
    else:
        audio_file = sample_dir / "benign_restaurant.wav"

    if not audio_file.exists():
        raise HTTPException(status_code=404, detail="Scenario audio not found")
    return FileResponse(path=str(audio_file), media_type="audio/wav")


@router.get("/sample-file/{filename}", summary="Retrieve reference benchmark testing samples")
def get_sample_file(filename: str) -> FileResponse:
    """Returns benchmark sample files such as ai_generated_voice.wav or natural_voice.wav."""
    test_dir = SETTINGS.data_dir.parent / "testing set"
    sample_dir = SETTINGS.data_dir / "samples"

    target = test_dir / filename
    if not target.exists():
        target = sample_dir / filename
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Sample file '{filename}' not found.")

    return FileResponse(path=str(target), media_type="audio/wav")

