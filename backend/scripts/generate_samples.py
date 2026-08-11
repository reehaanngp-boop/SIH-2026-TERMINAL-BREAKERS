"""Generate demo audio samples with offline TTS (pyttsx3 / Windows SAPI5).

Produces scam and benign call clips under ``data/samples/`` together with a
``manifest.json`` mapping each file to its script and expected verdict, so the
demo script and e2e checks can reference them deterministically.

Run:  .venv/Scripts/python.exe scripts/generate_samples.py
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "data" / "samples"

# (filename, category, transcript, expected)
SAMPLES: list[dict] = [
    {
        "file": "scam_digital_arrest.wav",
        "category": "digital_arrest",
        "expected": "high",
        "transcript": (
            "Hello, this is the Central Bureau of Investigation. A case has been registered "
            "against you for money laundering. You are under digital arrest. You must stay on "
            "this video call until the verification is complete. Pay the verification fee "
            "immediately or the police will arrest you. Do not tell anyone about this "
            "investigation."
        ),
    },
    {
        "file": "scam_courier.wav",
        "category": "fake_courier",
        "expected": "high",
        "transcript": (
            "Good morning. Your international courier parcel has been stopped at customs. "
            "A parcel sent in your name contains drugs and foreign currency. The narcotics "
            "control bureau has opened a case about your parcel. You need to pay the customs "
            "clearance fee to release the parcel today itself."
        ),
    },
    {
        "file": "scam_otp.wav",
        "category": "otp_phishing",
        "expected": "high",
        "transcript": (
            "Namaste, this is your bank calling. Your account has been blocked due to "
            "suspicious activity. Your KYC is incomplete and your account will be frozen. "
            "Share the OTP you received to verify your account immediately."
        ),
    },
    {
        "file": "benign_restaurant.wav",
        "category": "benign",
        "expected": "low",
        "note": (
            "TTS audio is itself synthetic, so AASIST flags the *voice* as AI-generated "
            "(medium overall). A real human voice scores low — demonstrate low risk with "
            "the transcript mode instead."
        ),
        "transcript": (
            "Good afternoon. This is the restaurant calling to confirm your food order. "
            "Your order will be delivered in twenty minutes. Thank you."
        ),
    },
    {
        "file": "benign_family.wav",
        "category": "benign",
        "expected": "low",
        "note": (
            "TTS audio is itself synthetic, so AASIST flags the *voice* as AI-generated "
            "(medium overall). A real human voice scores low — demonstrate low risk with "
            "the transcript mode instead."
        ),
        "transcript": (
            "Hi dad, it's me. I will reach home by evening. No need to worry. "
            "The train is on time. I'll see you soon."
        ),
    },
]


def synthesize(transcript: str, out_path: Path) -> bool:
    import pyttsx3

    engine = pyttsx3.init()
    try:
        voices = engine.getProperty("voices")
        # Prefer a clear en-IN/en-US voice if available.
        for v in voices:
            if "en" in (v.id or "").lower() and ("in" in (v.id or "").lower() or "david" in (v.id or "").lower()):
                engine.setProperty("voice", v.id)
                break
        engine.setProperty("rate", 150)
        engine.save_to_file(transcript, str(out_path))
        engine.runAndWait()
    finally:
        engine.stop()
    return out_path.exists() and out_path.stat().st_size > 0


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    for s in SAMPLES:
        out = OUT_DIR / s["file"]
        ok = synthesize(s["transcript"], out)
        print(f"[{'ok ' if ok else 'FAIL'}] {s['file']} ({out.stat().st_size if ok else 0} bytes)")
        s["duration_seconds"] = None
        manifest.append(s)

    with (OUT_DIR / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"Manifest -> {OUT_DIR / 'manifest.json'}")


if __name__ == "__main__":
    main()
