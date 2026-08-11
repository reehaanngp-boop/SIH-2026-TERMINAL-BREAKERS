"""AI analysis layer backed by an OpenRouter chat model (default: free tier).

The local detectors are fast and offline, but the text classifier only knows
the fixed scam scripts it was trained on. This module sends the transcript —
plus a compact summary of the local detector signals — to an OpenRouter
completion model and asks for a structured second opinion:

    {"status": "ok", "model": <id>,
     "verdict": {"is_scam": bool, "confidence": float,
                 "scam_category": str | None, "key_indicators": [str],
                 "explanation": {"en": str, "hi": str}}}

It is deliberately separate from the ``BaseDetector`` stack: it is not a
sensor, it is a corroboration layer that the risk engine may consult.

Design rules (mirrors the graceful-degradation style of ``speaker_verify.py``):

* **Off by default.** ``enable_llm_analysis`` must be set explicitly because
  enabling sends the call transcript to an external API.
* **Never crashes a scan.** Any failure — missing key, timeout, HTTP error,
  unparseable reply — returns ``None`` and the pipeline falls back to the
  local models exactly as before.
* **One HTTP POST via the stdlib** (``urllib``). No new dependency, so the
  pyinstaller EXE build is unaffected.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from app.config import get_settings

settings = get_settings()

_SYSTEM_PROMPT = (
    "You are a cautious anti-scam call analyst for DigiRaksha, an Indian "
    "awareness tool for digital-arrest, fake-courier, OTP-phishing and "
    "kin-emergency scams. Read the call transcript and the local detector "
    "signals, then decide whether the caller is trying to scam the person on "
    "the phone. Be conservative: only set is_scam=true when the language is "
    "genuinely suspicious or matches a known scam script; false alarms erode "
    "trust. Answer in strict JSON only, with keys: is_scam (boolean), "
    "confidence (0-1), scam_category (one of 'digital_arrest', 'fake_courier', "
    "'otp_phishing', 'kin_emergency', 'other_fraud', 'benign'), "
    "key_indicators (array of short strings), explanation_en (short English "
    "explanation), explanation_hi (the same explanation in Hindi)."
)

_MIN_TRANSCRIPT_CHARS = 20

# Free-tier models are served from a shared pool and commonly answer HTTP 429
# ("rate-limited upstream") under load, so a short bounded backoff is applied.
_POST_RETRIES = 2  # extra attempts after the first
_BACKOFF_SECONDS = (1.0, 2.0)


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------

def llm_ready() -> tuple[bool, str]:
    """Cheap, non-blocking probe for /meta. (Ready, reason) — no HTTP call."""
    if not settings.enable_llm_analysis:
        return False, "disabled by config (enable_llm_analysis=false)"
    if not settings.openrouter_api_key:
        return False, "no OPENROUTER_API_KEY configured"
    return True, ""


def llm_model() -> str:
    """Model id currently configured for OpenRouter."""
    return settings.openrouter_model


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def analyze_transcript_ai(
    transcript: str,
    signals: dict[str, Any] | None = None,
    risk: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Ask the LLM for a structured scam verdict on a transcript.

    Returns the ``{"status": "ok", ...}`` dict, or ``None`` when the AI layer
    is disabled/unconfigured, the transcript is too short, or any step of the
    external call fails. Never raises.
    """
    ready, _ = llm_ready()
    if not ready:
        return None
    text = (transcript or "").strip()
    if len(text) < _MIN_TRANSCRIPT_CHARS:
        return None

    payload = _build_payload(text, signals or {}, risk or {})
    try:
        content = _post_json(payload)
    except Exception:  # noqa: BLE001  (transport/parse hiccup -> fall back)
        return None
    if not content:
        return None

    verdict = _parse_verdict(content)
    if verdict is None:
        return None
    return {"status": "ok", "model": llm_model(), "verdict": verdict}


# ---------------------------------------------------------------------------
# Prompt / request construction
# ---------------------------------------------------------------------------

