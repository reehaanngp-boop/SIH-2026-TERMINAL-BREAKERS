"""Audio I/O helpers built on the bundled ffmpeg binary and soundfile.

Everything is normalised to 16 kHz mono float32 in [-1, 1], which is the
input format expected by Whisper, AASIST and the speaker-verification
embedding. The ffmpeg binary ships inside the ``imageio-ffmpeg`` wheel, so no
system-wide ffmpeg install is required.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import soundfile as sf

from app.config import get_settings

settings = get_settings()

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
SAMPLE_RATE = 16000


@dataclass
class AudioData:
    """Decoded audio at 16 kHz mono, float32 in [-1, 1]."""

    samples: np.ndarray
    sr: int = SAMPLE_RATE
    duration: float = 0.0
    path: Path | None = None

    @property
    def n_samples(self) -> int:
        return int(self.samples.shape[0])


def _converted_dir() -> Path:
    d = settings.upload_dir / "_converted"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _ffmpeg(*args: str) -> Path:
    """Run ffmpeg and return the (first) output file path."""
    result = subprocess.run(
        [FFMPEG_EXE, "-hide_banner", "-loglevel", "error", "-y", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.strip()[:400]}")
    # The last path-like argument before any map/output options is the output file.
    out = None
    for a in args:
        if a.startswith("-"):
            continue
        if a.lower().endswith((".wav", ".pcm")):
            out = Path(a)
    if out is None:
        raise RuntimeError("ffmpeg: could not determine output file")
    return out


def convert_to_wav16k(src: str | Path, *, extract_audio_from_video: bool = False) -> Path:
    """Convert any audio/video file to a 16 kHz mono PCM WAV. Returns the path."""
    src = Path(src)
    out = _converted_dir() / f"{src.stem}_16k.wav"
    # If a previous conversion exists and is newer than the source, reuse it.
    if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
        return out
    args: list[str] = []
    if extract_audio_from_video:
        args += ["-vn"]
    args += ["-i", str(src), "-ar", str(SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le", str(out)]
    _ffmpeg(*args)
    return out


def extract_audio_from_video(video_path: str | Path) -> Path:
    """Extract the audio track of a video file as a 16 kHz mono WAV."""
    return convert_to_wav16k(video_path, extract_audio_from_video=True)


def load_audio_16k(path: str | Path, *, convert: bool = True) -> AudioData:
    """Decode an audio file to 16 kHz mono float32 and wrap it in AudioData.

    ``convert=False`` reads the file directly — use when it is already a 16 kHz
    mono WAV (e.g. produced by :func:`extract_audio_from_video`) to avoid a
    needless re-encode.
    """
    path = Path(path)
    # Convert everything through ffmpeg so exotic container formats work.
    wav_path = convert_to_wav16k(path) if convert else path
    samples, sr = sf.read(str(wav_path), dtype="float32", always_2d=False)
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    samples = np.ascontiguousarray(samples, dtype=np.float32)
    return AudioData(samples=samples, sr=int(sr), duration=float(len(samples) / sr), path=wav_path)


def probe_media_duration(path: str | Path) -> float:
    """Return media duration in seconds without loading samples into memory."""
    path = Path(path)
    try:
        info = sf.info(str(path))
        return float(info.duration)
    except Exception:
        # Fall back to ffmpeg stderr duration parsing for unsupported containers.
        try:
            result = subprocess.run(
                [FFMPEG_EXE, "-hide_banner", "-i", str(path)], capture_output=True, text=True
            )
            for line in result.stderr.splitlines():
                if "Duration:" in line and "N/A" not in line:
                    part = line.split("Duration:", 1)[1].split(",")[0].strip()
                    h, m, s = part.split(":")
                    return int(h) * 3600 + int(m) * 60 + float(s)
        except Exception:
            pass
        return 0.0
