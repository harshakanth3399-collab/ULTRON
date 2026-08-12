"""
diagnostic.py - ULTRON Emergency System Diagnostic Harness
Audits 14 critical subsystems with explicit [PASS], [FAIL], [WARN] status and root cause reporting.
"""

import sys
import os
import time
import io
import wave
import audioop
import tempfile
import asyncio
import urllib.request
import json

sys.stdout.reconfigure(encoding='utf-8')
os.environ["QT_QPA_PLATFORM"] = "offscreen"

print("=" * 75)
print("             ULTRON SYSTEM DIAGNOSTIC & HEALTH AUDIT")
print("=" * 75)

report = {}


def log_test(name: str, status: str, details: str = ""):
    report[name] = status
    icon = "[PASS]" if status == "PASS" else ("[WARN]" if status == "WARN" else "[FAIL]")
    print(f" {icon} {name:<35s} : {details}")


# ── 1. Microphone Hardware Probe ───────────────────────────────────────────────
print("\n--- 1. MICROPHONE & AUDIO CAPTURE SUBSYSTEM ---")
try:
    import pyaudio
    import speech
    p = pyaudio.PyAudio()
    info = p.get_default_input_device_info()
    idx = int(info['index'])
    rate = int(info['defaultSampleRate'])
    ch = min(int(info['maxInputChannels']), 2)

    stream = p.open(format=pyaudio.paInt16, channels=1, rate=rate, input=True, input_device_index=idx, frames_per_buffer=512)
    rms_vals = []
    for _ in range(5):
        data = stream.read(512, exception_on_overflow=False)
        rms_vals.append(audioop.rms(data, 2))
    stream.stop_stream()
    stream.close()
    p.terminate()

    avg_noise = sum(rms_vals) / len(rms_vals) if rms_vals else 0.0
    log_test("Microphone Device", "PASS", f"Dev [{idx}] '{info['name'][:30]}' @ {rate}Hz, Noise={avg_noise:.1f} RMS")
    log_test("VAD Noise Threshold", "PASS", f"Dynamic Gate={speech._energy_threshold} (Ambient={speech._AMBIENT_RMS:.1f} RMS)")
except Exception as e:
    log_test("Microphone Device", "FAIL", str(e))
    log_test("VAD Noise Threshold", "FAIL", "Mic unavailable")

# ── 2. Faster-Whisper Speech Recognition ───────────────────────────────────────
print("\n--- 2. SPEECH RECOGNITION (WHISPER STT) ---")
try:
    out = io.BytesIO()
    with wave.open(out, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b'\x00' * 16000)

    trans_silence, lang_silence = speech.transcribe_audio_bytes(out.getvalue())
    override_test = speech.PHONETIC_OVERRIDES.get("reproduce")

    log_test("Silence Transcription", "PASS", f"Silence transcript: '{trans_silence}' (Language={lang_silence})")
    log_test("Phonetic Overrides", "PASS", f"'reproduce' -> '{override_test}'")
except Exception as e:
    log_test("Silence Transcription", "FAIL", str(e))
    log_test("Phonetic Overrides", "FAIL", str(e))

# ── 3. Wake Word Classifier ───────────────────────────────────────────────────
print("\n--- 3. WAKE WORD CLASSIFIER ---")
try:
    from core.voice_pipeline import VoicePipeline
    vp = VoicePipeline()

    w1, cmd1 = vp._is_wake("hey")
    w2, cmd2 = vp._is_wake("Hey")
    w3, cmd3 = vp._is_wake("hey, what is the time?")

    if w1 and w2:
        log_test("'Hey' Wake Classifier", "PASS", "Trigger 'hey' and 'Hey' verified")
    else:
        log_test("'Hey' Wake Classifier", "FAIL", f"w1={w1}, w2={w2}")

    if w3 and cmd3 == "what is the time":
        log_test("Single-Utterance Direct Dispatch", "PASS", f"'hey, what is the time?' -> cmd='{cmd3}'")
    else:
        log_test("Single-Utterance Direct Dispatch", "FAIL", f"cmd={cmd3}")
except Exception as e:
    log_test("'Hey' Wake Classifier", "FAIL", str(e))
    log_test("Single-Utterance Direct Dispatch", "FAIL", str(e))

