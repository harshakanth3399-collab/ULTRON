from faster_whisper import WhisperModel
import speech_recognition as sr
import tempfile
import os

print("Loading Faster-Whisper...")

model = WhisperModel(
    "medium",
    device="cpu",
    compute_type="int8"
)

print("Faster-Whisper loaded successfully.")

recognizer = sr.Recognizer()

# Balanced microphone settings
recognizer.dynamic_energy_threshold = True
recognizer.energy_threshold = 250
recognizer.pause_threshold = 0.8
recognizer.non_speaking_duration = 0.3
recognizer.phrase_threshold = 0.4


def listen():

    try:

        with sr.Microphone(sample_rate=16000) as source:

            print("\n🎤 Listening...")

            # Better ambient calibration
            recognizer.adjust_for_ambient_noise(source, duration=1.0)

            audio = recognizer.listen(
                source,
                timeout=10,
                phrase_time_limit=15
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio.get_wav_data())
            filename = f.name

        print("🧠 Transcribing...")

        segments, info = model.transcribe(
            filename,
            language="en",
            beam_size=8,
            best_of=8,
            vad_filter=True,
            vad_parameters={
                "min_silence_duration_ms": 350
            }
        )

        text = "".join(segment.text for segment in segments).strip().lower()

        if os.path.exists(filename):
            os.remove(filename)

        print("You said:", text)

        return text

    except sr.WaitTimeoutError:
        return ""

    except KeyboardInterrupt:
        return ""

    except Exception as e:

        print("Speech Error:", e)

        return ""