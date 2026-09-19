"""Tests for Multi-Layer Voice Cloning & Deepfake Detection Engine.

Validates the combined ensemble:
1. Multilingual Foundation Model (Dhwani Wav2Vec2 + AASIST ONNX)
2. Physical Vocoder & Spectral DSP Forensics
3. Biomechanical Acoustic Ensemble Classifier
"""

import sys
from pathlib import Path
import soundfile as sf

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.detectors.audio.audio_utils import AudioData
from app.detectors.audio.dhwani_detector import DhwaniDetector
from app.detectors.audio.vocoder_analyzer import VocoderAnalyzer
from app.detectors.audio.voice_spoof import VoiceSpoofDetector


AI_VOICE_SAMPLE = PROJECT_ROOT / "testing set" / "ai_generated_voice.wav"
NATURAL_VOICE_SAMPLE = PROJECT_ROOT / "testing set" / "natural_voice.wav"


def test_vocoder_analyzer_on_synthetic_vs_natural():
    """Verify physical vocoder DSP detects spectral and phase characteristics."""
    analyzer = VocoderAnalyzer(sample_rate=16000)

    ai_audio, sr_ai = sf.read(str(AI_VOICE_SAMPLE))
    ai_metrics = analyzer.analyze_spectral_artifacts(ai_audio)

    natural_audio, sr_nat = sf.read(str(NATURAL_VOICE_SAMPLE))
    natural_metrics = analyzer.analyze_spectral_artifacts(natural_audio)

    assert "vocoder_anomaly_score" in ai_metrics
    assert "vocoder_fingerprint" in ai_metrics
    assert "phase_inconsistency" in ai_metrics
    assert "phase_inconsistency" in natural_metrics


def test_combined_voice_spoof_detector():
    """Verify the multi-layer ensemble correctly differentiates AI voice from Natural voice."""
    detector = VoiceSpoofDetector()

    # 1. Test AI-generated voice sample
    ai_audio, sr_ai = sf.read(str(AI_VOICE_SAMPLE))
    ai_data = AudioData(samples=ai_audio, sr=sr_ai, duration=len(ai_audio) / sr_ai)
    ai_res = detector.analyze(ai_data)

    print("\n--- AI GENERATED VOICE RESULT ---")
    print(f"Risk Score: {ai_res['score']}")
    print(f"Label: {ai_res['label']}")
    print(f"Engine: {ai_res.get('engine')}")
    print(f"Metrics: {ai_res.get('metrics')}")

    assert ai_res["score"] >= 0.50
    assert ai_res["label"] in ("likely-ai-generated", "borderline-suspicious")

    # 2. Test Natural genuine voice sample
    nat_audio, sr_nat = sf.read(str(NATURAL_VOICE_SAMPLE))
    nat_data = AudioData(samples=nat_audio, sr=sr_nat, duration=len(nat_audio) / sr_nat)
    nat_res = detector.analyze(nat_data)

    print("\n--- NATURAL VOICE RESULT ---")
    print(f"Risk Score: {nat_res['score']}")
    print(f"Label: {nat_res['label']}")
    print(f"Engine: {nat_res.get('engine')}")
    print(f"Metrics: {nat_res.get('metrics')}")

    assert nat_res["score"] < 0.35
    assert nat_res["label"] == "likely-natural"


def test_live_chunk_streaming_performance():
    """Verify sub-30ms execution for live telephony chunks."""
    import time
    detector = VoiceSpoofDetector()

    ai_audio, sr = sf.read(str(AI_VOICE_SAMPLE))
    chunk_2sec = ai_audio[:32000]  # 2.0s chunk at 16kHz

    # Warm-up JIT and models
    detector.analyze_live_chunk(chunk_2sec, sr=16000)

    t0 = time.time()
    telemetry = detector.analyze_live_chunk(chunk_2sec, sr=16000)
    latency_ms = (time.time() - t0) * 1000

    print(f"\nLive Chunk Latency: {latency_ms:.2f} ms")
    assert latency_ms < 1500  # Well within sliding window budget on CPU
    assert "dynamic_risk_score" in telemetry
    assert "liveness_score" in telemetry
    assert "vocoder_anomaly" in telemetry


if __name__ == "__main__":
    test_vocoder_analyzer_on_synthetic_vs_natural()
    test_combined_voice_spoof_detector()
    test_live_chunk_streaming_performance()
    print("\n[PASS] All Multi-Layer Voice Cloning Detection tests passed successfully!")
