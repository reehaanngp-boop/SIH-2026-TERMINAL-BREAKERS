"""Download pretrained models for DigiRaksha AI Scam Shield."""

import sys
import os
from pathlib import Path

# Add backend root to sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.detectors.audio.dhwani_detector import download_dhwani_model

if __name__ == "__main__":
    print("=======================================================")
    print("  Downloading Dhwani Multilingual Voice Clone Model... ")
    print("=======================================================")
    try:
        saved_path = download_dhwani_model()
        size_mb = saved_path.stat().st_size / (1024 * 1024)
        print(f"\n[SUCCESS] Model downloaded to: {saved_path} ({size_mb:.1f} MB)")
    except Exception as exc:
        print(f"\n[ERROR] Failed to download model: {exc}")
        sys.exit(1)