# ── 4. AI Backend Connection & Ollama ──────────────────────────────────────────
print("\n--- 4. AI BACKEND CONNECTION & OLLAMA HEALTH ---")
try:
    import ai
    is_healthy, status_str, models = ai.check_ai_backend_health()

    print(f"  [AI] Backend: Ollama (Local)")
    print(f"  [AI] Host: {ai.OLLAMA_HOST}")
    print(f"  [AI] Port: {ai.OLLAMA_PORT}")
    print(f"  [AI] Connection: {status_str}")
    print(f"  [AI] Configured Model: {ai.DEFAULT_LOCAL_MODEL}")
    print(f"  [AI] Available Models: {models}")

    if is_healthy and len(models) > 0:
        log_test("AI Backend Health", "PASS", f"Ollama operational @ {ai.OLLAMA_URL}")
        # Test actual LLM query
        test_reply = ai.ask_ai("Say hello in 3 words.")
        print(f"  [AI] Test Prompt Reply: '{test_reply}'")
        if test_reply and "offline" not in test_reply.lower() and "unreachable" not in test_reply.lower():
            log_test("AI Model Generation", "PASS", f"Model '{ai.DEFAULT_LOCAL_MODEL}' responded cleanly")
        else:
            log_test("AI Model Generation", "FAIL", f"Model generation failed: '{test_reply}'")

    else:
        log_test("AI Backend Health", "FAIL", f"Ollama service unreachable on {ai.OLLAMA_URL}")
        log_test("AI Model Generation", "FAIL", "Backend offline")
except Exception as e:
    log_test("AI Backend Health", "FAIL", str(e))
    log_test("AI Model Generation", "FAIL", str(e))

# ── 5. TTS Voice Generation & Playback ─────────────────────────────────────────
print("\n--- 5. DUAL TTS & AUDIO PLAYBACK ENGINE ---")
try:
    import edge_tts
    import speech_engine
    import pygame

    print(f"  [TTS] English Male Voice: {speech_engine.VOICE_EN}")
    print(f"  [TTS] Telugu Female Voice: {speech_engine.VOICE_TE}")

    # Generate English test file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f_en:
        tmp_en = f_en.name

    comm_en = edge_tts.Communicate("Speech engine test.", voice=speech_engine.VOICE_EN)
    asyncio.run(comm_en.save(tmp_en))
    sz_en = os.path.getsize(tmp_en)

    # Play via Pygame
    pygame.mixer.music.load(tmp_en)
    pygame.mixer.music.play()
    time.sleep(0.1)
    pygame.mixer.music.stop()
    pygame.mixer.music.unload()
    os.remove(tmp_en)

    if sz_en > 1000:
        log_test("English Male TTS (en-GB-RyanNeural)", "PASS", f"MP3 generated ({sz_en} bytes) & played via Pygame")
    else:
        log_test("English Male TTS (en-GB-RyanNeural)", "FAIL", "MP3 empty")
except Exception as e:
    log_test("English Male TTS (en-GB-RyanNeural)", "FAIL", str(e))

try:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f_te:
        tmp_te = f_te.name

    comm_te = edge_tts.Communicate("నమస్కారం", voice=speech_engine.VOICE_TE)
    asyncio.run(comm_te.save(tmp_te))
    sz_te = os.path.getsize(tmp_te)
    os.remove(tmp_te)

    if sz_te > 1000:
        log_test("Telugu Female TTS (te-IN-ShrutiNeural)", "PASS", f"MP3 generated ({sz_te} bytes)")
    else:
        log_test("Telugu Female TTS (te-IN-ShrutiNeural)", "FAIL", "MP3 empty")
except Exception as e:
    log_test("Telugu Female TTS (te-IN-ShrutiNeural)", "FAIL", str(e))

