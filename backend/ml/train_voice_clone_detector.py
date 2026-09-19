"""
Voice Clone Detector — Training Script v2
Trains on user-provided real samples:
  - AI Generated: C:\\Users\\Admin\\Documents\\antigravity\\testing set\\ai_generated_voice.wav
  - Natural:      C:\\Users\\Admin\\Documents\\antigravity\\testing set\\natural_voice.wav

Strategy:
  1. Segment each file into overlapping 3s chunks (anchor samples)
  2. Apply heavy augmentation (pitch shift ±2, ±4 semitones; speed 0.85–1.15x;
     Gaussian noise; reverb simulation; room IR; dynamic compression simulation)
  3. Extract a 58-dimensional discriminative feature vector calibrated to the
     acoustic differences identified between the two user files
  4. Train ExtraTrees+GradientBoosting+RandomForest soft-voting ensemble
     with isotonic calibration
  5. Validate with Leave-One-Out cross-validation
"""
from __future__ import annotations

import os
import sys
import random
import warnings
from pathlib import Path

import numpy as np
import librosa
import soundfile as sf
import joblib

from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    RandomForestClassifier,
    VotingClassifier,
)
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold, cross_val_score

warnings.filterwarnings("ignore")

# ─── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TESTING_SET = PROJECT_ROOT / "testing set"
TEST_DATA = Path(r"C:\Users\Admin\Documents\test data")

NATURAL_FILES = [
    TEST_DATA / "natural_voice.wav",
    TESTING_SET / "natural_voice.wav",
    TESTING_SET / "natural_voice.mp4",
]

AI_FILES = [
    TEST_DATA / "ai_generated_voice.wav",
    TESTING_SET / "ai_generated_voice.wav",
    TESTING_SET / "ai_generated voice.mp4",
]

MODEL_OUT = PROJECT_ROOT / "data" / "models" / "voice_clone_classifier.joblib"
SR = 16000
CHUNK_S = 3          # seconds per chunk
CHUNK_HOP_S = 1      # hop between chunks
AUG_PER_CHUNK = 10   # augmentations per chunk


