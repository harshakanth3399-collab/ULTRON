"""
test_wake_word_reliability.py - Real-World Wake-Word Normalization & Reliability Test Suite
"""

from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
os.environ["QT_QPA_PLATFORM"] = "offscreen"

print("=" * 80)
print("          ULTRON WAKE-WORD NORMALIZATION & RELIABILITY TEST SUITE")
print("=" * 80)

from core.voice_pipeline import VoicePipeline

pipeline = VoicePipeline()


passed = []
failed = []

def log_test(name: str, success: bool, details: str):
    if success:
        passed.append(name)
        print(f" [PASS] {name:<55s} : {details}")
    else:
        failed.append((name, details))
        print(f" [FAIL] {name:<55s} : {details}")

# ── TEST CASES SPECIFIED BY USER ─────────────────────────────────────────────

test_cases = [
    # (Input transcript, expected_is_wake, expected_cmd_substring, Test Description)
    ("Hey ULTRON", True, "", "TEST 1: Standard 'Hey ULTRON' Standalone Wake"),
    ("Hey ULTRON, open WhatsApp", True, "whatsapp", "TEST 2: 'Hey ULTRON, open WhatsApp' Inline Command"),
    ("Hey ULTRON, what's the dollar rate?", True, "dollar rate", "TEST 3: 'Hey ULTRON, what's the dollar rate?' Inline Query"),
    ("low iron, hey", True, "", "TEST 4: Mishearing 'low iron, hey' Normalization"),
    ("I don't know. Go ahead, name.", True, "", "TEST 5: Mishearing 'go ahead name' Normalization"),
    ("I'll run open browser", True, "browser", "TEST 6: Mishearing 'I'll run' Normalization"),
    ("I'll draw what is the weather", True, "weather", "TEST 7: Mishearing 'I'll draw' Normalization"),
    ("pass me the salt please", False, "", "TEST 8: Unrelated Speech Non-Wake Guard")
]

print("\n--- RUNNING WAKE-WORD DETECTOR AUDIT ---")
for raw_input, exp_wake, exp_cmd_sub, test_name in test_cases:
    is_wake, inline_cmd = pipeline._is_wake(raw_input)
    
    success = (is_wake == exp_wake)
    if exp_cmd_sub and exp_cmd_sub not in inline_cmd.lower():
        success = False

    details = f"is_wake={is_wake}, inline_cmd='{inline_cmd}'"
    log_test(test_name, success, details)

# ── SUMMARY REPORT ─────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("                     TEST SUITE SUMMARY REPORT")
print("=" * 80)
print(f" PASSED TESTS: {len(passed)} / {len(test_cases)}")
print(f" FAILED TESTS: {len(failed)}")

if not failed:
    print("\nSTATUS: WAKE-WORD NORMALIZATION LAYER VERIFIED 100% WORKING.")
    sys.exit(0)
else:
    print("\nSTATUS: FAILURES DETECTED IN WAKE-WORD TEST SUITE.")
    sys.exit(1)
