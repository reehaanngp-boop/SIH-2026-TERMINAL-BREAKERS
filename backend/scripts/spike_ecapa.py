"""Spike: load SpeechBrain ECAPA-TDNN and embed real recordings.

Run:  C:\\dr-venv\\Scripts\\python.exe scripts\\spike_ecapa.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import torch  # noqa: E402
from speechbrain.inference.speaker import EncoderClassifier  # noqa: E402
from speechbrain.utils.fetching import LocalStrategy  # noqa: E402


def main() -> None:
    t0 = time.time()
    classifier = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir=Path.home() / ".cache" / "digiraksha" / "ecapa",
        run_opts={"device": "cpu"},
        local_strategy=LocalStrategy.COPY,
    )
    print(f"model loaded in {time.time() - t0:.1f}s")

    from app.detectors.audio.audio_utils import load_audio_16k
    from app.detectors.audio.speaker_verify import cosine_similarity

    root = BACKEND.parent
    files = [
        root / "data" / "samples" / "benign_family.wav",
        root / "data" / "samples" / "benign_restaurant.wav",
        root / "data" / "samples" / "scam_digital_arrest.wav",
    ]
    ups = list((root / "data" / "uploads").glob("*.m4a"))[:3]
    files += ups

    embeds = []
    for f in files:
        audio = load_audio_16k(f)
        wav = torch.from_numpy(audio.samples.astype("float32")).unsqueeze(0)
        with torch.no_grad():
            emb = classifier.encode_batch(wav, wav_lens=torch.ones(1))
        emb = emb.squeeze().numpy()
        emb = emb / max(float(emb.std()) * 1e-6, 1e-9)  # rough norm guard
        emb = emb / (float((emb ** 2).sum()) ** 0.5 + 1e-12)
        embeds.append(emb)
        print(f"{f.name:<42} {audio.duration:>5.2f}s  emb_dim={emb.shape[0]}  |e|={float((emb**2).sum())**0.5:.4f}")

    print("\nECAPA cosine matrix (different files = different content):")
    for r in range(len(files)):
        row = []
        for c in range(len(files)):
            row.append(f"{cosine_similarity(embeds[r], embeds[c]):.3f}")
        print("  " + " ".join(row))


if __name__ == "__main__":
    main()