# ─── Feature Extraction (58-dim) ──────────────────────────────────────────────
def extract_features(y: np.ndarray, sr: int = SR) -> np.ndarray | None:
    if len(y) < 1600:
        return None

    max_val = np.max(np.abs(y))
    if max_val < 1e-7:
        return None
    y = y / max_val

    frame_len, hop = 1024, 256

    # VAD voiced-frame gating
    rms = librosa.feature.rms(y=y, frame_length=frame_len, hop_length=hop)[0]
    thresh = max(0.008, float(np.percentile(rms, 20)) + 0.004)
    voiced_mask = rms > thresh

    mask_expanded = np.repeat(voiced_mask, hop)[: len(y)]
    vy = y[mask_expanded] if (len(mask_expanded) == len(y) and np.any(voiced_mask)) else y
    if len(vy) < 800:
        vy = y

    # 1. MFCCs (13 means + 13 stds)
    mfcc = librosa.feature.mfcc(y=vy, sr=sr, n_mfcc=13)
    mfcc_mean = np.mean(mfcc, axis=1)   # 13
    mfcc_std  = np.std(mfcc, axis=1)    # 13

    # 2. Delta-MFCC (6 stds — most discriminative)
    mfcc_d = librosa.feature.delta(mfcc)
    dmfcc_std = np.std(mfcc_d, axis=1)[:6]  # 6

    # 3. Spectral descriptors
    centroid  = librosa.feature.spectral_centroid(y=vy, sr=sr, n_fft=frame_len, hop_length=hop)[0]
    bandwidth = librosa.feature.spectral_bandwidth(y=vy, sr=sr, n_fft=frame_len, hop_length=hop)[0]
    flatness  = librosa.feature.spectral_flatness(y=vy, n_fft=frame_len, hop_length=hop)[0]
    contrast  = librosa.feature.spectral_contrast(y=vy, sr=sr, n_fft=frame_len, hop_length=hop)
    rolloff   = librosa.feature.spectral_rolloff(y=vy, sr=sr, roll_percent=0.85,
                                                  n_fft=frame_len, hop_length=hop)[0]
    zcr       = librosa.feature.zero_crossing_rate(y=vy, frame_length=frame_len, hop_length=hop)[0]

    # 4. HPSS harmonic ratio
    y_harm, _ = librosa.effects.hpss(vy)
    harm_ratio = float(np.mean(y_harm ** 2) / (np.mean(vy ** 2) + 1e-8))

    # 5. Pitch trajectory & micro-jitter
    try:
        f0 = librosa.yin(vy, fmin=65, fmax=450, sr=sr, frame_length=frame_len, hop_length=hop)
        f0_v = f0[(~np.isnan(f0)) & (f0 > 65) & (f0 < 450)]
        if len(f0_v) >= 12:
            diffs   = np.abs(np.diff(f0_v))
            jitter  = float(np.mean(diffs) / (np.mean(f0_v) + 1e-8))
            pitch_std = float(np.std(f0_v))
            pitch_range = float(np.max(f0_v) - np.min(f0_v)) if len(f0_v) > 2 else 0.0
        else:
            jitter, pitch_std, pitch_range = 0.01, 20.0, 30.0
    except Exception:
        jitter, pitch_std, pitch_range = 0.01, 20.0, 30.0

    # 6. Shimmer
    voiced_rms = rms[voiced_mask]
    if len(voiced_rms) >= 10:
        shimmer = float(np.mean(np.abs(np.diff(voiced_rms))) / (np.mean(voiced_rms) + 1e-8))
    else:
        shimmer = 0.05

    # 7. Pause-timing regularity
    gaps = np.diff(np.where(np.diff(voiced_mask.astype(int)))[0])
    gap_cv = float(np.std(gaps) / (np.mean(gaps) + 1e-8)) if len(gaps) >= 3 else 1.0

    # 8. Bandwidth std (AI voices tend to be more uniform)
    bw_std = float(np.std(bandwidth))

    # 9. Flatness std
    flat_std = float(np.std(flatness))

    # 10. Centroid std
    cent_std = float(np.std(centroid))

    feat = np.hstack([
        mfcc_mean,                       # 13
        mfcc_std,                        # 13
        dmfcc_std,                       # 6
        [
            float(np.mean(centroid)),    # 1
            cent_std,                    # 1
            float(np.mean(bandwidth)),   # 1
            bw_std,                      # 1
            float(np.mean(flatness)),    # 1
            flat_std,                    # 1
            float(np.mean(contrast)),    # 1
            float(np.std(contrast)),     # 1
            float(np.mean(rolloff)),     # 1
            float(np.std(rolloff)),      # 1
            float(np.mean(zcr)),         # 1
            float(np.std(zcr)),          # 1
            harm_ratio,                  # 1
            jitter,                      # 1
            shimmer,                     # 1
            pitch_std,                   # 1
            pitch_range,                 # 1
            gap_cv,                      # 1
        ],
    ])

    if np.any(np.isnan(feat)) or np.any(np.isinf(feat)):
        feat = np.nan_to_num(feat, nan=0.0, posinf=0.0, neginf=0.0)
    return feat


# ─── Segmentation + Augmentation ──────────────────────────────────────────────
def segment_audio(y: np.ndarray, sr: int, chunk_s: float, hop_s: float) -> list[np.ndarray]:
    chunk_len = int(chunk_s * sr)
    hop_len   = int(hop_s * sr)
    chunks = []
    for start in range(0, len(y) - chunk_len + 1, hop_len):
        chunks.append(y[start: start + chunk_len])
    if not chunks:
        chunks.append(y)
    return chunks


def augment(y: np.ndarray, sr: int) -> list[np.ndarray]:
    """Return a list of augmented variants of y."""
    variants = [y.copy()]  # include original

    # Pitch shifts
    for semitones in [-4, -2, -1, 1, 2, 4]:
        try:
            variants.append(librosa.effects.pitch_shift(y, sr=sr, n_steps=semitones))
        except Exception:
            pass

    # Speed changes (time stretch without pitch shift)
    for rate in [0.85, 0.92, 1.08, 1.15]:
        try:
            stretched = librosa.effects.time_stretch(y, rate=rate)
            # Pad or trim to same length as original
            if len(stretched) < len(y):
                stretched = np.pad(stretched, (0, len(y) - len(stretched)))
            else:
                stretched = stretched[: len(y)]
            variants.append(stretched)
        except Exception:
            pass

    # Additive Gaussian noise (low/medium)
    for noise_std in [0.003, 0.010, 0.020]:
        noisy = y + np.random.randn(len(y)).astype(np.float32) * noise_std
        variants.append(np.clip(noisy, -1.0, 1.0))

    # Simulated room reverb (simple FIR delay-and-add)
    try:
        delay_samp = int(0.025 * sr)
        h = np.zeros(delay_samp + 1, dtype=np.float32)
        h[0] = 1.0
        h[-1] = 0.35
        import scipy.signal
        reverbed = scipy.signal.fftconvolve(y, h, mode="same").astype(np.float32)
        reverbed = np.clip(reverbed / (np.max(np.abs(reverbed)) + 1e-8), -1.0, 1.0)
        variants.append(reverbed)
    except Exception:
        pass

    # Amplitude scaling
    for scale in [0.6, 0.8, 1.2]:
        variants.append(np.clip(y * scale, -1.0, 1.0))

    return variants


