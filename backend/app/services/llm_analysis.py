"""AI analysis layer backed by OpenRouter LLM API.

Provides:
1. Structured second-opinion corroboration for scam calls and transcripts.
2. DigiRaksha AI Scam Defense Copilot (multi-turn conversational assistant).
3. Cyber Crime FIR / 1930 Complaint drafting assistant.
4. Quick SMS / WhatsApp message triage.

Features resilient multi-model failover, timeout protection, and bilingual
(English & Hindi) explainability.
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

_ASSISTANT_SYSTEM_PROMPT = (
    "You are the DigiRaksha AI Cyber & Legal Defense Assistant (डिजीरक्षा AI सहायक) — "
    "a specialized AI copilot created for Smart India Hackathon 2026 to protect Indian "
    "citizens and assist cyber cell officers against Digital Arrest, Deepfake Voice/Video scams, "
    "and telecom financial fraud.\n\n"
    "Your core mission and factual grounding:\n"
    "1. DIGITAL ARREST DEBUNKING: There is NO concept of 'Digital Arrest' in the Bharatiya Nyaya "
    "Sanhita (BNS), Code of Criminal Procedure (CrPC), or Indian Law. No police agency (CBI, ED, "
    "NCB, Cyber Crime Police, Mumbai/Delhi Police) or Supreme Court judge conducts arrests or court "
    "hearings over Skype, WhatsApp, or video calls. Police never demand verification fees, security "
    "deposits, or fund transfers to 'RBI clearance accounts'.\n"
    "2. EMERGENCY ACTION PROTOCOL: If someone is on a live suspect call: advise them to hang up immediately, "
    "block the number, preserve recordings/screenshots, call National Cyber Crime Helpline 1930 within the "
    "golden hour (first 2-3 hours to freeze money in transit), and file a report at cybercrime.gov.in.\n"
    "3. LEGAL CITATIONS: Reference relevant Indian laws accurately when asked (e.g. IT Act Section 66D for "
    "cheating by personation using computer resource, BNS Section 318(4) for cheating, BNS Section 319 for cheating "
    "by personation, Indian Telegraph Act / DoT Chakshu portal for suspicious telecom communications).\n"
    "4. TONE & STYLE: Clear, empathetic, authoritative, calming, and highly practical. Provide concrete bullet points "
    "and step-by-step actions. Support English, Hindi, and Hinglish naturally depending on user query."
)

_MIN_TRANSCRIPT_CHARS = 20
_POST_RETRIES = 2
_BACKOFF_SECONDS = (0.2, 0.5)


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------

def llm_ready(api_key: str | None = None) -> tuple[bool, str]:
    """Cheap, non-blocking probe for /meta. (Ready, reason) — no HTTP call."""
    key = api_key or settings.openrouter_api_key
    if not settings.enable_llm_analysis and not key:
        return False, "disabled by config (enable_llm_analysis=false)"
    if not key:
        return False, "no OPENROUTER_API_KEY configured"
    return True, ""


def llm_model() -> str:
    """Model id currently configured for OpenRouter."""
    return settings.openrouter_model


def _get_fallback_models() -> list[str]:
    primary = settings.openrouter_model
    configured_fallbacks = [
        m.strip() for m in settings.openrouter_fallback_models.split(",") if m.strip()
    ]
    models = [primary]
    for m in configured_fallbacks:
        if m not in models:
            models.append(m)
    return models


def _call_post_json(payload: dict, api_key: str | None = None) -> str | None:
    """Helper that invokes _post_json safely even if monkeypatched with 1 argument."""
    try:
        return _post_json(payload, api_key=api_key)
    except TypeError:
        return _post_json(payload)


# ---------------------------------------------------------------------------
# Public entry point: Transcript Scam Analysis
# ---------------------------------------------------------------------------

def analyze_transcript_ai(
    transcript: str,
    signals: dict[str, Any] | None = None,
    risk: dict[str, Any] | None = None,
    api_key: str | None = None,
) -> dict[str, Any] | None:
    """Ask the LLM for a structured scam verdict on a transcript with multi-model failover."""
    ready, _ = llm_ready(api_key=api_key)
    if not ready:
        return None
    text = (transcript or "").strip()
    if len(text) < _MIN_TRANSCRIPT_CHARS:
        return None

    models = _get_fallback_models()
    key = api_key or settings.openrouter_api_key

    for model in models:
        payload = _build_payload(text, signals or {}, risk or {}, model=model)
        try:
            content = _call_post_json(payload, api_key=key)
            if content:
                verdict = _parse_verdict(content)
                if verdict is not None:
                    return {"status": "ok", "model": model, "verdict": verdict}
        except Exception:
            continue

    return None


# ---------------------------------------------------------------------------
# Public entry point: AI Assistant / Copilot Chat
# ---------------------------------------------------------------------------

def chat_with_copilot(
    messages: list[dict[str, str]],
    scan_context: dict[str, Any] | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Execute multi-turn conversational AI Copilot query."""
    ready, reason = llm_ready(api_key=api_key)
    key = api_key or settings.openrouter_api_key

    # Format scan context into system prompt if provided
    system_text = _ASSISTANT_SYSTEM_PROMPT
    if scan_context:
        system_text += "\n\nACTIVE SCAN CONTEXT (from user's current DigiRaksha session):\n"
        if scan_context.get("transcript"):
            system_text += f"- Transcript: \"{scan_context['transcript'][:1500]}\"\n"
        if scan_context.get("risk"):
            system_text += f"- Risk Level: {scan_context['risk'].get('level')} (Score: {scan_context['risk'].get('score')}/100)\n"
        if scan_context.get("red_flags"):
            flag_titles = [f.get("title", {}).get("en") if isinstance(f.get("title"), dict) else str(f.get("title")) for f in scan_context["red_flags"][:5]]
            system_text += f"- Identified Red Flags: {', '.join(filter(None, flag_titles))}\n"

    chat_messages = [{"role": "system", "content": system_text}]
    for msg in messages:
        role = msg.get("role", "user")
        if role in ("user", "assistant", "system"):
            chat_messages.append({"role": role, "content": msg.get("content", "")[:3000]})

    models = [model] if model else _get_fallback_models()
    last_error = reason

    if ready:
        for m in models:
            payload = {
                "model": m,
                "temperature": 0.3,
                "max_tokens": 1200,
                "messages": chat_messages,
            }
            try:
                reply = _call_post_json(payload, api_key=key)
                if reply and reply.strip():
                    return {
                        "status": "ok",
                        "model": m,
                        "reply": reply.strip(),
                        "suggestions": _generate_smart_suggestions(reply),
                    }
            except Exception as exc:
                last_error = str(exc)
                continue

    # Offline / rule-based fallback response if API is unreachable or key missing
    last_user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user_msg = m.get("content", "").lower()
            break

    fallback_reply = _get_rule_based_assistant_reply(last_user_msg, scan_context)
    return {
        "status": "offline_fallback",
        "model": "digiraksha-offline-rulebook",
        "error": last_error,
        "reply": fallback_reply,
        "suggestions": [
            "What are my legal rights under Indian Law?",
            "How do I file a complaint on 1930?",
            "Is Digital Arrest legal in India?",
            "How to protect my bank account in the golden hour?",
        ],
    }


