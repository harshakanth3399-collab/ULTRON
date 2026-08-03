from faster_whisper import WhisperModel
import speech_recognition as sr
import tempfile
import os
import io
import wave
import audioop

# Try to import local corrector; fall back to identity if missing
try:
    from corrector import correct
except Exception:
    def correct(text):
        return text

print("Loading Faster-Whisper model (for English commands)...")

model = WhisperModel(
    "medium",
    device="cpu",
    compute_type="int8"
)

print("Faster-Whisper loaded successfully.")

recognizer = sr.Recognizer()

# Use dynamic energy thresholding and tuned timing for short commands
recognizer.dynamic_energy_threshold = True
# Leave energy_threshold unset so it is adapted automatically by adjust_for_ambient_noise
# recognizer.energy_threshold = 250  <-- removed to allow automatic adjustment
recognizer.pause_threshold = 0.8
recognizer.non_speaking_duration = 0.3
recognizer.phrase_threshold = 0.4


def _normalize_wav_bytes(wav_bytes: bytes, target_rate: int = 16000) -> bytes:
    """Normalize WAV audio amplitude to near-full scale without clipping.

    Returns normalized WAV bytes (PCM) ready to be written to a .wav file.
    """
    try:
        bio = io.BytesIO(wav_bytes)
        with wave.open(bio, 'rb') as r:
            params = r.getparams()
            nchannels, sampwidth, framerate, nframes = params[:4]
            frames = r.readframes(nframes)

        # Compute current peak
        current_peak = audioop.max(frames, sampwidth)
        # Desired peak (avoid full clipping) e.g., 95% of max
        max_possible = (2 ** (8 * sampwidth - 1) - 1)
        desired_peak = int(max_possible * 0.95)

        if current_peak <= 0:
            factor = 1.0
        else:
            factor = float(desired_peak) / float(current_peak)
            # Limit extreme amplification
            if factor > 10.0:
                factor = 10.0

        if abs(factor - 1.0) > 0.01:
            frames = audioop.mul(frames, sampwidth, factor)

        # If sample rate differs from target_rate, do not resample here (keep original sample rate)
        # Write normalized WAV bytes
        out_bio = io.BytesIO()
        with wave.open(out_bio, 'wb') as w:
            w.setnchannels(nchannels)
            w.setsampwidth(sampwidth)
            w.setframerate(framerate)
            w.writeframes(frames)
        return out_bio.getvalue()
    except Exception:
        # Normalization failed; return original bytes
        return wav_bytes


def listen():

    try:
        with sr.Microphone(sample_rate=16000) as source:

            print("\n🎤 Listening...")

            # Increase ambient calibration to ~1 second for better energy_threshold estimation
            recognizer.adjust_for_ambient_noise(source, duration=1.0)

            audio = recognizer.listen(
                source,
                timeout=10,
                phrase_time_limit=15
            )

        # Save raw WAV to temp, normalize amplitude, then transcribe
        raw_wav = audio.get_wav_data()
        normalized_wav = _normalize_wav_bytes(raw_wav, target_rate=16000)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(normalized_wav)
            filename = f.name

        print("🧠 Transcribing (English, optimized for short commands)...")

        # Use recommended settings for English short commands
        segments, info = model.transcribe(
            filename,
            language="en",
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False
        )

        # Build raw transcription from segments
        raw_text = "".join(segment.text for segment in segments).strip()

        # Print raw transcription
        print("Raw transcription:", raw_text)

        # Apply spelling/word corrections used by router
        final_text = correct(raw_text)

        # Print final corrected command
        print("Final corrected command:", final_text)

        # Clean up temp file
        if os.path.exists(filename):
            os.remove(filename)

        return final_text

    except sr.WaitTimeoutError:
        return ""

    except KeyboardInterrupt:
        return ""

    except Exception as e:
        print("Speech Error:", e)
        return ""
