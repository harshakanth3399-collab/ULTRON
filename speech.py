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
    "tiny.en",
    device="cpu",
    compute_type="int8"
)

print("Faster-Whisper instant engine loaded.")

recognizer = sr.Recognizer()

# Instant timing tuning
recognizer.dynamic_energy_threshold = True
recognizer.pause_threshold = 0.5
recognizer.non_speaking_duration = 0.2
recognizer.phrase_threshold = 0.2


def _normalize_wav_bytes(wav_bytes: bytes, target_rate: int = 16000) -> bytes:
    """Normalize WAV audio amplitude to near-full scale without clipping."""
    try:
        bio = io.BytesIO(wav_bytes)
        with wave.open(bio, 'rb') as r:
            params = r.getparams()
            nchannels, sampwidth, framerate, nframes = params[:4]
            frames = r.readframes(nframes)

        current_peak = audioop.max(frames, sampwidth)
        max_possible = (2 ** (8 * sampwidth - 1) - 1)
        desired_peak = int(max_possible * 0.95)

        factor = float(desired_peak) / float(current_peak) if current_peak > 0 else 1.0
        if factor > 8.0:
            factor = 8.0

        if abs(factor - 1.0) > 0.01:
            frames = audioop.mul(frames, sampwidth, factor)

        out_bio = io.BytesIO()
        with wave.open(out_bio, 'wb') as w:
            w.setnchannels(nchannels)
            w.setsampwidth(sampwidth)
            w.setframerate(framerate)
            w.writeframes(frames)
        return out_bio.getvalue()
    except Exception:
        return wav_bytes


def listen():

    try:
        with sr.Microphone(sample_rate=16000) as source:

            print("\n🎤 Listening...")

            # Quick 0.1s ambient check for instant start
            recognizer.adjust_for_ambient_noise(source, duration=0.1)

            audio = recognizer.listen(
                source,
                timeout=8,
                phrase_time_limit=12
            )

        raw_wav = audio.get_wav_data()
        normalized_wav = _normalize_wav_bytes(raw_wav, target_rate=16000)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(normalized_wav)
            filename = f.name

        # Fast 0.2s transcription using base.en model
        segments, info = model.transcribe(
            filename,
            language="en",
            beam_size=1,
            best_of=1,
            temperature=0.0,
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