# ---------------------------------------------------------------------------
# Public entry point: Quick Message Triage
# ---------------------------------------------------------------------------

def quick_triage_ai(content: str, api_key: str | None = None) -> dict[str, Any]:
    """Rapid scam triage for messages, SMS, or WhatsApp scripts."""
    text = (content or "").strip()
    if not text:
        return {"is_scam": False, "category": "benign", "confidence": 0.0, "summary": "Empty content"}

    prompt = (
        f"Analyze this suspected communication received by an Indian user:\n\"{text[:2000]}\"\n\n"
        "Output JSON with keys: is_scam (bool), scam_category (string), confidence (float 0-1), "
        "summary_en (1-2 sentences), summary_hi (1-2 sentences in Hindi), "
        "urgency_level ('critical'|'high'|'medium'|'low'), recommended_action (string)."
    )

    models = _get_fallback_models()
    key = api_key or settings.openrouter_api_key

    for model in models:
        payload = {
            "model": model,
            "temperature": 0.1,
            "max_tokens": 500,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "You are a cyber security threat triage engine for DigiRaksha India."},
                {"role": "user", "content": prompt},
            ],
        }
        try:
            res = _call_post_json(payload, api_key=key)
            if res:
                obj = json.loads(res)
                return {"status": "ok", "model": model, "data": obj}
        except Exception:
            continue

    # Offline heuristic triage
    lower = text.lower()
    is_arrest = any(w in lower for w in ["digital arrest", "cbi", "ncb", "cyber police", "warrant", "skype"])
    is_otp = any(w in lower for w in ["otp", "power cut", "kyc", "apk", "anydesk", "teamviewer"])
    is_courier = any(w in lower for w in ["fedex", "customs", "mdma", "narcotics", "parcel"])

    cat = "digital_arrest" if is_arrest else ("otp_phishing" if is_otp else ("fake_courier" if is_courier else "suspicious"))
    is_scam = is_arrest or is_otp or is_courier

    return {
        "status": "offline_rule",
        "model": "digiraksha-heuristics",
        "data": {
            "is_scam": is_scam,
            "scam_category": cat,
            "confidence": 0.88 if is_scam else 0.3,
            "summary_en": f"Flagged as potential {cat.replace('_', ' ')} scam targeting Indian users." if is_scam else "No direct scam patterns identified.",
            "summary_hi": f"यह संभावित {cat} स्कैम प्रतीत होता है।" if is_scam else "कोई सीधा स्कैम पैटर्न नहीं मिला।",
            "urgency_level": "critical" if is_scam else "low",
            "recommended_action": "Do not transfer money or share personal details. Report to 1930." if is_scam else "Stay vigilant.",
        },
    }


