"""
test_language_switch.py - Comprehensive Language Switching & Enforcement Verification Harness

Verifies all 4 mandated behaviors:
  1. Speak English -> English response & active_language="en"
  2. Mention word "Telugu" without switch intent -> Remains English & active_language="en"
  3. Explicitly say "Switch to Telugu" -> Switches to Telugu & active_language="te"
  4. Explicitly say "Switch back to English" -> Immediately restores English & active_language="en"
"""

from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
os.environ["QT_QPA_PLATFORM"] = "offscreen"

print("=" * 80)
print("             ULTRON LANGUAGE SWITCHING VERIFICATION HARNESS")
print("=" * 80)

passed = []
failed = []

def log_test(name: str, success: bool, details: str):
    if success:
        passed.append(name)
        print(f" [PASS] {name:<50s} : {details}")
    else:
        failed.append((name, details))
        print(f" [FAIL] {name:<50s} : {details}")

import router
from modules.memory.profile_manager import get_profile_manager
from speech_engine import _is_telugu

pm = get_profile_manager()

# Ensure clean starting state: active_language = "en"
pm.set_active_language("en")

# ── TEST 1: Speak English ─────────────────────────────────────────────────────
print("\n--- TEST 1 — Speak English ---")
try:
    status, reply = router.process("What is the capital of India?")
    lang = pm.get_active_language()
    has_telugu_script = _is_telugu(reply)
    print(f" [OUTPUT] Reply: '{reply}' | Language={lang}")
    if lang == "en" and not has_telugu_script:
        log_test("TEST 1: Speak English", True, f"Language='en', No Telugu script in output")
    else:
        log_test("TEST 1: Speak English", False, f"Failed: lang={lang}, has_telugu={has_telugu_script}")
except Exception as e:
    log_test("TEST 1: Speak English", False, str(e))

# ── TEST 2: Mention word "Telugu" without requesting language change ─────────
print("\n--- TEST 2 — Mention word 'Telugu' without language change ---")
try:
    status, reply = router.process("Tell me about Telugu movies.")
    lang = pm.get_active_language()
    has_telugu_script = _is_telugu(reply)
    print(f" [OUTPUT] Reply: '{reply}' | Language={lang}")
    if lang == "en" and not has_telugu_script:
        log_test("TEST 2: Mention 'Telugu' (No Switch)", True, f"Remained in English mode! Reply in English.")
    else:
        log_test("TEST 2: Mention 'Telugu' (No Switch)", False, f"Failed: lang={lang}, has_telugu={has_telugu_script}")
except Exception as e:
    log_test("TEST 2: Mention 'Telugu' (No Switch)", False, str(e))

# ── TEST 3: Explicitly say "Switch to Telugu" ──────────────────────────────────
print("\n--- TEST 3 — Explicitly say 'Switch to Telugu' ---")
try:
    status, reply = router.process("Switch to Telugu")
    lang = pm.get_active_language()
    print(f" [OUTPUT] Reply: '{reply}' | Language={lang}")
    if lang == "te":
        log_test("TEST 3: Switch to Telugu", True, f"Language successfully set to 'te'! Reply: '{reply}'")
    else:
        log_test("TEST 3: Switch to Telugu", False, f"Failed to switch: lang={lang}")
except Exception as e:
    log_test("TEST 3: Switch to Telugu", False, str(e))

# ── TEST 4: Say "Switch back to English" ─────────────────────────────────────
print("\n--- TEST 4 — Say 'Switch back to English' ---")
try:
    status, reply = router.process("Switch back to English")
    lang = pm.get_active_language()
    has_telugu_script = _is_telugu(reply)
    print(f" [OUTPUT] Reply: '{reply}' | Language={lang}")
    if lang == "en" and not has_telugu_script:
        log_test("TEST 4: Switch back to English", True, f"Language restored to 'en'! Reply: '{reply}'")
    else:
        log_test("TEST 4: Switch back to English", False, f"Failed to restore English: lang={lang}")
except Exception as e:
    log_test("TEST 4: Switch back to English", False, str(e))

# ── SUMMARY REPORT ─────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("                     TEST SUITE SUMMARY REPORT")
print("=" * 80)
print(f" PASSED TESTS: {len(passed)} / {len(passed) + len(failed)}")
print(f" FAILED TESTS: {len(failed)}")

if not failed:
    print("\nSTATUS: ALL 4 LANGUAGE SWITCHING TESTS PASSED CLEANLY.")
    sys.exit(0)
else:
    print("\nSTATUS: FAILURES DETECTED IN LANGUAGE SWITCHING SUITE.")
    sys.exit(1)
