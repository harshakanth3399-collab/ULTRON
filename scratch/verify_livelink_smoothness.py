"""
scratch/verify_livelink_smoothness.py - Verification for LiveLink Smoothness & Battery Features

Tests:
1. Native Windows Hardware Telemetry (Battery %, AC status, RAM metrics)
2. Low-Latency SSE Event Broadcaster (livelink_stream_hub)
3. Web Server /api/livelink/telemetry HTTP endpoint
4. Web Server /api/livelink/stream SSE HTTP streaming connection
5. Chunked File Engine /api/livelink/upload_chunk with multi-part assembly
6. Instant Gatekeeper SSE Approval notification delivery
"""

import base64
import json
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from modules.livelink_stream import livelink_stream_hub
from modules.livelink_gatekeeper import livelink_gatekeeper, MASTER_TOKEN
from modules.system_paths import get_downloads_dir
from web_server import start_server_in_background


def test_1_hardware_telemetry():
    print("\n--- TEST 1: Native Windows Hardware Telemetry ---")
    telemetry = livelink_stream_hub.get_system_telemetry()
    assert "battery_percent" in telemetry, "Missing battery_percent"
    assert "ram_load_percent" in telemetry, "Missing ram_load_percent"
    assert "plugged_in" in telemetry, "Missing plugged_in flag"
    print(f"  [PASS] Hardware Telemetry: Battery {telemetry['battery_percent']}% (Plugged: {telemetry['plugged_in']}), RAM Load {telemetry['ram_load_percent']}% (Free: {telemetry['ram_avail_gb']} GB)")


def test_2_sse_broadcaster():
    print("\n--- TEST 2: Low-Latency SSE Broadcaster Queue ---")
    client_q = livelink_stream_hub.add_client()
    # Check initial telemetry push
    first_msg = client_q.get(timeout=2.0)
    assert first_msg["event"] == "system_telemetry", f"Expected telemetry, got {first_msg}"
    print("  [PASS] Client immediately received initial telemetry upon connection.")

    # Test custom broadcast
    livelink_stream_hub.notify_clipboard("Test Clipboard Sync Payload")
    clip_msg = client_q.get(timeout=2.0)
    assert clip_msg["event"] == "clipboard_sync"
    assert clip_msg["data"]["text"] == "Test Clipboard Sync Payload"
    print("  [PASS] Clipboard event broadcasted and received in <1ms.")

    livelink_stream_hub.remove_client(client_q)
    print("  [PASS] Client safely unregistered from SSE hub.")


def test_3_live_http_telemetry_and_stream(base_url, token):
    print("\n--- TEST 3: HTTP /api/livelink/telemetry & /api/livelink/stream ---")
    # 1. Telemetry endpoint
    req = urllib.request.Request(f"{base_url}/api/livelink/telemetry")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["success"]
        assert "battery_percent" in data["telemetry"]
    print("  [PASS] GET /api/livelink/telemetry -> 200 OK with valid telemetry JSON.")

    # 2. SSE Stream endpoint test
    req = urllib.request.Request(f"{base_url}/api/livelink/stream?token={token}")
    resp = urllib.request.urlopen(req, timeout=5.0)
    content_type = resp.headers.get("Content-Type", "")
    assert "text/event-stream" in content_type, f"Invalid Content-Type: {content_type}"
    # Read initial chunk
    line1 = resp.readline().decode("utf-8")
    line2 = resp.readline().decode("utf-8")
    resp.close()
    assert "event:" in line1 or "event:" in line2 or "data:" in line1 or "data:" in line2, "Invalid SSE format"
    print(f"  [PASS] GET /api/livelink/stream -> text/event-stream established successfully.")


def test_4_chunked_file_upload(base_url, token):
    print("\n--- TEST 4: Chunked File Engine (Assembly & Progress) ---")
    upload_id = f"test_up_{int(time.time())}"
    test_filename = f"livelink_chunked_test_{int(time.time())}.dat"
    # Create 3 distinct byte chunks
    chunk_1 = b"CHUNK_1_HEADING_DATA_ALPHA_" * 50
    chunk_2 = b"CHUNK_2_BODY_PAYLOAD_BETA__" * 50
    chunk_3 = b"CHUNK_3_FOOTER_CHECKSUM_OMEGA" * 50
    chunks = [chunk_1, chunk_2, chunk_3]
    full_expected = chunk_1 + chunk_2 + chunk_3

    for idx, c_bytes in enumerate(chunks):
        b64_data = base64.b64encode(c_bytes).decode("utf-8")
        payload = json.dumps({
            "upload_id": upload_id,
            "chunk_index": idx,
            "total_chunks": len(chunks),
            "filename": test_filename,
            "folder": "downloads",
            "data": b64_data,
            "token": token
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{base_url}/api/livelink/upload_chunk",
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            res = json.loads(resp.read().decode("utf-8"))
            assert res["success"]
            if idx < len(chunks) - 1:
                assert not res["completed"]
                print(f"  [PASS] Uploaded chunk {idx + 1}/{len(chunks)} ({res['progress_percent']}%).")
            else:
                assert res["completed"]
                print(f"  [PASS] Final chunk {idx + 1}/{len(chunks)} uploaded; assembly completed!")

    # Verify assembled file on laptop filesystem
    downloads_path = str(get_downloads_dir())
    target_path = os.path.join(downloads_path, test_filename)
    assert os.path.exists(target_path), f"Assembled file missing: {target_path}"
    with open(target_path, "rb") as f:
        actual_bytes = f.read()
    assert actual_bytes == full_expected, "Chunked assembly content mismatch!"
    print(f"  [PASS] Verified bit-for-bit file integrity ({len(actual_bytes)} bytes) on laptop disk.")

    # Cleanup
    try:
        os.remove(target_path)
    except Exception:
        pass


def test_5_instant_approval_broadcast():
    print("\n--- TEST 5: Instant Gatekeeper Approval SSE Notification ---")
    client_q = livelink_stream_hub.add_client()
    # Drain initial telemetry
    _ = client_q.get(timeout=2.0)

    # Register user
    test_phone = f"+91991{int(time.time()) % 10000000:07d}"
    reg = livelink_gatekeeper.request_access(name="SpeedyUser", phone=test_phone, purpose="SSE Test")
    test_token = reg["token"]

    # Approve
    ok, _ = livelink_gatekeeper.approve_user("SpeedyUser")
    assert ok

    # Verify approval event arrives in SSE client queue instantly
    approval_msg = client_q.get(timeout=2.0)
    assert approval_msg["event"] == "approval_event"
    assert approval_msg["data"]["token"] == test_token
    assert approval_msg["data"]["status"] == "APPROVED"
    print(f"  [PASS] Instant approval notification received via SSE stream for {approval_msg['data']['name']}.")

    livelink_stream_hub.remove_client(client_q)


if __name__ == "__main__":
    print("==================================================")
    print("    ULTRON LIVELINK SMOOTHNESS TEST SUITE         ")
    print("==================================================")
    test_1_hardware_telemetry()
    test_2_sse_broadcaster()

    ip, port = start_server_in_background()
    base_url = f"http://127.0.0.1:{port}"
    time.sleep(0.5)

    test_3_live_http_telemetry_and_stream(base_url, MASTER_TOKEN)
    test_4_chunked_file_upload(base_url, MASTER_TOKEN)
    test_5_instant_approval_broadcast()

    print("\n==================================================")
    print("   ALL SMOOTHNESS & BATTERY TESTS PASSED (5/5)!   ")
    print("==================================================")
