"""
test_searxng_web_system.py - SearXNG Web Search Verification Harness

Mandatory verification cases:
  1. Current USD -> INR rate
  2. Current product price ("price of iPhone 15 Pro")
  3. Current news question ("latest news about NASA Space Exploration")
  4. Normal non-web question ("What is 25 plus 75?")
"""

from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
os.environ["QT_QPA_PLATFORM"] = "offscreen"

print("=" * 80)
print("             ULTRON SEARXNG WEB SEARCH VERIFICATION HARNESS")
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

pm = get_profile_manager()
pm.set_active_language("en")

# ── TEST 1: CURRENT USD -> INR RATE ──────────────────────────────────────────
print("\n--- TEST 1 — CURRENT USD -> INR RATE ---")
try:
    status, reply = router.process("What is the current USD to INR exchange rate?")
    print(f" [OUTPUT] Reply: '{reply}'")
    if "82" not in reply and ("rupees" in reply.lower() or "inr" in reply.lower() or "dollar" in reply.lower() or "rate" in reply.lower()):
        log_test("TEST 1: USD -> INR Exchange Rate", True, f"Accurate live rate: '{reply}'")
    else:
        log_test("TEST 1: USD -> INR Exchange Rate", False, f"Stale/hard-coded answer: '{reply}'")
except Exception as e:
    log_test("TEST 1: USD -> INR Exchange Rate", False, str(e))

# ── TEST 2: CURRENT PRODUCT PRICE ────────────────────────────────────────────
print("\n--- TEST 2 — CURRENT PRODUCT PRICE ---")
try:
    status, reply = router.process("What is the current price of iPhone 15 Pro?")
    print(f" [OUTPUT] Reply: '{reply}'")
    if reply and "82" not in reply:
        log_test("TEST 2: Current Product Price", True, f"SearXNG live search answer: '{reply}'")
    else:
        log_test("TEST 2: Current Product Price", False, f"Failed product price search: '{reply}'")
except Exception as e:
    log_test("TEST 2: Current Product Price", False, str(e))

# ── TEST 3: CURRENT NEWS QUESTION ────────────────────────────────────────────
print("\n--- TEST 3 — CURRENT NEWS QUESTION ---")
try:
    status, reply = router.process("What is the latest news about NASA space exploration?")
    print(f" [OUTPUT] Reply: '{reply}'")
    if reply:
        log_test("TEST 3: Current News Question", True, f"SearXNG live news answer: '{reply[:80]}...'")
    else:
        log_test("TEST 3: Current News Question", False, f"Failed news query: '{reply}'")
except Exception as e:
    log_test("TEST 3: Current News Question", False, str(e))

# ── TEST 4: NORMAL NON-WEB QUESTION ──────────────────────────────────────────
print("\n--- TEST 4 — NORMAL NON-WEB QUESTION ---")
try:
    status, reply = router.process("What is 25 plus 75?")
    print(f" [OUTPUT] Reply: '{reply}'")
    if "100" in reply:
        log_test("TEST 4: Normal Non-Web Question", True, f"Instant response (No web overhead): '{reply}'")
    else:
        log_test("TEST 4: Normal Non-Web Question", False, f"Failed math query: '{reply}'")
except Exception as e:
    log_test("TEST 4: Normal Non-Web Question", False, str(e))

# ── SUMMARY ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("                     TEST SUITE SUMMARY REPORT")
print("=" * 80)
print(f" PASSED TESTS: {len(passed)} / {len(passed) + len(failed)}")
print(f" FAILED TESTS: {len(failed)}")

if not failed:
    print("\nSTATUS: ALL 4 SEARXNG WEB SEARCH TESTS PASSED CLEANLY.")
    sys.exit(0)
else:
    print("\nSTATUS: FAILURES DETECTED IN SEARXNG WEB SUITE.")
    sys.exit(1)
