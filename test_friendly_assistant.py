"""
test_friendly_assistant.py - Test Suite for Real-World Friendly Assistant & System Diagnostics
"""

from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
os.environ["QT_QPA_PLATFORM"] = "offscreen"

print("=" * 80)
print("             ULTRON FRIENDLY ASSISTANT VERIFICATION HARNESS")
print("=" * 80)

import router
from modules.friendly_assistant import get_dynamic_greeting, get_system_diagnostics, get_friendly_response

passed = []
failed = []

def log_test(name: str, success: bool, details: str):
    if success:
        passed.append(name)
        print(f" [PASS] {name:<55s} : {details}")
    else:
        failed.append((name, details))
        print(f" [FAIL] {name:<55s} : {details}")

# ── TEST 1: TIME-AWARE DYNAMIC GREETING ───────────────────────────────────────
print("\n--- TEST 1: Time-Aware Dynamic Greeting ---")
try:
    greeting = get_dynamic_greeting("Harsha")
    print(f" [DYNAMIC GREETING]: '{greeting}'")
    if "Harsha" in greeting and ("morning" in greeting or "afternoon" in greeting or "evening" in greeting):
        log_test("TEST 1: Time-Aware Dynamic Greeting", True, f"Greeting generated: '{greeting}'")
    else:
        log_test("TEST 1: Time-Aware Dynamic Greeting", False, f"Unexpected greeting format: '{greeting}'")
except Exception as e:
    log_test("TEST 1: Time-Aware Dynamic Greeting", False, str(e))

# ── TEST 2: J.A.R.V.I.S. SYSTEM DIAGNOSTICS REPORT ───────────────────────────
print("\n--- TEST 2: J.A.R.V.I.S. System Diagnostics Report ---")
try:
    diag = get_system_diagnostics("Harsha")
    print(f" [DIAGNOSTICS REPORT]: '{diag}'")
    if "operational" in diag and ("Memory" in diag or "RAM" in diag) and "battery" in diag:
        log_test("TEST 2: System Diagnostics Report", True, f"Report: '{diag[:80]}...'")
    else:
        log_test("TEST 2: System Diagnostics Report", False, f"Unexpected report format: '{diag}'")
except Exception as e:
    log_test("TEST 2: System Diagnostics Report", False, str(e))

# ── TEST 3: FRIENDLY PLEASANTRIES & GRATITUDE ──────────────────────────────────
print("\n--- TEST 3: Gratitude & Pleasantries ---")
try:
    reply = get_friendly_response("Thank you ULTRON", "Harsha")
    print(f" [GRATITUDE REPLY]: '{reply}'")
    if "pleasure" in reply:
        log_test("TEST 3: Gratitude & Pleasantries", True, f"Reply: '{reply}'")
    else:
        log_test("TEST 3: Gratitude & Pleasantries", False, f"Unexpected reply: '{reply}'")
except Exception as e:
    log_test("TEST 3: Gratitude & Pleasantries", False, str(e))

# ── TEST 4: ROUTER DIAGNOSTICS INTEGRATION ────────────────────────────────────
print("\n--- TEST 4: Router System Diagnostics ---")
try:
    status, router_diag = router.process("ULTRON, how are you doing?")
    print(f" [ROUTER DIAGNOSTICS]: '{router_diag}'")
    if "operational" in router_diag and ("Memory" in router_diag or "RAM" in router_diag):
        log_test("TEST 4: Router System Diagnostics Integration", True, f"Router reply: '{router_diag[:80]}...'")
    else:
        log_test("TEST 4: Router System Diagnostics Integration", False, f"Unexpected router reply: '{router_diag}'")
except Exception as e:
    log_test("TEST 4: Router System Diagnostics Integration", False, str(e))

# ── SUMMARY ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("                     TEST SUITE SUMMARY REPORT")
print("=" * 80)
print(f" PASSED TESTS: {len(passed)} / {len(passed) + len(failed)}")
print(f" FAILED TESTS: {len(failed)}")

if not failed:
    print("\nSTATUS: ALL FRIENDLY ASSISTANT FEATURES VERIFIED 100% WORKING.")
    sys.exit(0)
else:
    print("\nSTATUS: FAILURES DETECTED IN FRIENDLY ASSISTANT TEST SUITE.")
    sys.exit(1)
