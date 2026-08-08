"""ULTRON Mobile & Web Cross-Device Server."""

from __future__ import annotations

import os
import socket
import http.server
import socketserver
import threading


PORT = 8000
DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")


def get_local_ip() -> str:
    """Returns the laptop's Wi-Fi / Local IP address for phone connection."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DOCS_DIR, **kwargs)


def start_server_in_background():
    """Starts the web server in a daemon background thread."""
    ip = get_local_ip()
    print(f"🌐 ULTRON Mobile Web Server running at: http://{ip}:{PORT}")

    handler = CustomHTTPRequestHandler
    httpd = socketserver.TCPServer(("", PORT), handler)

    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    return ip, PORT


if __name__ == "__main__":
    ip, port = start_server_in_background()
    print(f"\n==================================================")
    print(f"📲 CONNECT YOUR PHONE TO ULTRON:")
    print(f"1. Connect phone to same Wi-Fi as laptop.")
    print(f"2. Open phone browser and go to: http://{ip}:{port}")
    print(f"3. Tap 'Add to Home Screen' on your phone!")
    print(f"==================================================\n")
    import time
    while True:
        time.sleep(1)
