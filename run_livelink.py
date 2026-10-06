"""
run_livelink.py - ULTRON LiveLink Server & Cross-Device Bridge Launcher
"""

import os
import sys
import time
import webbrowser

# Add workspace to path
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from web_server import start_server_in_background, get_local_ip

if __name__ == "__main__":
    ip, port = start_server_in_background()
    phone_url = f"http://{ip}:{port}"
    laptop_url = f"http://localhost:{port}"

    print("\n" + "=" * 56)
    print("      ULTRON LIVELINK SYSTEM ONLINE & READY       ")
    print("=" * 56)
    print(f" [💻 LAPTOP INTERFACE] -> {laptop_url}")
    print(f" [📱 PHONE LIVE LINK]  -> {phone_url}")
    print(f" [📱 USB ADB LINK]     -> http://localhost:{port}")
    print("=" * 56)
    print(" -> Scan the QR Code on your laptop screen to connect your phone instantly.")
    print(" -> Press Ctrl+C in this window to stop the server.\n")

    # Automatically launch laptop interface in browser
    try:
        webbrowser.open(laptop_url)
    except Exception:
        pass

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[LIVELINK] Server stopped gracefully.")
