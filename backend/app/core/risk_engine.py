"""Risk aggregation: combine detector outputs into one explainable verdict.

The engine turns raw detector results into:

* a single **risk score** (0-100) and level (low/medium/high),
* a **red-flags** list with localised explanations,
* a **next-steps** list guiding the user to verify and report.

Weights are chosen so voice and scam-language signals dominate (they are the
most reliable), with video as a supporting signal. Missing detectors simply
contribute nothing rather than failing the whole analysis.
"""

from __future__ import annotations

from typing import Any

from app.core.strings import NEXT_STEPS, RED_FLAGS, RISK_LABELS

# Dimension weights (renormalised over the dimensions that produced results).
WEIGHTS = {"voice": 0.40, "text": 0.35, "video": 0.25}

# Score thresholds (0-100).
LOW_MEDIUM = 40.0
MEDIUM_HIGH = 65.0

# Minimum LLM confidence before an AI "this is a scam" verdict may corroborate
# (i.e. raise) a low/medium local verdict. Below this the AI is treated as
# advisory only. The AI can never lower a verdict the local models raised.
AI_ESCALATE_CONFIDENCE = 0.7

# Per-category -> red-flag mapping from the scam classifier.
CATEGORY_FLAGS = {
    "digital_arrest": "scam-arrest",
    "fake_courier": "scam-courier",
    "otp_phishing": "scam-otp",
    "kin_emergency": "scam-kin",
    "other_fraud": "scam-generic",
}


def _clone_text(t: dict) -> dict:
    """Return a plain dict copy of a LocalizedText-like object."""
    return {"en": t.get("en", ""), "hi": t.get("hi", "")}


def _lazy_flag(flag_id: str) -> dict | None:
    spec = RED_FLAGS.get(flag_id)
    if spec is None:
        return None
    return {
        "id": flag_id,
        "category": spec["category"],
        "severity": spec["severity"],
        "title": _clone_text(spec["title"]),
        "detail": _clone_text(spec["detail"]),
    }


def _next_step(step_id: str) -> dict | None:
    spec = NEXT_STEPS.get(step_id)
    if spec is None:
        return None
    return {
        "id": step_id,
        "kind": spec["kind"],
        "title": _clone_text(spec["title"]),
        "detail": _clone_text(spec["detail"]),
        "href": "tel:1930" if step_id == "report-1930" else ("https://cybercrime.gov.in" if step_id == "report-portal" else None),
    }


