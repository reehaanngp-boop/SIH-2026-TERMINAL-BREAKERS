"""Diagnose Safe-Voice Registry false matches.

Computes the pairwise cosine-similarity matrix of the current 52-D MFCC-stats
embedding across a set of *distinct* uploaded recordings, and flags every pair
that would be accepted as a "match" under the configured threshold.

Run:  C:\\dr-venv\\Scripts\\python.exe scripts\\diag_voice_similarity.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.config import get_settings  # noqa: E402
from app.detectors.audio.audio_utils import load_audio_16k  # noqa: E402
from app.detectors.audio.speaker_verify import (  # noqa: E402
    compute_embedding,
    cosine_similarity,
    embedding_engine,
)

settings = get_settings()
UPLOADS = Path(settings.upload_dir)


def main() -> None:
    # One representative per distinct size, then a few extra 1 s clips (same size
    # can still be different recordings).
    files = sorted(UPLOADS.glob("*.*"))
    seen_sizes: set[int] = set()
    picks: list[Path] = []
    for f in files:
        if f.suffix.lower() not in (".wav", ".m4a", ".mp3"):
            continue
        sz = f.stat().st_size
        if sz not in seen_sizes or len([p for p in picks if p.stat().st_size == sz]) < 3:
            seen_sizes.add(sz)
            picks.append(f)
    picks = picks[:12]

    print(f"threshold = {settings.verify_similarity_threshold}")
    print(f"engine    = {embedding_engine()}")
    print(f"{'#':<3} {'file':<48} {'dur':>5} {'size':>9}")
    embeds: dict[int, list[float]] = {}
    for i, f in enumerate(picks):
        try:
            audio = load_audio_16k(f)
            emb = compute_embedding(audio)
        except Exception as exc:  # noqa: BLE001
            print(f"ERR {i:<2} {f.name:<48} {exc}")
            continue
        embeds[i] = emb
        print(f"{i:<3} {f.name:<48} {audio.duration:>5.2f} {f.stat().st_size:>9}")

    print("\nCosine-similarity matrix (rows x cols); '*' = accepted match at threshold:")
    idx = sorted(embeds)
    n = len(idx)
    print("   " + " ".join(f"{j:>7}" for j in range(n)))
    false_accepts = 0
    pairs = 0
    for r in range(n):
        row = []
        for c in range(n):
            if r == c:
                row.append("    1.00")
                continue
            sim = cosine_similarity(embeds[idx[r]], embeds[idx[c]])
            match = sim >= settings.verify_similarity_threshold
            if match:
                false_accepts += 1
            pairs += 1
            row.append(f"{'*' if match else ' '}{sim:>6.3f}")
        print(f"{r:<3} " + " ".join(row))

    print(f"\nDistinct pairs compared: {pairs};  FALSE ACCEPTS: {false_accepts} "
          f"({100.0 * false_accepts / pairs:.1f}%)")


if __name__ == "__main__":
    main()
