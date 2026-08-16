"""
test_qspiders_deep_pipeline.py - Verification Harness for QSpiders Branch Extraction

Mandatory User Test:
  "QSpiders Bangalore locations — give me all branch area names."
"""

from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
os.environ["QT_QPA_PLATFORM"] = "offscreen"

print("=" * 80)
print("             ULTRON DEEP WEB EXTRACTION VERIFICATION HARNESS")
print("=" * 80)

import router
from modules.memory.profile_manager import get_profile_manager

pm = get_profile_manager()
pm.set_active_language("en")

query = "QSpiders Bangalore locations — give me all branch area names."
print(f"\n--- TESTING QUERY: '{query}' ---")

try:
    status, reply = router.process(query)
    print("\n" + "=" * 80)
    print("AI RESPONSE GENERATED:")
    print("=" * 80)
    print(reply)
    print("=" * 80)

    # Check for known Bangalore areas in response
    possible_areas = ["rajaji", "btm", "basavanagudi", "indira", "marathahalli", "hebbal", "jayanagar", "electronic city", "hsr"]
    found_areas = [area for area in possible_areas if area in reply.lower()]

    if len(found_areas) >= 2 and "couldn't verify" not in reply.lower():
        print(f"\n [PASS] DEEP WEB EXTRACTION SUCCESSFUL! Verified branch areas found in reply: {found_areas}")
        sys.exit(0)
    else:
        print(f"\n [FAIL] Incomplete branch list in response. Found: {found_areas}")
        sys.exit(1)

except Exception as e:
    print(f"\n [FAIL] Exception during deep web research pipeline: {e}")
    sys.exit(1)
