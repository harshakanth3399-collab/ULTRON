"""
run_pipeline_checks.py - Comprehensive End-to-End Programmatic Checks.
Runs headless verification of all ULTRON modules:
  - Imports & dependencies
  - Standalone ModernGL context creation, shader compilation, framebuffer check
  - Microphone initialization & RMS scan
  - Faster-Whisper transcription on dynamic WAV
  - Router command response mapping
  - TTS generation check
"""
import sys
import os
import time
import io
import wave
import audioop
import tempfile
import asyncio

sys.stdout.reconfigure(encoding='utf-8')

# Mock QOpenGLWidget and QApplication to allow test execution without windows
os.environ["QT_QPA_PLATFORM"] = "offscreen"

print("=" * 60)
print("             ULTRON TECHNICAL AUDIT HARNESS")
print("=" * 60)

results = {
    "Imports & Dependencies": "FAIL",
    "ModernGL Headless Shaders": "FAIL",
    "Microphone System": "FAIL",
    "Whisper Transcription": "FAIL",
    "Router / Command Mapping": "FAIL",
    "TTS Generation & Pygame Play": "FAIL",
}

# ── 1. Imports ─────────────────────────────────────────────────────────────────
print("\n[TEST 1/6] Verifying Imports & Dependencies...")
try:
    import numpy as np
    import moderngl
    import PySide6
    from PySide6.QtWidgets import QApplication
    import pyaudio
    import speech_recognition as sr
    import pygame
    import edge_tts
    from faster_whisper import WhisperModel
    import speech
    import speech_engine
    import router
    from graphics.shaders import PARTICLE_VERT, PARTICLE_FRAG, BILLBOARD_VERT, BILLBOARD_FRAG
    results["Imports & Dependencies"] = "PASS"
    print("  -> All imports successful.")
except Exception as e:
    print(f"  -> Import check failed: {e}")
    sys.exit(1)

# ── 2. Shaders ─────────────────────────────────────────────────────────────────
print("\n[TEST 2/6] Compiling Shaders in Standalone OpenGL Context...")
try:
    # Create standalone ModernGL context
    ctx = moderngl.create_standalone_context()
    print(f"  -> Context created: {ctx.info.get('GL_VENDOR', 'unknown')} | {ctx.info.get('GL_VERSION', 'unknown')}")
    
    # Try compiling Particle Shader
    prog1 = ctx.program(vertex_shader=PARTICLE_VERT, fragment_shader=PARTICLE_FRAG)
    print("  -> Particle shaders compiled successfully.")
    
    # Try compiling Billboard Shader
    prog2 = ctx.program(vertex_shader=BILLBOARD_VERT, fragment_shader=BILLBOARD_FRAG)
    print("  -> Billboard shaders compiled successfully.")
    
    # Create a framebuffer to verify FBO creation
    fbo = ctx.framebuffer(
        color_attachments=[ctx.texture((256, 256), 4)],
        depth_attachment=ctx.depth_renderbuffer((256, 256))
    )
    print("  -> Headless framebuffer test passed.")
    results["ModernGL Headless Shaders"] = "PASS"
except Exception as e:
    print(f"  -> Shader compilation / FBO creation failed: {e}")

# ── 3. Microphone ─────────────────────────────────────────────────────────────
print("\n[TEST 3/6] Scanning Microphone & Measuring RMS...")
try:
    p = pyaudio.PyAudio()
    info = p.get_default_input_device_info()
    idx = int(info['index'])
    rate = int(info['defaultSampleRate'])
    print(f"  -> Default mic: [{idx}] {info['name']} | rate={rate}Hz")
    
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=rate,
        input=True,
        input_device_index=idx,
        frames_per_buffer=512
    )
    
    # Read a few chunks to verify data flow
    chunks_ok = 0
    for _ in range(5):
        data = stream.read(512, exception_on_overflow=False)
        rms = audioop.rms(data, 2)
        if len(data) == 1024:
            chunks_ok += 1
            
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    if chunks_ok == 5:
        print("  -> Successfully read 5 raw frames from mic.")
        results["Microphone System"] = "PASS"
    else:
        print(f"  -> Read mismatch: expected 5 complete chunks, got {chunks_ok}")
except Exception as e:
    print(f"  -> Mic verification failed: {e}")

# ── 4. Whisper ─────────────────────────────────────────────────────────────────
print("\n[TEST 4/6] Verifying Whisper Pipeline (Offline Test)...")
try:
    # Generate 0.5s of pure silence to verify Whisper transcribes it
    out = io.BytesIO()
    with wave.open(out, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b'\x00' * 16000)
    
    wav_data = out.getvalue()
    trans = speech.transcribe_audio_bytes(wav_data)
    # Silence transcription should be empty string
    if trans == "":
        print("  -> Silent WAV transcribed successfully (returned empty string as expected).")
        results["Whisper Transcription"] = "PASS"
    else:
        print(f"  -> Whisper returned unexpected output for silence: '{trans}'")
except Exception as e:
    print(f"  -> Whisper check failed: {e}")

# ── 5. Router ──────────────────────────────────────────────────────────────────
print("\n[TEST 5/6] Verifying Command Router & Command Mappings...")
try:
    from router import process
    flag, resp = process("what time is it")
    print(f"  -> Processed 'what time is it': flag={flag}, response={resp!r}")
    if flag is True and resp is not None:
        print("  -> Router process successfully mapped time intent.")
        results["Router / Command Mapping"] = "PASS"
    else:
        print("  -> Router mapping failed or returned None.")
except Exception as e:
    print(f"  -> Router check failed: {e}")

# ── 6. TTS ─────────────────────────────────────────────────────────────────────
print("\n[TEST 6/6] Verifying TTS Generation & Pygame Mixer...")
try:
    # Check if edge-tts can download and Pygame can load the locked RyanNeural voice
    filename = ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        filename = f.name
        
    communicate = edge_tts.Communicate(
        text="Technical audit pass completed.",
        voice=speech_engine.VOICE,
        rate=speech_engine.RATE,
        pitch=speech_engine.PITCH
    )
    asyncio.run(communicate.save(filename))
    
    # Load into pygame to verify format compatibility
    pygame.mixer.pre_init(44100, -16, 1, 512)
    pygame.mixer.init()
    pygame.mixer.music.load(filename)
    # Start playback for 100ms to verify no driver errors, then unload
    pygame.mixer.music.play()
    time.sleep(0.1)
    pygame.mixer.music.stop()
    pygame.mixer.music.unload()
    pygame.mixer.quit()
    
    try:
        os.remove(filename)
    except:
        pass
        
    print("  -> Generated and loaded TTS audio successfully.")
    results["TTS Generation & Pygame Play"] = "PASS"
except Exception as e:
    print(f"  -> TTS/Mixer check failed: {e}")

print("\n" + "=" * 60)
print("                  AUDIT REPORT CARD")
print("=" * 60)
all_pass = True
for test, res in results.items():
    print(f" {test:40s} : [{res}]")
    if res == "FAIL":
        all_pass = False

print("=" * 60)
if all_pass:
    print("STATUS: ALL SYSTEMS PROGRAMMATICALLY AUDITED AND READY.")
    sys.exit(0)
else:
    print("STATUS: VERIFICATION AUDIT FAILED.")
    sys.exit(1)
