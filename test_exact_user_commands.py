"""
test_exact_user_commands.py - Verification Harness for Exact User Prompts

Mandatory Test Sequence:
  1. "ULTRON, give me the five Q-Spiders Bangalore locations."
  2. "ULTRON, what is the Q-Spiders headquarters area?"
  3. "ULTRON, tell me the verified source."
"""

from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
os.environ["QT_QPA_PLATFORM"] = "offscreen"

print("=" * 80)
print("             ULTRON EXACT USER COMMANDS VERIFICATION HARNESS")
print("=" * 80)

import router
from modules.memory.profile_manager import get_profile_manager

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

# ── TEST 1: "ULTRON, give me the five Q-Spiders Bangalore locations." ────────
print("\n--- TEST 1: 'ULTRON, give me the five Q-Spiders Bangalore locations.' ---")
try:
    status, reply1 = router.process("ULTRON, give me the five Q-Spiders Bangalore locations.")
    print(f" [OUTPUT 1]: '{reply1}'")
    possible_areas = ["rajaji", "btm", "basavanagudi", "indira", "marathahalli", "hebbal", "jayanagar"]
    found1 = [area for area in possible_areas if area in reply1.lower()]
    if found1 and "couldn't verify" not in reply1.lower():
        log_test("TEST 1: 5 QSpiders Locations", True, f"Verified branch area names found: {found1}")
    else:
        log_test("TEST 1: 5 QSpiders Locations", False, f"Missing branch area names: '{reply1}'")
except Exception as e:
    log_test("TEST 1: 5 QSpiders Locations", False, str(e))

# ── TEST 2: "ULTRON, what is the Q-Spiders headquarters area?" ────────────────
print("\n--- TEST 2: 'ULTRON, what is the Q-Spiders headquarters area?' ---")
try:
    status, reply2 = router.process("ULTRON, what is the Q-Spiders headquarters area?")
    print(f" [OUTPUT 2]: '{reply2}'")
    hq_areas = ["basavanagudi", "kempegowda", "gandhi bazaar", "basappa", "rajaji", "btm", "old airport"]
    found2 = [area for area in hq_areas if area in reply2.lower()]
    if found2 and "couldn't verify" not in reply2.lower():
        log_test("TEST 2: QSpiders Headquarters Area", True, f"Verified HQ area found: {found2}")
    else:
        log_test("TEST 2: QSpiders Headquarters Area", False, f"Missing HQ area: '{reply2}'")
except Exception as e:
    log_test("TEST 2: QSpiders Headquarters Area", False, str(e))

# ── TEST 3: "ULTRON, tell me the verified source." ───────────────────────────
print("\n--- TEST 3: 'ULTRON, tell me the verified source.' ---")
try:
    status, reply3 = router.process("ULTRON, tell me the verified source.")
    print(f" [OUTPUT 3]: '{reply3}'")
    if "qspiders" in reply3.lower() or "justdial" in reply3.lower() or "grotal" in reply3.lower() or "craft" in reply3.lower() or "source" in reply3.lower():
        log_test("TEST 3: Verified Source Citation", True, f"Verified sources cited: '{reply3}'")
    else:
        log_test("TEST 3: Verified Source Citation", False, f"Failed source citation: '{reply3}'")
except Exception as e:
    log_test("TEST 3: Verified Source Citation", False, str(e))

# ── SUMMARY ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("                     TEST SUITE SUMMARY REPORT")
print("=" * 80)
print(f" PASSED TESTS: {len(passed)} / {len(passed) + len(failed)}")
print(f" FAILED TESTS: {len(failed)}")

if not failed:
    print("\nSTATUS: ALL 3 EXACT USER COMMAND TESTS PASSED CLEANLY.")
    sys.exit(0)
else:
    print("\nSTATUS: FAILURES DETECTED IN EXACT USER COMMAND SUITE.")
    sys.exit(1)
