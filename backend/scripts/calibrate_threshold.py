"""Calibrate the speaker-verification threshold.

Synthesises the SAME sentence with every installed Windows SAPI voice (same
content, different speakers) plus different sentences with the SAME voice
(same speaker, different content), embeds them with ECAPA-TDNN and prints the
cosine matrix so a decision threshold can be picked that separates the two.

Run:  C:\\dr-venv\\Scripts\\python.exe scripts\\calibrate_threshold.py
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import torch  # noqa: E402
from speechbrain.inference.speaker import EncoderClassifier  # noqa: E402
from speechbrain.utils.fetching import LocalStrategy  # noqa: E402

from app.detectors.audio.audio_utils import load_audio_16k  # noqa: E402
from app.detectors.audio.speaker_verify import cosine_similarity  # noqa: E402

SENTENCE_A = "Hello, I am calling to confirm my order. Please verify before paying."
SENTENCE_B = "The meeting has been moved to three pm today. I will reach home by evening."


def load_classifier() -> EncoderClassifier:
    savedir = Path.home() / ".cache" / "digiraksha" / "ecapa"
    return EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir=str(savedir),
        run_opts={"device": "cpu"},
        local_strategy=LocalStrategy.COPY,
    )


def synth(voice_id: str, text: str, out: Path) -> bool:
    import pyttsx3

    engine = pyttsx3.init()
    try:
        engine.setProperty("voice", voice_id)
        engine.setProperty("rate", 150)
        engine.save_to_file(text, str(out))
        engine.runAndWait()
    finally:
        engine.stop()
    return out.exists() and out.stat().st_size > 0


def embed(classifier, audio) -> list[float]:
    wav = torch.from_numpy(audio.samples.astype("float32")).unsqueeze(0)
    with torch.no_grad():
        emb = classifier.encode_batch(wav, wav_lens=torch.ones(1))
    emb = emb.squeeze().numpy()
    n = float((emb ** 2).sum()) ** 0.5
    return (emb / (n + 1e-12)).tolist()


def main() -> None:
    import pyttsx3

    voices = pyttsx3.init().getProperty("voices")
    print(f"{len(voices)} SAPI voices available:")
    for v in voices:
        print(f"  {v.id}  ({v.name})")

    classifier = load_classifier()
    print("ECAPA loaded.\n")

    with tempfile.TemporaryDirectory(prefix="dr_cal_") as tmp:
        tmp = Path(tmp)
        # Different speakers, same sentence A.
        embeds_a: list[tuple[str, list[float]]] = []
        for v in voices:
            wav = tmp / f"{Path(v.id).name or v.name}.wav"
            if not synth(v.id, SENTENCE_A, wav):
                continue
            embeds_a.append((v.name, embed(classifier, load_audio_16k(wav))))

        # Same speaker (first voice), different sentences.
        wav_b = tmp / "same_speaker_b.wav"
        emb_b = None
        if embeds_a and synth(voices[0].id, SENTENCE_B, wav_b):
            emb_b = embed(classifier, load_audio_16k(wav_b))

        print("=== DIFFERENT SPEAKERS, SAME SENTENCE (cosine) ===")
        names = [n for n, _ in embeds_a]
        for i in range(len(embeds_a)):
            row = []
            for j in range(len(embeds_a)):
                row.append(f"{cosine_similarity(embeds_a[i][1], embeds_a[j][1]):.3f}")
            print(f"  {names[i]:<24} " + " ".join(row))

        if emb_b is not None:
            print("\n=== SAME SPEAKER, DIFFERENT SENTENCE ===")
            for i, (n, e) in enumerate(embeds_a):
                print(f"  {names[i]:<24} vs same-voice-different-text: {cosine_similarity(emb_b, e):.3f}")


if __name__ == "__main__":
    main()
