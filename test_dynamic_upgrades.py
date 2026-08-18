"""
test_dynamic_upgrades.py - Test Suite for ULTRON Dynamic Application Discovery & Hardware Telemetry
"""

from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
os.environ["QT_QPA_PLATFORM"] = "offscreen"

print("=" * 80)
print("             ULTRON DYNAMIC UPGRADES VERIFICATION SUITE")
print("=" * 80)

import router
from modules.app_finder import app_finder
from modules.system_control import get_memory_status, get_battery_status, control_volume

passed = []
failed = []

def log_test(name: str, success: bool, details: str):
    if success:
        passed.append(name)
        print(f" [PASS] {name:<55s} : {details}")
    else:
        failed.append((name, details))
        print(f" [FAIL] {name:<55s} : {details}")

# ── TEST 1: DYNAMIC APP FINDER INDEXING ───────────────────────────────────────
print("\n--- TEST 1: Dynamic Application Discovery ---")
try:
    cache_len = len(app_finder.apps_cache)
    if cache_len > 10:
        log_test("TEST 1: Dynamic App Discovery Indexing", True, f"Successfully indexed {cache_len} Start Menu shortcuts")
    else:
        log_test("TEST 1: Dynamic App Discovery Indexing", False, f"Low shortcut count: {cache_len}")
except Exception as e:
    log_test("TEST 1: Dynamic App Discovery Indexing", False, str(e))

# ── TEST 2: DYNAMIC FUZZY MATCHING ───────────────────────────────────────────
print("\n--- TEST 2: Dynamic Fuzzy Match ---")
try:
    match = app_finder.find_app("open cursor") or app_finder.find_app("open file explorer") or app_finder.find_app("open chrome")
    if match:
        log_test("TEST 2: Dynamic Shortcut Match", True, f"Matched app '{match[0]}' -> '{match[1]}'")
    else:
        log_test("TEST 2: Dynamic Shortcut Match", False, "No shortcut match returned")
except Exception as e:
    log_test("TEST 2: Dynamic Shortcut Match", False, str(e))

# ── TEST 3: RAM TELEMETRY ─────────────────────────────────────────────────────
print("\n--- TEST 3: Memory Telemetry (ctypes) ---")
try:
    ram_pct, used_mb, total_mb = get_memory_status()
    if 0 < ram_pct <= 100 and total_mb > 0:
        log_test("TEST 3: RAM Telemetry", True, f"RAM: {ram_pct}% ({used_mb}MB / {total_mb}MB)")
    else:
        log_test("TEST 3: RAM Telemetry", False, f"Invalid memory telemetry: {ram_pct}%")
except Exception as e:
    log_test("TEST 3: RAM Telemetry", False, str(e))

# ── TEST 4: BATTERY TELEMETRY ────────────────────────────────────────────────
print("\n--- TEST 4: Battery Telemetry (ctypes) ---")
try:
    pct, plugged = get_battery_status()
    log_test("TEST 4: Battery Telemetry", True, f"Battery: {pct}%, Plugged: {plugged}")
except Exception as e:
    log_test("TEST 4: Battery Telemetry", False, str(e))

# ── TEST 5: ROUTER SYSTEM COMMAND PROCESSING ────────────────────────────────
print("\n--- TEST 5: Router System Command Processing ---")
try:
    status1, reply1 = router.process("What is my RAM usage?")
    print(f" [ROUTER RAM]: '{reply1}'")
    status2, reply2 = router.process("What is my battery percentage?")
    print(f" [ROUTER BATT]: '{reply2}'")

    if "RAM" in reply1 or "usage" in reply1:
        log_test("TEST 5: Router Telemetry Integration", True, f"RAM response: '{reply1}'")
    else:
        log_test("TEST 5: Router Telemetry Integration", False, f"Unexpected response: '{reply1}'")
except Exception as e:
    log_test("TEST 5: Router Telemetry Integration", False, str(e))

# ── SUMMARY ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("                     TEST SUITE SUMMARY REPORT")
print("=" * 80)
print(f" PASSED TESTS: {len(passed)} / {len(passed) + len(failed)}")
print(f" FAILED TESTS: {len(failed)}")

if not failed:
    print("\nSTATUS: ALL DYNAMIC UPGRADES VERIFIED 100% WORKING.")
    sys.exit(0)
else:
    print("\nSTATUS: FAILURES DETECTED IN DYNAMIC UPGRADES TEST SUITE.")
    sys.exit(1)
