"""Expanded Voice Suite Preview Tool for ULTRON — Supports Merged Composite Voice Option 11."""

import sys
import asyncio
import edge_tts
import pygame
import tempfile
import time

VOICE_OPTIONS = {
    "1": ("en-IN-PrabhatNeural", "-8%", "-8Hz", "Deep Male Indian English Accent (Currently Active)"),
    "2": ("en-GB-RyanNeural", "-12%", "-20Hz", "Deep 40yo British MCU J.A.R.V.I.S. Accent"),
    "3": ("en-GB-ThomasNeural", "-8%", "-10Hz", "Authoritative British Gentleman Accent"),
    "4": ("en-US-ChristopherNeural", "-6%", "-6Hz", "High-Testosterone Alpha Male Accent"),
    "5": ("en-US-EricNeural", "-10%", "-8Hz", "Commanding Cybernetic Male Accent"),
    "6": ("en-US-GuyNeural", "-8%", "-10Hz", "Deep Classic American Male Accent"),
    "7": ("en-US-SteffanNeural", "-8%", "-8Hz", "Deep Energetic Male Accent"),
    "8": ("en-AU-WilliamNeural", "-8%", "-8Hz", "Deep Australian Male Accent"),
    "9": ("en-CA-LiamNeural", "-8%", "-8Hz", "Deep Canadian Male Accent"),
    "10": ("en-IE-ConnorNeural", "-8%", "-8Hz", "Deep Irish Male Accent"),
    "11": ("en-GB-RyanNeural", "-10%", "-14Hz", "Merged Hybrid: Deep British J.A.R.V.I.S. + Alpha Male + Australian Accent"),
}

async def generate_sample(voice, rate, pitch, text, filename):
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(filename)

def preview_voice(option_key):
    if option_key not in VOICE_OPTIONS:
        print(f"Invalid option '{option_key}'. Choose 1 through 11.")
        return

    voice, rate, pitch, desc = VOICE_OPTIONS[option_key]
    print(f"\n[VOICE] Playing Voice [{option_key}]: {desc}")
    print(f"   Model: {voice} | Rate: {rate} | Pitch: {pitch}...")

    pygame.mixer.init()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        filename = f.name

    text = f"Voice Option {option_key}. {desc}. Hey Hur-sha, what can I help you with? ULTRON online."
    try:
        asyncio.run(generate_sample(voice, rate, pitch, text, filename))

        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(0.05)

        pygame.mixer.music.unload()
    except Exception as e:
        print(f"Voice generation note: {e}")

def play_all_voices():
    print("\n==================================================")
    print("🎧 PLAYING ALL 11 MALE NEURAL VOICES IN SEQUENCE")
    print("==================================================")
    for key in range(1, 12):
        preview_voice(str(key))
        time.sleep(0.5)

def set_active_voice(option_key):
    if option_key not in VOICE_OPTIONS:
        print(f"Invalid option '{option_key}'.")
        return

    voice, rate, pitch, desc = VOICE_OPTIONS[option_key]

    with open("speech_engine.py", "r", encoding="utf-8") as f:
        content = f.read()

    import re
    content = re.sub(r'VOICE\s*=\s*".*?"', f'VOICE = "{voice}"', content)
    content = re.sub(r'rate\s*=\s*".*?"', f'rate="{rate}"', content)
    content = re.sub(r'pitch\s*=\s*".*?"', f'pitch="{pitch}"', content)

    with open("speech_engine.py", "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n✅ SUCCESS! Locked ULTRON voice to [{option_key}]: {desc} ({voice})!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "all":
            play_all_voices()
        elif len(sys.argv) > 2 and sys.argv[2] == "set":
            set_active_voice(cmd)
        else:
            preview_voice(cmd)
    else:
        print("=== ULTRON VOICE SUITE ===")
        for key, info in VOICE_OPTIONS.items():
            print(f"  [{key}] {info[3]}")
        print("\nUsage:")
        print("  python test_voice.py 11      # Preview Merged Voice 11")
        print("  python test_voice.py 11 set  # Lock Merged Voice 11 as active ULTRON voice")
