"""Analysis pipeline: orchestrate detectors and produce a verdict.

Exposes two entry points used by the API routes:

* :meth:`analyze_transcript` — text-only analysis (no media).
* :meth:`analyze_media` — full audio/video pipeline (ASR -> voice spoof ->
  video deepfake -> scam-script classification -> risk aggregation).

Both accept an optional ``on_progress`` callback used by the job queue.
"""

from __future__ import annotations

from typing import Any, Callable

from app.config import get_settings
from app.core.risk_engine import assess
from app.detectors import DetectorManager, get_detectors
from app.detectors.audio.audio_utils import extract_audio_from_video, load_audio_16k
from app.services.llm_analysis import analyze_transcript_ai


class AnalysisPipeline:
    def __init__(self, detectors: DetectorManager | None = None, settings=None):
        self.settings = settings or get_settings()
        self.detectors = detectors or get_detectors()

    # ------------------------------------------------------------------ public
    def analyze_transcript(
        self, text: str, language_hint: str | None = None, skip_ai: bool = False
    ) -> dict[str, Any]:
        scam = self.detectors.scam.classify(text, language=language_hint)
        result = assess(
            media_type="text",
            asr=None,
            voice=None,
            video=None,
            scam=scam,
            transcript=text,
            language=language_hint,
        )
        if skip_ai:
            result["ai_analysis"] = None
            return result
        return self._attach_ai(result, media_type="text")

    def analyze_media(
        self,
        media_type: str,
        file_path: str,
        original_filename: str | None = None,
        on_progress: Callable[[float, str | None], None] | None = None,
    ) -> dict[str, Any]:
        def _p(p: float, msg: str | None = None) -> None:
            if on_progress:
                on_progress(p, msg)

        media_type = "video" if media_type == "video" else "audio"

        import concurrent.futures

        _p(0.15, "Decoding audio")
        audio = None
        asr_res = None
        voice_res = None
        video_res = None

        if media_type == "video":
            wav_path = extract_audio_from_video(file_path)
            audio = load_audio_16k(str(wav_path), convert=False)
        else:
            audio = load_audio_16k(file_path)

        _p(0.30, "Analysing audio & visual signals in parallel")

        def _run_asr():
            if audio is not None:
                return self.detectors.asr.transcribe(str(audio.path))
            return None

        def _run_voice():
            if audio is not None:
                return self.detectors.voice.analyze(audio)
            return None

        def _run_video():
            if media_type == "video":
                return self.detectors.video.analyze(file_path)
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            fut_asr = executor.submit(_run_asr)
            fut_voice = executor.submit(_run_voice)
            fut_video = executor.submit(_run_video)

            asr_res = fut_asr.result()
            _p(0.60, "Speech transcribed")
            voice_res = fut_voice.result()
            _p(0.75, "Voice authenticity assessed")
            video_res = fut_video.result()
            if media_type == "video":
                _p(0.85, "Video deepfake cues scanned")

        transcript = (asr_res or {}).get("transcript") or None
        language = (asr_res or {}).get("language") or None

        scam_res = None
        if transcript and transcript.strip():
            _p(0.90, "Scanning for scam-script patterns")
            scam_res = self.detectors.scam.classify(transcript, language=language)

        _p(0.95, "Aggregating risk & consulting AI shield")
        result = assess(
            media_type=media_type,
            asr=asr_res,
            voice=voice_res,
            video=video_res,
            scam=scam_res,
            transcript=transcript,
            language=language,
        )
        result = self._attach_ai(result, media_type=media_type)
        result["media"] = {
            "media_type": media_type,
            "original_filename": original_filename,
            "duration_seconds": round(audio.duration, 2) if audio else None,
        }
        _p(1.0, "Done")
        return result

    # ------------------------------------------------------------- AI layer
    def _attach_ai(self, result: dict, media_type: str) -> dict:
        """Attach the LLM second opinion to a verdict.

        When the AI is a confident scam verdict the local models missed, the
        risk engine is re-run with ``ai=`` so it can corroborate (raise the
        score, capped) and add an ``ai-llm-corrob`` red flag. Any failure of
        the external AI call leaves ``ai_analysis=None`` and the verdict
        identical to the local-only result.
        """
        transcript = (result.get("transcript") or "").strip()
        if not transcript:
            result["ai_analysis"] = None
            return result
        try:
            ai = analyze_transcript_ai(transcript, result.get("signals"), result.get("risk"))
        except Exception:  # noqa: BLE001  (AI layer must never break a scan)
            ai = None
        result["ai_analysis"] = ai

        if ai and ai.get("status") == "ok" and ai.get("verdict", {}).get("is_scam"):
            signals = result.get("signals") or {}
            result = assess(
                media_type=media_type,
                asr=signals.get("asr"),
                voice=signals.get("voice"),
                video=signals.get("video"),
                scam=signals.get("text"),
                transcript=result.get("transcript"),
                language=result.get("language"),
                ai=ai,
            )
            result["ai_analysis"] = ai
        return result


def get_pipeline() -> AnalysisPipeline:
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = AnalysisPipeline()
    return _PIPELINE


_PIPELINE: AnalysisPipeline | None = None