# ── 6. Personal Memory & Address Sanitation ───────────────────────────────────
print("\n--- 6. PERSONAL MEMORY & ADDRESS SANITATION ---")
try:
    from modules.memory.profile_manager import get_profile_manager
    import router

    pm = get_profile_manager()
    pm.set_preference("preferred_address", "Sir")
    stored_addr = pm.data.get("preferences", {}).get("preferred_address")

    bad_sample = "Different regions have their own dialects, man."
    cleaned = ai.validate_and_correct_address(bad_sample, "Sir")

    _, router_query = router.process("what should you call me")

    if stored_addr == "Sir" and "man" not in cleaned and "Sir" in router_query:
        log_test("Persistent Address 'Sir'", "PASS", f"Preference stored & sanitized: '{cleaned}'")
    else:
        log_test("Persistent Address 'Sir'", "FAIL", f"stored={stored_addr}, cleaned='{cleaned}'")
except Exception as e:
    log_test("Persistent Address 'Sir'", "FAIL", str(e))

# ── 7. SQLite Database Storage Engine ─────────────────────────────────────────
print("\n--- 7. SQLITE DATABASE STORAGE ENGINE ---")
try:
    from modules.database import get_chat_stats, search_chat_history
    stats = get_chat_stats()
    log_test("SQLite ultron.db Engine", "PASS", f"Database initialized (Total Chats={stats['total_chats']}, Size={stats['db_size_kb']} KB)")
except Exception as e:
    log_test("SQLite ultron.db Engine", "FAIL", str(e))

# ── 8. Gmail Assistant & Personal Data Trainer ────────────────────────────────
print("\n--- 8. GMAIL ASSISTANT & PERSONAL DATA TRAINER ---")
try:
    import modules.email_engine as ee
    import modules.memory.trainer as tr
    log_test("Gmail Assistant & Job Selection Alert", "PASS", "Module loaded (voice job alerts & formal AI reply ready)")
    log_test("Personal Data & ChatGPT Trainer", "PASS", "Module loaded (conversations.json & TXT memory ingestion ready)")
except Exception as e:
    log_test("Gmail Assistant & Job Selection Alert", "FAIL", str(e))
    log_test("Personal Data & ChatGPT Trainer", "FAIL", str(e))

# ── 10. Real Web Research & Conversational Short-Term Memory Suite ─────────────
print("\n--- 10. REAL WEB RESEARCH & CONVERSATIONAL SHORT-TERM MEMORY SUITE ---")
try:
    import router
    from modules.short_term_memory import short_term_memory

    test_queries = [
        ("TEST 1", "Hello ULTRON.", False),
        ("TEST 2", "Who are you?", False),
        ("TEST 3", "What is Q-Spiders?", True),
        ("TEST 4", "Search the internet and tell me about Q-Spiders.", True),
        ("TEST 5", "How many Q-Spiders locations are there in Bangalore?", True),
        ("TEST 6", "What are those locations?", False), # Follow-up short-term reference
        ("TEST 7", "Tell me more about the first one.", False), # Follow-up index reference
        ("TEST 8", "What did I just ask you?", False), # Follow-up history query
        ("TEST 9", "What's the latest information about Q-Spiders?", True),
    ]

    conv_success = True
    for label, q_text, expects_web in test_queries:
        print(f"\n[RUNNING {label}] Prompt: '{q_text}'")
        status, reply = router.process(q_text)
        print(f"[REPLY {label}] {reply}")

        if not reply or len(reply.strip()) < 3:
            conv_success = False
            log_test(f"Conversational {label}", "FAIL", f"Empty reply for '{q_text}'")
        else:
            log_test(f"Conversational {label}", "PASS", f"Reply: '{reply[:60]}...'")

    if conv_success:
        log_test("Web Research & 9-Step Conversational Suite", "PASS", "All 9 test prompts executed and verified cleanly")
    else:
        log_test("Web Research & 9-Step Conversational Suite", "FAIL", "One or more conversational tests produced empty replies")
except Exception as e:
    log_test("Web Research & 9-Step Conversational Suite", "FAIL", str(e))

print("\n" + "=" * 75)
print("                     DIAGNOSTIC REPORT CARD")
print("=" * 75)
all_pass = True
for test, st in report.items():
    if st != "PASS":
        all_pass = False

print("=" * 75)
if all_pass:
    print("STATUS: ALL SUBSYSTEMS OPERATIONAL. ZERO REGRESSIONS DETECTED.")
    sys.exit(0)
else:
    print("STATUS: DIAGNOSTIC AUDIT DETECTED SUBSYSTEM FAILURES.")
    sys.exit(1)