def _build_payload(text: str, signals: dict[str, Any], risk: dict[str, Any]) -> dict:
    risk_level = (risk or {}).get("level", "unknown")
    risk_score = (risk or {}).get("score")
    risk_line = f"- overall local risk: {risk_level}"
    if risk_score is not None:
        risk_line += f" ({risk_score}/100)"

    user = (
        "TRANSCRIPT:\n"
        f"{text[: settings.llm_max_transcript_chars]}\n\n"
        "LOCAL DETECTOR SIGNALS:\n"
        f"{_summarize_signals(signals)}\n"
        f"{risk_line}\n\n"
        "Reply with ONLY the JSON object."
    )
    return {
        "model": settings.openrouter_model,
        "temperature": 0,
        "max_tokens": 600,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
    }


def _summarize_signals(signals: dict[str, Any]) -> str:
    """One-line-per-signal summary so the LLM sees what the local models saw."""
    lines: list[str] = []
    for name in ("asr", "voice", "video", "text"):
        sig = (signals or {}).get(name) or {}
        label = sig.get("label") or "n/a"
        score = sig.get("score")
        engine = sig.get("engine")
        line = f"- {name}: label={label}"
        if score is not None:
            line += f" score={float(score):.3f}"
        if engine:
            line += f" engine={engine}"
        lines.append(line)
    return "\n".join(lines) if lines else "no detector signals"


# ---------------------------------------------------------------------------
# Transport (stdlib only)
# ---------------------------------------------------------------------------

def _post_json(payload: dict) -> str | None:
    """POST to OpenRouter and return the assistant message text (or None).

    Applies a short bounded backoff on HTTP 429 (rate-limited free tier).
    Kept as a module function so tests can monkeypatch it without a network.
    """
    url = f"{settings.openrouter_base_url.rstrip('/')}/chat/completions"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key or ''}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    for attempt in range(_POST_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=settings.llm_timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return _extract_content(data)
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < _POST_RETRIES:
                time.sleep(_BACKOFF_SECONDS[min(attempt, len(_BACKOFF_SECONDS) - 1)])
                continue
            return None
        except Exception:  # noqa: BLE001  (timeout / other HTTP / bad JSON)
            return None
    return None


def _extract_content(data: dict) -> str | None:
    """Pull the assistant text out of an OpenRouter chat/completions response."""
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    return content if isinstance(content, str) else None


# ---------------------------------------------------------------------------
# Reply parsing (tolerant of free models that ignore response_format)
# ---------------------------------------------------------------------------

def _parse_verdict(text: str) -> dict[str, Any] | None:
    """Extract the verdict JSON from the model's raw reply.

    Tries a direct ``json.loads`` first, then locates the first balanced
    ``{...}`` (skipping JSON strings) to handle markdown fences or prose that
    some free models wrap around the object.
    """
    if not text:
        return None
    try:
        obj = json.loads(text)
        return _norm_verdict(obj)
    except Exception:  # noqa: BLE001
        pass

    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    end = -1
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        return None
    try:
        obj = json.loads(text[start : end + 1])
    except Exception:  # noqa: BLE001
        return None
    return _norm_verdict(obj)


def _norm_verdict(obj: Any) -> dict[str, Any] | None:
    """Validate/normalise the model's JSON into the canonical verdict shape."""
    if not isinstance(obj, dict):
        return None
    is_scam = bool(obj.get("is_scam", False))
    try:
        conf = float(obj.get("confidence", 0.0))
    except (TypeError, ValueError):
        conf = 0.0
    conf = min(1.0, max(0.0, conf))

    category = obj.get("scam_category")
    if category is not None and not isinstance(category, str):
        category = None

    indicators = obj.get("key_indicators")
    if not isinstance(indicators, list):
        indicators = []
    indicators = [str(i)[:200] for i in indicators[:10]]

    explanation = obj.get("explanation")
    exp_en = str(obj.get("explanation_en") or (explanation.get("en") if isinstance(explanation, dict) else None) or "")
    exp_hi = str(obj.get("explanation_hi") or (explanation.get("hi") if isinstance(explanation, dict) else None) or exp_en)

    return {
        "is_scam": is_scam,
        "confidence": round(conf, 3),
        "scam_category": category,
        "key_indicators": indicators,
        "explanation": {"en": exp_en, "hi": exp_hi},
    }
