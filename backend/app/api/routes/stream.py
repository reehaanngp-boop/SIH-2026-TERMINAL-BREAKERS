"""Real-time live-call stream WebSocket endpoint (mic-only sentinel).

The threat-simulation and benchmark sample-file endpoints were removed: the
console is a live audit tool, not a demo player. On session end the captured
audio is re-analysed through the authoritative full-file ensemble and the
AASIST-style workflow (audio -> human/AI gate -> transcribe -> language ->
scam classify by key terms -> risk-engine verdict), so the final certificate
carries the transcript-aware risk decision, not just the live peak.
"""

from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timezone
import json
from typing import Any
from uuid import uuid4

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import get_settings
from app.core.blockchain_ledger import get_blockchain_ledger
from app.detectors.audio.audio_utils import AudioData
from app.detectors.audio.speaker_verify import compute_embedding, verify_claimed
from app.detectors.audio.voice_spoof import VoiceSpoofDetector

router = APIRouter(prefix="/stream", tags=["stream"])
SETTINGS = get_settings()

MAX_AUDIT_SECONDS = 120  # cap the end-of-call audit window to bound latency


def run_stop_analysis(detector: VoiceSpoofDetector, combined_audio: np.ndarray) -> dict[str, Any]:
    """AASIST-style end-of-call audit.

    1. Full-file audio -> model-backed human/AI verdict (ensemble).
    2. Whisper transcribes it and auto-detects the language.
    3. Scam classifier scans the wording for known script signatures in that
       language.
    4. Risk engine fuses voice + text into the final verdict; a confirmed
       synthetic/cloned voice forces ``terminate_call`` regardless of text.
    """
    combined_audio = np.asarray(combined_audio, dtype=np.float32)
    if len(combined_audio) > 16000 * MAX_AUDIT_SECONDS:
        combined_audio = combined_audio[-16000 * MAX_AUDIT_SECONDS:]

    duration = float(len(combined_audio) / 16000.0) if len(combined_audio) else 0.0
    audio = AudioData(samples=combined_audio, sr=16000, duration=duration)
    voice = detector.analyze(audio)

    asr_res = None
    transcript = None
    language = None
    if len(combined_audio) >= 16000 * 0.5:
        tmp = SETTINGS.upload_dir / "_converted" / f"stream_{uuid4().hex[:12]}.wav"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        try:
            import soundfile as sf

            sf.write(str(tmp), combined_audio, 16000, subtype="PCM_16")
            from app.detectors.audio.asr import AsrDetector

            asr_res = AsrDetector(SETTINGS).transcribe(str(tmp))
            transcript = (asr_res or {}).get("transcript")
            language = (asr_res or {}).get("language")
        except Exception:  # noqa: BLE001 - ASR must never break certificate issuance
            asr_res = None
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass

    scam = None
    if transcript and transcript.strip():
        try:
            from app.detectors.text.scam_classifier import ScamClassifierDetector

            scam = ScamClassifierDetector(SETTINGS).classify(transcript, language=language)
        except Exception:  # noqa: BLE001
            scam = None

    from app.core.risk_engine import assess

    result = assess(
        media_type="audio",
        asr=asr_res,
        voice=voice,
        video=None,
        scam=scam,
        transcript=transcript,
        language=language,
    )
    level = result["risk"]["level"]
    verdict = {
        "high": "CRITICAL_FRAUD_ATTEMPT",
        "medium": "BORDERLINE_SUSPICIOUS",
        "low": "AUTHENTIC_HUMAN",
    }.get(level, "AUTHENTIC_HUMAN")

    scam_cat = None
    scam_conf = None
    if scam and scam.get("metrics"):
        cat = scam.get("label")
        if cat and cat != "uncertain":
            scam_cat = cat
            scam_conf = float(scam.get("score") or 0.0)

    return {
        "scored": True,
        "risk_score_100": float(result["risk"]["score"]),
        "risk_level": level,
        "risk": result["risk"],
        "verdict": verdict,
        "voice_label": (voice or {}).get("label"),
        "voice_engine": (voice or {}).get("engine"),
        "transcript": transcript,
        "language": language,
        "scam_category": scam_cat,
        "scam_confidence": round(scam_conf, 3) if scam_conf is not None else None,
        "red_flag_ids": [f.get("id") for f in result.get("red_flags", [])],
        "terminate_call": bool(result.get("terminate_call")),
        "next_steps": result.get("next_steps", []),
    }


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
    claimed_profile = None  # cached (member, cohort) for the claimed identity
    session_active = True
    call_start_time = datetime.now(timezone.utc).isoformat()
    max_risk_observed = 0.0

    try:
        while session_active:
            message = await websocket.receive()

            if "text" in message:
                try:
                    data = json.loads(message["text"])
                except Exception:  # noqa: BLE001
                    continue

                # Accept both {type: "init"} (frontend) and {action: "start"} (legacy)
                msg_type = data.get("type") or data.get("action") or ""

                if msg_type in ("init", "start"):
                    caller_id = data.get("caller_id", caller_id)
                    claimed_identity = data.get("claimed_identity", claimed_identity)
                    claimed_profile = None
                    await websocket.send_json({
                        "type": "session_started",
                        "caller_id": caller_id,
                        "claimed_identity": claimed_identity,
                        "window_seconds": 2.0,
                        "status": "SENTINEL_ACTIVE",
                    })
                    continue

                elif msg_type in ("stop", "end"):
                    # Finalize session: authoritative full-file audit + certificate
                    combined_audio = (
                        np.concatenate(full_audio_stream) if full_audio_stream
                        else np.zeros(1600, dtype=np.float32)
                    )
                    audio_bytes = (combined_audio * 32767).astype(np.int16).tobytes()

                    workflow = None
                    try:
                        workflow = await asyncio.to_thread(run_stop_analysis, detector, combined_audio)
                    except Exception:  # noqa: BLE001 - final analysis must not break the summary
                        workflow = None

                    if workflow and workflow.get("scored"):
                        final_risk = max(max_risk_observed, workflow["risk_score_100"] / 100.0)
                        final_verdict = workflow["verdict"]
                        terminate_call = workflow["terminate_call"]
                    else:
                        final_risk = max_risk_observed
                        final_verdict = (
                            "CRITICAL_FRAUD_ATTEMPT" if final_risk >= 0.52
                            else ("BORDERLINE_SUSPICIOUS" if final_risk >= 0.30 else "AUTHENTIC_HUMAN")
                        )
                        terminate_call = False

                    block = ledger.record_verification(
                        caller_id=caller_id,
                        claimed_identity=claimed_identity,
                        audio_bytes_or_hash=audio_bytes,
                        risk_score=final_risk,
                        verdict=final_verdict,
                        vocoder_fingerprint="streaming_session_analysis",
                        telemetry={
                            "start_time": call_start_time,
                            "duration_samples": len(combined_audio),
                            "language": (workflow or {}).get("language"),
                            "scam_category": (workflow or {}).get("scam_category"),
                            "transcript": ((workflow or {}).get("transcript") or "")[:500],
                        },
                    )

                    summary = {
                        "type": "session_summary",
                        "status": "COMPLETED",
                        "final_risk_score": round(final_risk, 3),
                        "verdict": final_verdict,
                        "certificate_id": block["certificate_id"],
                        "block_hash": block["block_hash"],
                        "merkle_root": block["merkle_root"],
                        "compliance": "Section 65B Bharatiya Sakshya Adhiniyam Tamper-Proof Audit Record",
                    }
                    if workflow:
                        summary.update({
                            "terminate_call": terminate_call,
                            "risk_level": workflow.get("risk_level"),
                            "voice_label": workflow.get("voice_label"),
                            "engine": workflow.get("voice_engine"),
                            "transcript": workflow.get("transcript"),
                            "language": workflow.get("language"),
                            "scam_category": workflow.get("scam_category"),
                            "scam_confidence": workflow.get("scam_confidence"),
                            "red_flag_ids": workflow.get("red_flag_ids", []),
                        })
                    await websocket.send_json(summary)
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

                # Analyze chunk with the live three-signal ensemble
                telemetry = detector.analyze_live_chunk(eval_window, sr=sample_rate)
                current_risk = telemetry["dynamic_risk_score"]

                # Check Speaker Verification against claimed identity
                speaker_info = {"matched": True, "similarity": 0.85, "note": "No enrolled profile constraint"}
                if claimed_profile is None and claimed_identity and claimed_identity != "UNKNOWN_CALLER":
                    from app.db.database import SessionLocal
                    from app.db.models import FamilyMember

                    db = SessionLocal()
                    try:
                        member = db.query(FamilyMember).filter(
                            (FamilyMember.name.ilike(f"%{claimed_identity}%")) |
                            (FamilyMember.relationship.ilike(f"%{claimed_identity}%"))
                        ).first()
                        cohort: list[Any] = []
                        if member is not None:
                            for other in db.query(FamilyMember).filter(FamilyMember.id != member.id).all():
                                cohort.extend(e.embedding for e in other.enrollments if e.embedding is not None)
                        claimed_profile = {"member": member, "cohort": cohort}
                    finally:
                        db.close()

                if claimed_profile and claimed_profile["member"]:
                    member = claimed_profile["member"]
                    enrolled_embs = [
                        np.asarray(e.embedding, dtype=np.float32)
                        for e in member.enrollments
                        if e.embedding is not None
                    ]
                    if enrolled_embs:
                        probe_audio = AudioData(samples=eval_window, sr=sample_rate)
                        try:
                            probe_emb = compute_embedding(probe_audio)
                        except Exception:  # noqa: BLE001
                            probe_emb = None
                        if probe_emb is not None:
                            decision = verify_claimed(
                                probe_emb,
                                enrolled_embs,
                                claimed_profile["cohort"],
                                threshold=SETTINGS.verify_similarity_threshold,
                            )
                            if decision:
                                is_match = decision["is_match"]
                                speaker_info = {
                                    "matched": is_match,
                                    "similarity": decision["best_similarity"],
                                    "separation": decision["separation"],
                                    "confidence_level": decision["confidence_level"],
                                    "threshold": SETTINGS.verify_similarity_threshold,
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
                                    "note": "Incompatible embedded profile",
                                }
                        else:
                            speaker_info = {
                                "matched": False,
                                "similarity": 0.0,
                                "threshold": SETTINGS.verify_similarity_threshold,
                                "name": member.name,
                                "relationship": member.relationship or "Enrolled Member",
                                "note": "Acoustic probe too short or degraded",
                            }
                    else:
                        speaker_info = {
                            "matched": None,
                            "similarity": None,
                            "threshold": SETTINGS.verify_similarity_threshold,
                            "name": member.name,
                            "relationship": member.relationship or "Enrolled Member",
                            "note": "No enrolled voice samples yet",
                        }

                if current_risk > max_risk_observed:
                    max_risk_observed = current_risk

                # Build real-time response packet
                payload = {
                    "type": "telemetry",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "dynamic_risk_score": round(current_risk, 3),
                    "liveness_score": telemetry["liveness_score"],
                    "vocoder_anomaly": telemetry["vocoder_anomaly"],
                    "wav2vec2_fake_probability": telemetry.get("wav2vec2_fake_probability"),
                    "dhwani_fake_probability": telemetry.get("dhwani_fake_probability"),
                    "large_fake_probability": telemetry.get("large_fake_probability"),
                    "fusion": telemetry.get("fusion"),
                    "pitch_stability": telemetry["pitch_stability"],
                    "micro_jitter": telemetry["micro_jitter"],
                    "telephony_mode": telemetry["telephony_mode"],
                    "fingerprint": telemetry["fingerprint"],
                    "speaker_match": speaker_info,
                    "verdict": telemetry["verdict"],
                    "alert": telemetry["alert"],
                    "recommended_action": (
                        "TERMINATE_AND_CHALLENGE_WITH_OUT_OF_BAND_AUTH" if current_risk >= 0.52
                        else ("VERIFY_VIA_CALLBACK" if current_risk >= 0.28 else "SAFE_PROCEED")
                    ),
                }

                await websocket.send_json(payload)

    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:  # noqa: BLE001
            pass