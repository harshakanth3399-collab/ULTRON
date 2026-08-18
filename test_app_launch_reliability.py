"""
test_app_launch_reliability.py - App Launch & Reliability Verification Harness

Verifies:
  1. "Hey ULTRON, open WhatsApp." -> Real OS action + process verification
  2. "Hey ULTRON, open browser." -> Real OS action + process verification
  3. "Hey ULTRON, open VS Code." -> Real OS action + process verification
  4. "Hey ULTRON, open file explorer." -> Real OS action + process verification
"""

from __future__ import annotations

import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
os.environ["QT_QPA_PLATFORM"] = "offscreen"

print("=" * 80)
print("          ULTRON APP LAUNCH & RELIABILITY VERIFICATION HARNESS")
print("=" * 80)

import router
from modules.memory.profile_manager import get_profile_manager
from commands import verify_app_running

pm = get_profile_manager()
pm.set_active_language("en")

passed = []
failed = []

def log_test(name: str, success: bool, details: str):
    if success:
        passed.append(name)
        print(f" [PASS] {name:<50s} : {details}")
    else:
        failed.append((name, details))
        print(f" [FAIL] {name:<50s} : {details}")

# ── TEST 1: WHATSAPP ──────────────────────────────────────────────────────────
print("\n--- TEST 1: 'Hey ULTRON, open WhatsApp.' ---")
try:
    status, reply = router.process("Hey ULTRON, open WhatsApp.")
    print(f" [ROUTER REPLY]: '{reply}'")
    time.sleep(1.2)
    is_open = verify_app_running(["whatsapp", "whatsapp.exe"])
    if is_open:
        log_test("TEST 1: WhatsApp Launch", True, f"WhatsApp verified running! Reply: '{reply}'")
    else:
        log_test("TEST 1: WhatsApp Launch", False, f"Process not running. Reply: '{reply}'")
except Exception as e:
    log_test("TEST 1: WhatsApp Launch", False, str(e))

# ── TEST 2: BROWSER ───────────────────────────────────────────────────────────
print("\n--- TEST 2: 'Hey ULTRON, open browser.' ---")
try:
    status, reply = router.process("Hey ULTRON, open browser.")
    print(f" [ROUTER REPLY]: '{reply}'")
    time.sleep(1.0)
    is_open = verify_app_running(["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"])
    if is_open:
        log_test("TEST 2: Browser Launch", True, f"Browser verified running! Reply: '{reply}'")
    else:
        log_test("TEST 2: Browser Launch", False, f"Process not running. Reply: '{reply}'")
except Exception as e:
    log_test("TEST 2: Browser Launch", False, str(e))

# ── TEST 3: VS CODE ───────────────────────────────────────────────────────────
print("\n--- TEST 3: 'Hey ULTRON, open VS Code.' ---")
try:
    status, reply = router.process("Hey ULTRON, open VS Code.")
    print(f" [ROUTER REPLY]: '{reply}'")
    time.sleep(1.0)
    is_open = verify_app_running(["code.exe", "code"])
    if is_open:
        log_test("TEST 3: VS Code Launch", True, f"VS Code verified running! Reply: '{reply}'")
    else:
        log_test("TEST 3: VS Code Launch", False, f"Process not running. Reply: '{reply}'")
except Exception as e:
    log_test("TEST 3: VS Code Launch", False, str(e))

# ── TEST 4: FILE EXPLORER ─────────────────────────────────────────────────────
print("\n--- TEST 4: 'Hey ULTRON, open file explorer.' ---")
try:
    status, reply = router.process("Hey ULTRON, open file explorer.")
    print(f" [ROUTER REPLY]: '{reply}'")
    time.sleep(0.8)
    is_open = verify_app_running(["explorer.exe"])
    if is_open:
        log_test("TEST 4: File Explorer Launch", True, f"File Explorer verified running! Reply: '{reply}'")
    else:
        log_test("TEST 4: File Explorer Launch", False, f"Process not running. Reply: '{reply}'")
except Exception as e:
    log_test("TEST 4: File Explorer Launch", False, str(e))

# ── SUMMARY ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("                     TEST SUITE SUMMARY REPORT")
print("=" * 80)
print(f" PASSED TESTS: {len(passed)} / {len(passed) + len(failed)}")
print(f" FAILED TESTS: {len(failed)}")

if not failed:
    print("\nSTATUS: ALL 4 APP LAUNCH TESTS PASSED CLEANLY. OS ACTIONS VERIFIED.")
    sys.exit(0)
else:
    print("\nSTATUS: FAILURES DETECTED IN APP LAUNCH TEST SUITE.")
    sys.exit(1)