def assess(
    *,
    media_type: str,
    asr: dict | None = None,
    voice: dict | None = None,
    video: dict | None = None,
    scam: dict | None = None,
    transcript: str | None = None,
    language: str | None = None,
    ai: dict | None = None,
) -> dict[str, Any]:
    """Compute the verdict from detector result dicts.

    ``ai`` is the optional LLM second opinion produced by
    ``app.services.llm_analysis.analyze_transcript_ai``. When it is a confident
    scam verdict it can *raise* a low/medium text verdict (adding an
    ``ai-llm-corrob`` red flag), but it never lowers a verdict the local
    detectors produced.
    """
    flags: list[dict] = []
    steps: list[dict] = []
    dim_risks: dict[str, float] = {}

    # ---- Voice dimension -------------------------------------------------
    voice_signal = _signal("voice", voice)
    if voice and voice.get("status") == "available" and voice.get("score") is not None:
        vs = voice["score"]
        engine = voice.get("engine", "heuristics")
        label = voice.get("label", "")
        if any(m in engine for m in ("voice_clone", "aasist", "dhwani", "combined")):
            # Model-backed verdict (Dhwani Multilingual / Voice Cloning AI / AASIST / Vocoder).
            dim_risks["voice"] = vs
            if vs >= 0.55 or label == "likely-ai-generated":
                flags.append(_lazy_flag("voice-ai-likely"))
            elif vs >= 0.38 or label == "borderline-suspicious":
                flags.append(_lazy_flag("voice-artifacts"))
        else:
            # Heuristics-only (no anti-spoof model loaded) is genuinely
            # low-confidence. Never emit AI-clone flags from heuristics alone,
            # and cap the contribution so it cannot push a benign call to high.
            dim_risks["voice"] = min(vs, 0.3)
            if label in ("likely-ai-generated", "borderline-suspicious", "spoof") or vs >= 0.5:
                flags.append(_lazy_flag("voice-cannot-check"))
    elif voice and voice.get("label") == "no-speech":
        pass  # nothing to authenticate; not a fraud signal

    # ---- Video dimension -------------------------------------------------
    video_signal = _signal("video", video)
    if video and video.get("status") == "available" and video.get("score") is not None:
        vd = video["score"]
        # Frame-level heuristics are a supporting cue only: webcam/video calls
        # are naturally steady, so a high score here is never critical. Cap the
        # contribution and keep severity at warning to avoid escalating benign
        # calls from motion/compression artifacts.
        dim_risks["video"] = min(vd, 0.4)
        if vd >= 0.5:
            flags.append(_lazy_flag("video-warning"))
    elif video and video.get("status") == "available" and video.get("label") == "no-face":
        flags.append(_lazy_flag("video-cannot-check"))

    # ---- Text dimension ---------------------------------------------------
    text_signal = _signal("text", scam)
    scam_category = None
    if scam and scam.get("status") == "available" and scam.get("score") is not None:
        probs = (scam.get("metrics") or {}).get("probabilities", {})
        if scam.get("label") != "uncertain":
            scam_category = scam["label"]
            if scam_category in ("benign", "neutral"):
                dim_risks["text"] = 0.05
                flags.append(_lazy_flag("text-benign"))
            elif scam_category == "other_fraud":
                # Generic fraud bucket (lottery/refund/job-offer scams). The
                # classifier's margin-over-benign rule already stops benign
                # text from landing here, so a confident match can still reach
                # a moderate-high risk; the floor stays low for fuzzy matches.
                conf = scam["score"]
                dim_risks["text"] = float(max(0.35, min(0.7, 0.35 + (conf - 0.5) * 0.9)))
                flags.append(_lazy_flag("scam-generic"))
            else:
                flag_id = CATEGORY_FLAGS.get(scam_category, "scam-generic")
                # Specific documented scam scripts. Confidence-scaled: at the
                # 0.5 confidence floor -> 0.5, at 1.0 -> 0.9.
                conf = scam["score"]
                risk = min(0.9, 0.5 + (conf - 0.5) * 0.8)
                dim_risks["text"] = risk
                flags.append(_lazy_flag(flag_id))

    # ---- AI second opinion --------------------------------------------------
    # Independent LLM review. It may corroborate a scam the local text model
    # missed by raising the text dimension (capped so AI is never the sole
    # driver), but only above a confidence floor and never lowering anything.
    if ai and ai.get("status") == "ok":
        v = ai.get("verdict") or {}
        if v.get("is_scam"):
            try:
                conf = float(v.get("confidence") or 0.0)
            except (TypeError, ValueError):
                conf = 0.0
            if conf >= AI_ESCALATE_CONFIDENCE:
                # conf 0.7 -> 0.53, conf 1.0 -> 0.8.
                contrib = min(0.8, 0.35 + (conf - 0.5) * 0.9)
                if contrib > dim_risks.get("text", 0.0):
                    dim_risks["text"] = contrib
                    if contrib >= 0.6:
                        flags.append(_lazy_flag("ai-llm-corrob"))

    # ---- ASR quality hint ---------------------------------------------------
    if asr and asr.get("status") == "available" and asr.get("metrics"):
        lp = asr["metrics"].get("avg_logprob")
        if lp is not None and lp < -1.4:
            flags.append(_lazy_flag("low-audio-quality"))

    # ---- Overall score ------------------------------------------------------
    used = [k for k in WEIGHTS if k in dim_risks]
    if used:
        wsum = sum(WEIGHTS[k] for k in used)
        score = sum(dim_risks[k] * WEIGHTS[k] for k in used) / wsum
    else:
        score = 0.05

    # Filter None values and deduplicate flags safely
    valid_flags: list[dict] = []
    seen_flag_ids: set[str] = set()
    for f in flags:
        if f and isinstance(f, dict) and f.get("id") and f["id"] not in seen_flag_ids:
            seen_flag_ids.add(f["id"])
            valid_flags.append(f)

    # Escalate for multiple critical signals.
    n_critical = sum(1 for f in valid_flags if f.get("severity") == "critical")
    if n_critical >= 2:
        score = min(1.0, score * 1.15 + 0.05)
    elif n_critical == 1:
        score = min(1.0, score * 1.05)

    score100 = round(score * 100.0, 1)
    if score100 >= MEDIUM_HIGH:
        level = "high"
    elif score100 >= LOW_MEDIUM:
        level = "medium"
    else:
        level = "low"

    # ---- Next steps ----------------------------------------------------------
    if level == "high":
        steps.append(_next_step("verify-official"))
        steps.append(_next_step("no-otp"))
        if scam_category == "digital_arrest":
            steps.append(_next_step("no-arrest-fee"))
            steps.append(_next_step("stay-on-call"))
        steps.append(_next_step("report-1930"))
        steps.append(_next_step("report-portal"))
        steps.append(_next_step("contact-family"))
    elif level == "medium":
        steps.append(_next_step("verify-official"))
        steps.append(_next_step("no-otp"))
        if scam_category == "kin_emergency":
            steps.append(_next_step("registry-verify"))
        steps.append(_next_step("contact-family"))
    else:
        steps.append(_next_step("stay-vigilant"))

    valid_steps: list[dict] = []
    seen_step_ids: set[str] = set()
    for s in steps:
        if s and isinstance(s, dict) and s.get("id") and s["id"] not in seen_step_ids:
            seen_step_ids.add(s["id"])
            valid_steps.append(s)

    return {
        "risk": {
            "level": level,
            "score": score100,
            "label": _clone_text(RISK_LABELS[level]),
        },
        "signals": {
            "asr": asr_signal(asr),
            "voice": voice_signal,
            "video": video_signal,
            "text": text_signal,
        },
        "red_flags": valid_flags,
        "next_steps": valid_steps,
        "transcript": transcript,
        "language": language,
    }


def _signal(name: str, result: dict | None) -> dict:
    if not result:
        return {"name": name, "status": "unavailable", "available": False,
                "score": None, "label": None, "detail": None, "metrics": {}}
    return {
        "name": name,
        "status": result.get("status", "error"),
        "available": result.get("available", False),
        "score": result.get("score"),
        "label": result.get("label"),
        "detail": result.get("detail"),
        "metrics": result.get("metrics", {}),
        "engine": result.get("engine"),
    }


def asr_signal(result: dict | None) -> dict:
    """ASR signal carries the transcript; keep it separate from the risk signal."""
    return _signal("asr", result)
