# DigiRaksha — User Guide

DigiRaksha is an AI-powered tool that helps you detect **Digital Arrest scams**, **deepfake voice/video fraud**, and other telecommunication scams. It analyses suspicious call recordings, voice notes, or video clips and gives you an explainable risk score with actionable next steps.

> **Available in English and Hindi** — toggle the language using the 🌐 button in the navigation bar.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Analyse a Suspicious Call](#analyse-a-suspicious-call)
  - [Option A: Paste a Transcript](#option-a-paste-a-transcript)
  - [Option B: Upload a Recording](#option-b-upload-a-recording)
- [Understanding Your Results](#understanding-your-results)
  - [Risk Score & Level](#risk-score--level)
  - [Red Flags](#red-flags)
  - [Next Steps](#next-steps)
  - [Detector Details](#detector-details)
- [Family Safe-Voice Registry](#family-safe-voice-registry)
  - [Adding a Family Member](#adding-a-family-member)
  - [Enrolling a Voice](#enrolling-a-voice)
  - [Verifying a Suspicious Call](#verifying-a-suspicious-call)
- [Scan History](#scan-history)
- [Supported File Formats](#supported-file-formats)
- [FAQ](#faq)

---

## Getting Started

1. Open DigiRaksha in your browser (the URL will be provided by your system administrator, e.g. `http://localhost:8000`).
2. You'll see the **Analyse** page by default.
3. Switch between English (EN) and Hindi (HI) using the language toggle in the top navigation.

---

## Analyse a Suspicious Call

### Option A: Paste a Transcript

Use this when you have the text of a suspicious call (from notes, a transcription service, or your own typing).

1. Click the **"Paste transcript"** tab.
2. Paste the call transcript into the text area.
3. (Optional) Select the language if you know it, or leave it on **"Auto-detect"**.
4. Click **"Analyse"**.

### Option B: Upload a Recording

Use this when you have an audio recording (.wav, .mp3, .m4a, .ogg, .flac) or video clip (.mp4, .mov, .webm) — including WhatsApp and Telegram voice notes.

1. Click the **"Upload recording / video"** tab.
2. Either:
   - **Drag and drop** the file onto the upload area, or
   - **Click** the upload area and browse for the file.
3. Click **"Upload & analyse"**.
4. Wait while the system processes your file. You'll see progress updates:
   - Uploading → Transcribing → Checking voice authenticity → Scanning video → Matching scam patterns → Done.

---

## Understanding Your Results

### Risk Score & Level

After analysis, you'll see a risk gauge showing:

| Level | Score Range | Meaning |
|-------|-------------|---------|
| 🟢 **Low risk** | 0–39 | No strong fraud signals detected. Stay cautious with unknown callers. |
| 🟡 **Medium risk** | 40–64 | Some caution signals found. Verify the caller through an independent channel before acting. |
| 🔴 **High risk** | 65–100 | Strong indicators of a scam. Hang up immediately, do not share any information, and report. |

### Red Flags

The **"Why this was flagged"** section lists specific concerns raised by the detectors:

- **🔴 Critical** — Strong evidence of fraud (e.g., AI-generated voice detected, known scam script matched).
- **🟡 Warning** — Suspicious signals that warrant caution (e.g., voice manipulation signs, video irregularities).
- **ℹ️ Info** — Informational notes (e.g., audio quality limited the analysis).

Each red flag includes a detailed explanation in your chosen language.

### Next Steps

The **"What to do next"** section gives you specific, actionable guidance based on the risk level:

- **Verify through official channels** — Hang up and independently call the organisation the caller claims to represent.
- **Never share OTP/PIN/UPI** — No genuine authority asks for these over a call.
- **Report to 1930** — Call the national cyber crime helpline immediately if money has been lost.
- **File a complaint** — Report at [cybercrime.gov.in](https://cybercrime.gov.in).
- **Contact a trusted person** — Talk to family or local police before acting on urgent money requests.

### Detector Details

The **"Detector details"** section shows which AI models ran and their individual findings:

- **ASR** — Speech-to-text transcription (Whisper model)
- **Voice** — AI/deepfake voice detection (AASIST anti-spoofing model)
- **Video** — Video frame analysis for deepfake tampering
- **Text** — Scam language pattern matching (ML classifier)

A detector marked as "not available" means it couldn't run (e.g., no speech detected, or the optional model isn't loaded).

---

## Family Safe-Voice Registry

This is a **proactive** feature. By enrolling your family members' real voices ahead of time, you can instantly check if a suspicious "this is your relative in trouble" call is genuine.

Navigate to **Safe-Voice Registry** in the navigation bar.

### Adding a Family Member

1. Click **"Add family member"**.
2. Enter their **name** and **relationship** (optional).
3. Optionally add their **phone number** and a **note**.
4. Click **"Add member"**.

### Enrolling a Voice

After adding a member, you need to enrol at least one voice sample:

1. Click **"Enrol voice"** next to the family member's name.
2. Upload a recording of their voice (a voice note, phone recording, etc.).
3. The system extracts a speaker fingerprint (MFCC embedding) from the audio.

**Tip:** Enrol 2–3 samples from different recordings for more reliable matching.

### Verifying a Suspicious Call

When you receive a call claiming to be from a family member:

1. Go to the family member's entry in the registry.
2. Click **"Verify a call"**.
3. Upload the suspicious voice note or recording.
4. The system compares it against the enrolled voice(s).

**Results:**

- ✅ **Matches** — The voice similarity is above the threshold. The caller is likely who they claim to be.
- ❌ **Does NOT match** — The voice doesn't match the enrolled sample. This may be a **deepfake clone**. Do not trust the caller.

---

## Scan History

The **History** page shows all your past analyses, including:

- **Time** of the analysis
- **Type** (audio, video, or text)
- **File** name (if uploaded)
- **Risk level** (low/medium/high with score)

Click **"view detail"** to see the full analysis result for any past scan.

---

## Supported File Formats

| Type | Formats |
|------|---------|
| Audio | `.wav`, `.mp3`, `.m4a`, `.ogg`, `.flac` |
| Video | `.mp4`, `.mov`, `.webm` |
| Text | Paste directly into the transcript field |

**Constraints:**
- Maximum file size: 50 MB
- Maximum duration: 10 minutes (600 seconds)

---

## FAQ

**Q: Does my data leave my server?**
A: No. All analysis runs locally on your server. No data is sent to external services.

**Q: What if the AI model isn't loaded?**
A: The system degrades gracefully. Missing detectors are marked "not available" and the risk score is calculated from whichever detectors are active.

**Q: Can I use this on my phone?**
A: Yes. The frontend is responsive and works on mobile browsers.

**Q: Why does a benign TTS recording show "medium risk"?**
A: The voice anti-spoofing model (AASIST) correctly identifies text-to-speech as synthetic. This is expected behaviour — it means the model is working. Real human voices will score low.

**Q: What languages are supported?**
A: The UI supports English and Hindi. The ASR model auto-detects the language of the audio. The scam classifier works with English, Hindi, and Hinglish transcripts.

**Q: Is this a replacement for police reporting?**
A: No. DigiRaksha is an **awareness and triage tool**. Always report scam calls to the police via [1930](tel:1930) or [cybercrime.gov.in](https://cybercrime.gov.in).
