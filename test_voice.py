"""Voice Sample Generator for Harsha's Approved ULTRON Voice Selection."""

import sys
import asyncio
import edge_tts
import pygame
import tempfile
import time

VOICE_OPTIONS = {
    "1": ("en-IN-PrabhatNeural", "-8%", "-8Hz", "Deep Male Indian English Neural Voice"),
    "2": ("en-GB-RyanNeural", "-12%", "-20Hz", "Deep British J.A.R.V.I.S. Male Voice"),
    "3": ("en-US-ChristopherNeural", "-6%", "-6Hz", "High-Testosterone Alpha Male Voice"),
    "4": ("en-US-AndrewNeural", "-10%", "-2Hz", "Standard American Male Voice"),
}

async def generate_sample(voice, rate, pitch, text, filename):
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(filename)

def preview_voice(option_key):
    if option_key not in VOICE_OPTIONS:
        print("Invalid option.")
        return

    voice, rate, pitch, desc = VOICE_OPTIONS[option_key]
    print(f"\n🔊 Playing Voice [{option_key}]: {desc} ({voice})...")

    pygame.mixer.init()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        filename = f.name

    text = f"Hey Harsha, what can I help you with? ULTRON online and ready."
    asyncio.run(generate_sample(voice, rate, pitch, text, filename))

    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        time.sleep(0.05)

    pygame.mixer.music.unload()

if __name__ == "__main__":
    opt = sys.argv[1] if len(sys.argv) > 1 else "1"
    preview_voice(opt)
