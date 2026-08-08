"""Voice Biometric Speaker Verification Engine for Harsha."""

from __future__ import annotations

import os
import wave
import numpy as np

VOICE_PRINT_PATH = os.path.join("memory", "harsha_voice.npy")


def extract_audio_features(wav_path: str) -> np.ndarray:
    """Extracts normalized spectral & energy feature vector from WAV file."""
    try:
        with wave.open(wav_path, "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            raw_data = wf.readframes(n_frames)

        audio = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32)
        if n_channels > 1:
            audio = audio[::n_channels]

        if len(audio) < 1600:  # < 0.1s
            return np.zeros(64, dtype=np.float32)

        # Normalize audio amplitude
        audio = audio / (np.max(np.abs(audio)) + 1e-6)

        # Compute STFT magnitude spectrogram
        frame_length = 512
        hop_length = 256
        n_frames = (len(audio) - frame_length) // hop_length
        if n_frames <= 0:
            return np.zeros(64, dtype=np.float32)

        frames = np.lib.stride_tricks.sliding_window_view(audio[:n_frames * hop_length + frame_length], frame_length)[::hop_length]
        window = np.hanning(frame_length)
        spectrogram = np.abs(np.fft.rfft(frames * window, axis=1))

        # 64-bin Mel-spaced frequency energy profile
        freq_bins = spectrogram.shape[1]
        bin_size = max(1, freq_bins // 64)
        feature_vector = np.array([np.mean(spectrogram[:, i * bin_size:(i + 1) * bin_size]) for i in range(64)], dtype=np.float32)

        # L2 Normalize feature vector
        norm = np.linalg.norm(feature_vector)
        if norm > 1e-6:
            feature_vector /= norm

        return feature_vector
    except Exception as e:
        print("Audio Feature Extraction Error:", e)
        return np.zeros(64, dtype=np.float32)


def enroll_harsha_voice(wav_path: str) -> bool:
    """Saves Harsha's baseline voice biometric print."""
    os.makedirs(os.path.dirname(VOICE_PRINT_PATH), exist_ok=True)
    features = extract_audio_features(wav_path)
    if np.sum(features) == 0:
        return False
    np.save(VOICE_PRINT_PATH, features)
    print("🔒 Harsha's Voice Print enrolled successfully!")
    return True


def is_harsha_speaking(wav_path: str, threshold: float = 0.65) -> Tuple[bool, float]:
    """Compares input voice against Harsha's enrolled voice print using Cosine Similarity."""
    if not os.path.exists(VOICE_PRINT_PATH):
        # Auto-enroll on first speech sample
        enroll_harsha_voice(wav_path)
        return True, 1.0

    target = np.load(VOICE_PRINT_PATH)
    sample = extract_audio_features(wav_path)

    if np.sum(sample) == 0:
        return True, 0.5  # Soft fallback if audio sample too short

    # Cosine Similarity
    similarity = float(np.dot(target, sample) / (np.linalg.norm(target) * np.linalg.norm(sample) + 1e-8))
    print(f"🔒 Speaker Verification Match Score: {similarity:.2f} (Threshold: {threshold})")

    return (similarity >= threshold), similarity