# ---------------------------------------------------------------------------
# Public entry point: Formal Cyber Complaint / FIR Drafting
# ---------------------------------------------------------------------------

def draft_complaint_ai(
    incident_data: dict[str, Any],
    api_key: str | None = None,
) -> dict[str, Any]:
    """Generate a formal cyber crime complaint formatted for 1930 / cybercrime.gov.in."""
    prompt = (
        "Generate a formal Cyber Crime Complaint Draft suitable for submission to the National Cyber Crime "
        "Reporting Portal (cybercrime.gov.in) and for calling helpline 1930.\n\n"
        f"INCIDENT DETAILS:\n{json.dumps(incident_data, indent=2)}\n\n"
        "Include:\n"
        "1. To: The Superintendent of Police / Officer-in-Charge, Cyber Crime Police Station\n"
        "2. Subject Line (clear & formal)\n"
        "3. Complainant & Suspect Details (Phone, UPI ID, Bank Acc, App used)\n"
        "4. Factual Chronological Sequence of Incident (Modus Operandi)\n"
        "5. Applicable Legal Sections (IT Act 2000 Section 66D, BNS 2023 Section 318(4)/319)\n"
        "6. Specific Urgent Prayers / Relief Requested (Bank Account Freeze under Golden Hour, SIM block via Chakshu, FIR registration)\n"
        "Format cleanly in Markdown with bold headers."
    )

    models = _get_fallback_models()
    key = api_key or settings.openrouter_api_key

    for model in models:
        payload = {
            "model": model,
            "temperature": 0.2,
            "max_tokens": 1500,
            "messages": [
                {"role": "system", "content": _ASSISTANT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }
        try:
            complaint_text = _call_post_json(payload, api_key=key)
            if complaint_text and complaint_text.strip():
                return {"status": "ok", "model": model, "complaint_markdown": complaint_text.strip()}
        except Exception:
            continue

    # Fallback template
    victim = incident_data.get("victim_name", "Complainant")
    suspect_num = incident_data.get("suspect_phone", "Unknown")
    scam_type = incident_data.get("scam_type", "Digital Arrest / Impersonation Scam")
    amount = incident_data.get("amount_lost", "N/A")
    date_time = incident_data.get("date_time", "Recent")
    transcript = incident_data.get("transcript", "")

    fallback_doc = f"""# FORMAL CYBER CRIME COMPLAINT

**To:**  
The Officer-in-Charge / Superintendent of Police,  
Cyber Crime Investigation Cell / National Cyber Crime Reporting Portal (cybercrime.gov.in)  
**Helpline Reference:** 1930  

---

**SUBJECT:** Complaint regarding cyber fraud, criminal impersonation, and fraudulent intimidation under the guise of **{scam_type}**

### 1. COMPLAINANT INFORMATION
- **Name:** {victim}
- **Contact:** [Your Contact Number]
- **Address:** [Your Address / City]

### 2. SUSPECT / ACCUSED DETAILS
- **Suspect Phone Number(s):** {suspect_num}
- **Impersonated Authority:** CBI / Narcotics Control Bureau / Cyber Police / Customs
- **Medium Used:** WhatsApp / Skype / Telephony Call
- **Suspect Bank / UPI details:** {incident_data.get("suspect_upi", "Provided in evidence attachments")}

### 3. CHRONOLOGICAL STATEMENT OF FACTS
1. On or about **{date_time}**, the complainant received an unsolicited communication from the suspect(s).
2. The suspect fraudulently claimed that an arrest warrant, seized narcotic consignment, or illegal bank account was registered in the complainant's name.
3. The caller placed the complainant under coerced 'Digital Arrest' via video communication, preventing the complainant from contacting family or legal counsel.
4. Total financial demand / loss incurred: **₹{amount}**.

### 4. RELEVANT LEGAL PROVISIONS
- **Section 66D, Information Technology Act, 2000** (Cheating by personation using computer resource)
- **Section 318(4), Bharatiya Nyaya Sanhita, 2023** (Cheating and dishonestly inducing delivery of property)
- **Section 319, Bharatiya Nyaya Sanhita, 2023** (Cheating by personation)
- **Section 351, Bharatiya Nyaya Sanhita, 2023** (Criminal Intimidation)

### 5. PRAYER / RELIEF REQUESTED
1. Immediate flagging and debit-freezing of the suspect's beneficiary account under the **Golden Hour Interdiction Mechanism (1930 / I4C)**.
2. Blocking of the suspect mobile numbers via the **DoT Sanchar Saathi (Chakshu)** portal.
3. Registration of an FIR and investigation to apprehend the criminal syndicate.

**Date:** [Date]  
**Signature:** __________________________  
"""
    return {"status": "offline_template", "model": "digiraksha-legal-template", "complaint_markdown": fallback_doc}


# ---------------------------------------------------------------------------
# Prompt / request construction
# ---------------------------------------------------------------------------

def _build_payload(text: str, signals: dict[str, Any], risk: dict[str, Any], model: str | None = None) -> dict:
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
        "model": model or settings.openrouter_model,
        "temperature": 0,
        "max_tokens": 600,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
    }


def _summarize_signals(signals: dict[str, Any]) -> str:
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

def _post_json(payload: dict, api_key: str | None = None) -> str | None:
    url = f"{settings.openrouter_base_url.rstrip('/')}/chat/completions"
    body = json.dumps(payload).encode("utf-8")
    key = api_key or settings.openrouter_api_key or ""
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/reehaanngp-boop/SIH-2026-TERMINAL-BREAKERS",
            "X-Title": "DigiRaksha AI Shield",
        },
        method="POST",
    )
    for attempt in range(_POST_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=settings.llm_timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return _extract_content(data)
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503) and attempt < _POST_RETRIES:
                time.sleep(_BACKOFF_SECONDS[min(attempt, len(_BACKOFF_SECONDS) - 1)])
                continue
            return None
        except Exception:
            return None
    return None


