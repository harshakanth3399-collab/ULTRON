"""Interactive Voice Studio & Tuning Tool for Harsha."""

import sys
import asyncio
import edge_tts
import pygame
import tempfile
import time
import re

def generate_sample(voice, rate, pitch, text, filename):
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    asyncio.run(communicate.save(filename))

def play_custom_voice(voice="en-GB-RyanNeural", rate="-10%", pitch="-14Hz", phonetic="Har-sha"):
    print(f"\n[VOICE STUDIO] Testing Voice Tuning:")
    print(f"  Model: {voice} | Speed/Rate: {rate} | Deepness/Pitch: {pitch} | Name: '{phonetic}'")

    text = f"Hey {phonetic}, I am ULTRON. Testing your custom voice parameters now."
    pygame.mixer.init()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        filename = f.name

    try:
        generate_sample(voice, rate, pitch, text, filename)
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(0.05)

        pygame.mixer.music.unload()
    except Exception as e:
        print(f"Playback note: {e}")

def apply_to_ultron(voice, rate, pitch, phonetic):
    with open("speech_engine.py", "r", encoding="utf-8") as f:
        content = f.read()

    content = re.sub(r'VOICE\s*=\s*".*?"', f'VOICE = "{voice}"', content)
    content = re.sub(r'rate\s*=\s*".*?"', f'rate="{rate}"', content)
    content = re.sub(r'pitch\s*=\s*".*?"', f'pitch="{pitch}"', content)

    # Update _fix_phonetics
    content = re.sub(
        r'return text\.replace\("Harsha", ".*?"\)\.replace\("harsha", ".*?"\)',
        f'return text.replace("Harsha", "{phonetic}").replace("harsha", "{phonetic.lower()}")',
        content
    )

    with open("speech_engine.py", "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n✅ SUCCESS! Applied your custom voice parameters to ULTRON speech_engine.py!")

if __name__ == "__main__":
    v = sys.argv[1] if len(sys.argv) > 1 else "en-GB-RyanNeural"
    r = sys.argv[2] if len(sys.argv) > 2 else "-10%"
    p = sys.argv[3] if len(sys.argv) > 3 else "-14Hz"
    n = sys.argv[4] if len(sys.argv) > 4 else "Har-sha"

    if len(sys.argv) > 5 and sys.argv[5] == "apply":
        apply_to_ultron(v, r, p, n)
    else:
        play_custom_voice(v, r, p, n)
