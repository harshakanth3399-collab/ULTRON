"""
test_bonus_features.py - Verification Harness for Screen Vision, Window Management & File Search
"""

from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
os.environ["QT_QPA_PLATFORM"] = "offscreen"

print("=" * 80)
print("             ULTRON BONUS FEATURES VERIFICATION HARNESS")
print("=" * 80)

import router
from modules.screen_vision import take_screenshot, capture_screen_gdi
from modules.window_manager import minimize_all_windows
from modules.file_search import search_local_files

passed = []
failed = []

def log_test(name: str, success: bool, details: str):
    if success:
        passed.append(name)
        print(f" [PASS] {name:<55s} : {details}")
    else:
        failed.append((name, details))
        print(f" [FAIL] {name:<55s} : {details}")

# ── TEST 1: SCREEN CAPTURE & SCREENSHOT ───────────────────────────────────────
print("\n--- TEST 1: Screen Vision & Capture ---")
try:
    ok, msg, w, h = capture_screen_gdi()
    if ok and w > 0:
        log_test("TEST 1: GDI Screen Capture", True, f"Captured screen ({w}x{h}): '{msg}'")
    else:
        log_test("TEST 1: GDI Screen Capture", False, msg)
except Exception as e:
    log_test("TEST 1: GDI Screen Capture", False, str(e))

# ── TEST 2: WINDOW MANAGEMENT ─────────────────────────────────────────────────
print("\n--- TEST 2: Desktop Window Management ---")
try:
    msg = minimize_all_windows()
    log_test("TEST 2: Show Desktop / Minimize All", True, f"Executed: '{msg}'")
except Exception as e:
    log_test("TEST 2: Show Desktop / Minimize All", False, str(e))

# ── TEST 3: LOCAL FILE SEARCH ─────────────────────────────────────────────────
print("\n--- TEST 3: Fast Local File Search ---")
try:
    ok, msg, files = search_local_files("find file main.py")
    if ok and len(files) > 0:
        log_test("TEST 3: Local File Search", True, f"Found {len(files)} files: '{msg}'")
    else:
        log_test("TEST 3: Local File Search", False, msg)
except Exception as e:
    log_test("TEST 3: Local File Search", False, str(e))

# ── TEST 4: ROUTER SCREENSHOT INTENT ──────────────────────────────────────────
print("\n--- TEST 4: Router Screenshot Intent ---")
try:
    status, reply = router.process("Take a screenshot.")
    print(f" [ROUTER SCREENSHOT]: '{reply}'")
    if "Screenshot" in reply or "captured" in reply or "saved" in reply:
        log_test("TEST 4: Router Screenshot Integration", True, f"Reply: '{reply}'")
    else:
        log_test("TEST 4: Router Screenshot Integration", False, f"Unexpected reply: '{reply}'")
except Exception as e:
    log_test("TEST 4: Router Screenshot Integration", False, str(e))

# ── SUMMARY ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("                     TEST SUITE SUMMARY REPORT")
print("=" * 80)
print(f" PASSED TESTS: {len(passed)} / {len(passed) + len(failed)}")
print(f" FAILED TESTS: {len(failed)}")

if not failed:
    print("\nSTATUS: ALL BONUS ENHANCEMENTS VERIFIED 100% WORKING.")
    sys.exit(0)
else:
    print("\nSTATUS: FAILURES DETECTED IN BONUS ENHANCEMENTS TEST SUITE.")
    sys.exit(1)