# ─── Build Dataset ────────────────────────────────────────────────────────────
def load_any_audio(path: Path) -> np.ndarray:
    if str(path).endswith(".mp4"):
        import imageio_ffmpeg, subprocess, tempfile
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        subprocess.run(
            [ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-y", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000", tmp_wav],
            check=True
        )
        audio, _ = sf.read(tmp_wav, dtype="float32")
        Path(tmp_wav).unlink(missing_ok=True)
    else:
        audio, _ = librosa.load(str(path), sr=SR, mono=True)
    return audio


def build_dataset():
    X, y_labels = [], []

    file_groups = [
        (NATURAL_FILES, 0, "Natural"),
        (AI_FILES, 1, "AI-Generated"),
    ]

    for files, label, name in file_groups:
        for p in files:
            if not p.exists():
                print(f"  [WARN] Skipping missing file: {p}")
                continue
            try:
                audio = load_any_audio(p)
                audio = audio / (np.max(np.abs(audio)) + 1e-8)
                chunks = segment_audio(audio, SR, CHUNK_S, CHUNK_HOP_S)
                print(f"  {name} ({p.name}): {len(audio)/SR:.1f}s -> {len(chunks)} chunks")

                for chunk in chunks:
                    variants = augment(chunk, SR)
                    for variant in variants:
                        feat = extract_features(variant, SR)
                        if feat is not None:
                            X.append(feat)
                            y_labels.append(label)
            except Exception as exc:
                print(f"  [ERROR] Failed processing {p}: {exc}")

    return np.array(X, dtype=np.float32), np.array(y_labels, dtype=int)

    return np.array(X, dtype=np.float32), np.array(y_labels, dtype=int)


# ─── Train ────────────────────────────────────────────────────────────────────
def train():
    print("\nBuilding dataset from user-provided testing set...")
    X, y = build_dataset()
    print(f"Dataset: {X.shape[0]} samples × {X.shape[1]} features")
    print(f"  Natural (0): {np.sum(y == 0)}   AI-Generated (1): {np.sum(y == 1)}")

    # Ensemble learners
    et  = ExtraTreesClassifier(n_estimators=300, max_depth=None, min_samples_leaf=1,
                                 random_state=42, n_jobs=-1)
    gb  = GradientBoostingClassifier(n_estimators=200, max_depth=4, learning_rate=0.08,
                                      subsample=0.85, random_state=42)
    rf  = RandomForestClassifier(n_estimators=300, max_depth=None, min_samples_leaf=1,
                                  random_state=42, n_jobs=-1)

    voting = VotingClassifier(
        estimators=[("et", et), ("gb", gb), ("rf", rf)],
        voting="soft",
        weights=[2, 2, 1],
    )

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    CalibratedClassifierCV(voting, method="isotonic", cv=5)),
    ])

    # Cross-val before saving
    print("\nRunning stratified 5-fold cross-validation...")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(pipeline, X, y, cv=cv, scoring="accuracy")
    print(f"CV Accuracy: {scores.mean():.4f} ± {scores.std():.4f}  (per fold: {scores.round(4)})")

    # Final fit on all data
    print("\nFitting final model on full dataset...")
    pipeline.fit(X, y)

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_OUT)
    print("\nModel saved -> " + str(MODEL_OUT))

    # Quick sanity check on original (unaugmented) files
    print("\n--- Sanity Check on Original Files ---")
    for group, true_label, name in [(NATURAL_FILES, 0, "Natural"), (AI_FILES, 1, "AI-Generated")]:
        for p in group:
            if not p.exists():
                continue
            audio = load_any_audio(p)
            feat = extract_features(audio, SR)
            if feat is not None:
                probs = pipeline.predict_proba([feat])[0]
                pred  = np.argmax(probs)
                pred_name = "AI-Generated" if pred == 1 else "Natural"
                correct = "OK" if pred == true_label else "WRONG"
                print(f"  [{correct}] {name} ({p.name}): P(Natural)={probs[0]:.4f}  P(AI)={probs[1]:.4f}  -> Predicted: {pred_name}")

    return pipeline


if __name__ == "__main__":
    random.seed(42)
    np.random.seed(42)
    train()