def _extract_content(data: dict) -> str | None:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    return content if isinstance(content, str) else None


# ---------------------------------------------------------------------------
# Reply parsing
# ---------------------------------------------------------------------------

def _parse_verdict(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    try:
        obj = json.loads(text)
        return _norm_verdict(obj)
    except Exception:
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
        return _norm_verdict(obj)
    except Exception:
        return None


def _norm_verdict(obj: Any) -> dict[str, Any] | None:
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


def _generate_smart_suggestions(reply: str) -> list[str]:
    """Generate intelligent follow-up query suggestions based on response content."""
    lower = reply.lower()
    suggestions = []
    if "digital arrest" in lower or "cbi" in lower or "police" in lower:
        suggestions.append("Draft a formal cyber complaint for 1930 / FIR")
        suggestions.append("How do I verify if a police officer's call is genuine?")
    if "bank" in lower or "transfer" in lower or "money" in lower or "upi" in lower:
        suggestions.append("What is the Golden Hour protocol for frozen accounts?")
        suggestions.append("How to report a fraudulent UPI transaction?")
    if "deepfake" in lower or "voice" in lower or "clone" in lower:
        suggestions.append("How does the Safe-Voice Registry verify family members?")
        suggestions.append("What are the acoustic signs of an AI cloned voice?")

    if not suggestions:
        suggestions = [
            "What should I do if a scammer is threatening me right now?",
            "What are the official helpline channels in India?",
            "How do I block a scammer's SIM on Chakshu?",
        ]
    return suggestions[:4]


def _get_rule_based_assistant_reply(query: str, context: dict | None = None) -> str:
    """Accurate offline knowledge base for Indian cyber crime emergencies."""
    q = query.lower()

    if "digital arrest" in q or "arrest" in q or "cbi" in q or "warrant" in q:
        return (
            "🚨 **CRITICAL ADVISORY: DIGITAL ARREST IS 100% FAKE**\n\n"
            "1. **No Legal Provision**: Under Indian Law (Bharatiya Nyaya Sanhita, CrPC, IT Act), **there is NO such thing as 'Digital Arrest'**.\n"
            "2. **Official Police SOP**: No legitimate police agency (CBI, ED, Cyber Crime, Narcotics Control Bureau, State Police) will EVER arrest someone over Skype, WhatsApp, or video call.\n"
            "3. **No Money Transfers for Clearance**: Police, judges, or investigating officers will **NEVER** ask you to transfer funds to a 'security account', 'verification account', or 'RBI clearance pool'.\n\n"
            "**IMMEDIATE STEPS TO TAKE:**\n"
            "- Disconnect the call immediately. Do not stay on camera.\n"
            "- Block the phone number.\n"
            "- Dial **1930** immediately or report at **[cybercrime.gov.in](https://cybercrime.gov.in)**.\n"
            "- If any money was transferred, notify your bank immediately to initiate a lien/freeze under the **Golden Hour** mechanism."
        )

    if "1930" in q or "complaint" in q or "report" in q or "fir" in q:
        return (
            "📋 **HOW TO REPORT FINANCIAL FRAUD & FILE AN FIR:**\n\n"
            "1. **Call 1930 Helpline**: Call **1930** (operated by I4C, Ministry of Home Affairs). Have the following ready:\n"
            "   - Time of transaction\n"
            "   - Debit account number & bank name\n"
            "   - Suspect UPI ID / Beneficiary account number\n"
            "   - Transaction Reference Number (UTR / RRN)\n"
            "2. **Golden Hour Rule**: If reported within **2 to 3 hours**, the National Cybercrime Reporting Portal triggers an automated inter-bank freeze preventing fraudsters from withdrawing funds.\n"
            "3. **File on cybercrime.gov.in**: Register a formal complaint under 'Report Financial Fraud'. Attach call screenshots and transaction receipts.\n"
            "4. **Report to Telecom (Chakshu)**: Report the scammer's phone number on the DoT Sanchar Saathi **Chakshu portal** to get their SIM and device IMEI blacklisted."
        )

    if "voice" in q or "clone" in q or "deepfake" in q or "family" in q:
        return (
            "🎙️ **AI VOICE CLONING & KIN EMERGENCY SCAMS:**\n\n"
            "Scammers now use 3-second audio clips from social media to clone voices of children, spouses, or relatives and stage fake kidnappings or accidents.\n\n"
            "**HOW TO DEFEND:**\n"
            "1. **Code Word Technique**: Agree on a private family security word that only real family members know.\n"
            "2. **Hang Up and Call Directly**: Always call the relative back directly on their known, saved phone number before sending any money.\n"
            "3. **DigiRaksha Safe-Voice Registry**: Use the Safe-Voice Registry tab in this app to pre-enrol your family members' voiceprints. When an emergency voice note arrives, verify it instantly."
        )

    return (
        "🛡️ **DigiRaksha AI Shield is Active.**\n\n"
        "I can assist you with:\n"
        "- **Scam Analysis**: Paste any call transcript, SMS, or WhatsApp forward to evaluate risk.\n"
        "- **Legal Guidance**: Check your rights under the Information Technology Act and Indian cyber laws.\n"
        "- **Emergency Protocol**: Get step-by-step guidance on how to freeze bank accounts and file 1930 / FIR reports.\n"
        "- **Safe-Voice Verification**: Advice on combating AI deepfake voice cloning."
    )
