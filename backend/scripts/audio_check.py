"""Run the full media pipeline over the bundled sample clips.

Verifies the voice detector (AASIST + calibrated heuristics) and the whole
ASR -> voice -> text -> risk chain on real audio files.

Run:  C:\\dr-venv\\Scripts\\python.exe scripts\\audio_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.pipeline import get_pipeline  # noqa: E402

SAMPLES = BACKEND.parent / "data" / "samples"


def main() -> None:
    pipeline = get_pipeline()
    wavs = sorted(SAMPLES.glob("*.wav"))
    if not wavs:
        print("No sample clips found under", SAMPLES)
        return
    print(f"{'clip':<28} {'risk':<7} {'score':>5}  voice(engine:score:label)  text")
    print("-" * 90)
    for wav in wavs:
        res = pipeline.analyze_media("audio", str(wav), wav.name)
        risk = res["risk"]
        voice = res["signals"]["voice"]
        text = res["signals"]["text"]
        print(
            f"{wav.name:<28} {risk['level']:<7} {risk['score']:>5.1f}  "
            f"{voice.get('engine')}:{voice.get('score')}:{voice.get('label'):<20} "
            f"{text.get('label')}"
        )


if __name__ == "__main__":
    main()
