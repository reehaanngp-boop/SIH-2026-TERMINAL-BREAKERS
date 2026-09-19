"""Vocoder artifact and spectral anomaly analyzer for voice cloning detection.

Detects signatures specific to neural text-to-speech (TTS) and voice conversion vocoders:
1. High-frequency phase inconsistencies and instantaneous frequency variance.
2. Unnatural spectral rolloff and steep vocoder cutoffs (common in 16k/22k/24k neural resynthesis).
3. Voiced-frame spectral flatness & crest factor abnormalities.
4. Telephony codec bandpass compensation (G.711 narrowband 300-3400Hz and AMR/Opus wideband).
5. High-order harmonic dispersion (biomechanical vocal fold harmonics vs synthetic sinusoidal synthesis).
"""

from __future__ import annotations

from typing import Any
import numpy as np


class VocoderAnalyzer:
    """Analyzes audio signals for mathematical artifacts left by neural vocoders."""

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate

    def analyze_spectral_artifacts(self, x: np.ndarray) -> dict[str, Any]:
        """Perform granular spectral analysis to detect neural vocoder fingerprints.
        
        Returns a dictionary of metrics and a normalized vocoder anomaly score (0.0 to 1.0).
        """
        if x is None or len(x) < 1600:
            return {
                "vocoder_anomaly_score": 0.0,
                "phase_inconsistency": 0.0,
                "spectral_cutoff_hz": 0.0,
                "harmonic_dispersion": 0.0,
                "vocoder_fingerprint": "insufficient_audio",
            }

        # Normalize amplitude
        max_val = np.max(np.abs(x))
        if max_val > 1e-7:
            x_norm = x / max_val
        else:
            x_norm = x

        n_fft = 1024
        hop_length = 256

        # Short-time Fourier Transform
        window = np.hanning(n_fft)
        num_frames = 1 + (len(x_norm) - n_fft) // hop_length
        if num_frames < 4:
            return {
                "vocoder_anomaly_score": 0.0,
                "phase_inconsistency": 0.0,
                "spectral_cutoff_hz": 0.0,
                "harmonic_dispersion": 0.0,
                "vocoder_fingerprint": "insufficient_frames",
            }

        # Vectorized frame extraction
        shape = (num_frames, n_fft)
        strides = (x_norm.strides[0] * hop_length, x_norm.strides[0])
        frames = np.lib.stride_tricks.as_strided(x_norm, shape=shape, strides=strides)
        windowed_frames = frames * window

        # Compute complex spectrum
        stft = np.fft.rfft(windowed_frames, n=n_fft, axis=1)  # shape: (num_frames, n_fft // 2 + 1)
        mag = np.abs(stft) + 1e-10
        phase = np.angle(stft)

        freq_bins = np.fft.rfftfreq(n_fft, d=1.0 / self.sample_rate)

        # 1. Telephony Bandpass Detection
        # Narrowband telephony (G.711) cuts sharply below 300Hz and above 3400Hz.
        mean_spectrum = np.mean(mag, axis=0)
        total_energy = np.sum(mean_spectrum)
        hf_energy_ratio = float(np.sum(mean_spectrum[freq_bins > 4000]) / (total_energy + 1e-8))
        telephony_narrowband = hf_energy_ratio < 0.015

        # 2. Spectral Rolloff and Hard Cutoff Detection
        # Neural vocoders often synthesize at internal rates (e.g., 22050Hz or 24000Hz)
        # leaving an abrupt artificial drop-off in the 7000-8000Hz band.
        cutoff_freq = self._detect_cutoff_frequency(mean_spectrum, freq_bins)
        sharp_cutoff_detected = False
        if not telephony_narrowband and 6800 <= cutoff_freq <= 7900:
            sharp_cutoff_detected = True

        # 3. Phase Inconsistency & Instantaneous Frequency Anomaly
        # Natural human vocal cords create highly continuous phase progressions along harmonics.
        # Neural vocoders (HiFi-GAN, WaveGlow, Diffusion) produce subtle phase jitter across adjacent frames.
        unwrapped_phase = np.unwrap(phase, axis=0)
        phase_diff = np.diff(unwrapped_phase, axis=0)
        # Variance of phase progression across speech harmonics (300Hz - 3000Hz)
        speech_band_mask = (freq_bins >= 300) & (freq_bins <= 3500)
        if np.any(speech_band_mask):
            phase_var = float(np.mean(np.var(phase_diff[:, speech_band_mask], axis=0)))
        else:
            phase_var = float(np.mean(np.var(phase_diff, axis=0)))

        # 4. Spectral Crest and Flatness Discrepancy
        # Synthetic speech vocoders tend to have higher spectral flatness in unvoiced regions
        # and abnormal harmonic crest in voiced regions due to oscillator approximations.
        geometric_mean = np.exp(np.mean(np.log(mag[:, speech_band_mask]), axis=1))
        arithmetic_mean = np.mean(mag[:, speech_band_mask], axis=1)
        flatness_series = geometric_mean / (arithmetic_mean + 1e-10)
        spectral_flatness_mean = float(np.mean(flatness_series))

        # 5. Harmonic Dispersion & Subharmonic Void
        # Natural voices exhibit subharmonics and aspiration breath noise.
        # Neural vocoders often suppress inter-harmonic noise, creating "hollow" or "too clean" spectra.
        peak_to_valley_ratio = float(np.percentile(mean_spectrum, 95) / (np.percentile(mean_spectrum, 15) + 1e-8))

        # Compute Composite Vocoder Anomaly Score
        score = 0.0
        indicators = []

        if sharp_cutoff_detected:
            score += 0.35
            indicators.append("Neural vocoder high-frequency cutoff artifact (~7.5kHz)")

        if phase_var > 3.8:
            score += 0.30
            indicators.append("High phase inconsistency between adjacent frames")
        elif phase_var > 2.6:
            score += 0.15

        if spectral_flatness_mean < 0.012 and peak_to_valley_ratio > 35.0:
            score += 0.25
            indicators.append("Abnormally sterile inter-harmonic void (synthetic over-regularization)")

        if telephony_narrowband:
            # Telephony codec compensation: Adjust thresholds so G.711 compression does not yield false positives
            score = max(0.0, score - 0.10)
            telephony_mode = "narrowband_telephony (G.711)"
        else:
            telephony_mode = "wideband_telephony_or_voip"

        vocoder_score = float(np.clip(score, 0.0, 1.0))

        # Fingerprint the synthesis model architecture
        fingerprint = "natural_vocal_tract"
        if vocoder_score >= 0.60:
            if sharp_cutoff_detected:
                fingerprint = "neural_vocoder_hifigan_or_xtts"
            elif phase_var > 3.5:
                fingerprint = "diffusion_or_autoregressive_vocoder"
            else:
                fingerprint = "neural_speech_synthesis"
        elif vocoder_score >= 0.30:
            fingerprint = "suspicious_spectral_dispersion"

        return {
            "vocoder_anomaly_score": round(vocoder_score, 3),
            "phase_inconsistency": round(float(phase_var), 3),
            "spectral_cutoff_hz": round(float(cutoff_freq), 1),
            "spectral_flatness": round(float(spectral_flatness_mean), 4),
            "telephony_mode": telephony_mode,
            "sharp_cutoff_detected": sharp_cutoff_detected,
            "vocoder_fingerprint": fingerprint,
            "indicators": indicators,
        }

    def _detect_cutoff_frequency(self, mean_spectrum: np.ndarray, freq_bins: np.ndarray) -> float:
        """Find the frequency where spectral power drops precipitously."""
        if len(mean_spectrum) < 10:
            return float(self.sample_rate / 2)

        # Smooth spectrum
        smoothed = np.convolve(mean_spectrum, np.ones(5) / 5.0, mode="same")
        # Gradient
        grad = np.gradient(smoothed)
        # Look in the upper half of the spectrum (above 4kHz)
        upper_mask = freq_bins > 4000
        if not np.any(upper_mask):
            return float(self.sample_rate / 2)

        min_grad_idx = np.argmin(grad[upper_mask])
        cutoff_freq = freq_bins[upper_mask][min_grad_idx]
        return float(cutoff_freq)
