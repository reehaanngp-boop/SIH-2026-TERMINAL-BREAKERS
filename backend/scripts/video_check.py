"""End-to-end check for the video deepfake path (MesoNet + risk engine).

Generates a small synthetic video (no real face) and runs:
  1. VideoDeepfakeDetector.analyze()  -> must complete, carry an `engine` field,
     and report `video_engine` in metrics (either "mesonet" or "unavailable").
  2. risk_engine.assess(video=...)    -> must not error and must stay <= medium
     when video is the only signal.

The model-backed per-crop scoring path is exercised by the unit test
``test_video_deepfake.py::test_mesonet_loads_and_scores_crop``; this script only
proves the video-file path end to end.

Run:  C:\\dr-venv\\Scripts\\python.exe scripts\\video_check.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from app.core import risk_engine  # noqa: E402
from app.detectors.video.deepfake import VideoDeepfakeDetector  # noqa: E402


def make_video(path: Path, seconds: float = 3.0, fps: float = 10.0) -> None:
    """Synthetic clip: a moving grey square on a dark background (no real face)."""
    w, h = 320, 240
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h)
    )
    for i in range(int(seconds * fps)):
        frame = np.zeros((h, w, 3), dtype=np.uint8) + 20
        x = int((w // 2) + 40 * np.sin(i / 3.0))
        cv2.rectangle(frame, (x - 25, 90), (x + 25, 140), (200, 200, 200), -1)
        writer.write(frame)
    writer.release()


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="digiraksha_video_check_"))
    clip = tmp / "synthetic.mp4"
    make_video(clip)

    det = VideoDeepfakeDetector()
    print(f"mesonet_available = {det.mesonet_available()}  (engine={det.describe()['engine']})")

    result = det.analyze(str(clip))
    print(f"status={result['status']}  label={result['label']}  engine={result.get('engine')}")
    print(f"metrics.video_engine = {result['metrics'].get('video_engine')}")

    assert result["status"] == "available"
    assert "engine" in result, "analyze() must carry an engine field"
    assert result["metrics"].get("video_engine") in ("mesonet", "unavailable")

    verdict = risk_engine.assess(media_type="video", video=result)
    print(f"overall risk = {verdict['risk']['score']} ({verdict['risk']['level']})")
    assert verdict["risk"]["level"] in ("low", "medium"), "video alone must never reach high"
    print("OK — video path verified end to end.")


if __name__ == "__main__":
    main()
