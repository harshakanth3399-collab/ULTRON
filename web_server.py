"""ULTRON Mobile & Web Cross-Device Server."""

from __future__ import annotations

import os
import json
import socket
import http.server
import socketserver
import threading

PORT = 8000
HOST = "0.0.0.0"
DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")


def get_local_ip() -> str:
    """Returns the laptop's primary local IP address for phone connection."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "10.83.134.102"


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DOCS_DIR, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/status"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status": "online", "system": "ULTRON Holographic Matrix"}')
            return
        super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/command"):
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(post_data)
                cmd = data.get("command", "")
                print(f"[ROUTER] Web server received: '{cmd}'")
                from router import process
                _flag, response = process(cmd)
                reply = response or "Command executed, Harsha!"
                try:
                    from speech_engine import speak
                    speak(reply)
                except Exception as sp_err:
                    print(f"[ROUTER] Web server speech error: {sp_err}")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"reply": reply}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return
        super().do_POST()


class ThreadingServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def setup_adb_forwarding(port: int = PORT) -> bool:
    """Sets up ADB reverse and forward port bridge so phone's http://localhost:8000 connects directly to laptop."""
    try:
        import subprocess
        from modules.adb_bridge import _get_adb_executable
        adb_exe = _get_adb_executable()
        subprocess.run([adb_exe, "reverse", f"tcp:{port}", f"tcp:{port}"], capture_output=True, text=True, timeout=5.0)
        subprocess.run([adb_exe, "forward", f"tcp:{port}", f"tcp:{port}"], capture_output=True, text=True, timeout=5.0)
        return True
    except Exception:
        pass
    return False


def start_server_in_background():
    """Starts the web server locked to host '0.0.0.0' and port 8000."""
    ip = get_local_ip()
    handler = CustomHTTPRequestHandler
    
    httpd = ThreadingServer((HOST, PORT), handler)

    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    setup_adb_forwarding(PORT)
    print(f"[SERVER] Mobile Access Link -> http://{ip}:{PORT}")
    return ip, PORT


if __name__ == "__main__":
    ip, port = start_server_in_background()
    print(f"\n==================================================")
    print(f"[SERVER] Mobile Access Link -> http://{ip}:{port}")
    print(f"[SERVER] USB ADB Link        -> http://localhost:{port}")
    print(f"==================================================\n")
    import time
    while True:
        time.sleep(1)
