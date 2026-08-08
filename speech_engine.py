import asyncio
import threading
import edge_tts
import pygame
import os
import tempfile

VOICE = "en-IN-PrabhatNeural"

pygame.mixer.init()

_current_thread = None
_is_speaking = False


async def _generate(text, filename):

    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate="-10%",
        pitch="-14Hz"
    )

    await communicate.save(filename)


def _play(text):

    global _is_speaking

    _is_speaking = True

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        filename = f.name

    asyncio.run(_generate(text, filename))

    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(30)

    pygame.mixer.music.unload()

    try:
        os.remove(filename)
    except:
        pass

    _is_speaking = False


def speak(text):

    global _current_thread

    stop()

    _current_thread = threading.Thread(
        target=_play,
        args=(text,),
        daemon=True
    )

    _current_thread.start()


def stop():

    global _is_speaking

    if pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()

    _is_speaking = False


def speaking():
    return _is_speaking