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


import json

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
    """Sets up ADB port forwarding so localhost:8000 on phone connects directly via USB/ADB."""
    try:
        import subprocess
        from modules.adb_bridge import _get_adb_executable
        adb_exe = _get_adb_executable()
        res = subprocess.run([adb_exe, "forward", f"tcp:{port}", f"tcp:{port}"], capture_output=True, text=True, timeout=5.0)
        if res.returncode == 0:
            print(f"[MOBILE] ADB Port Forwarding active: phone http://localhost:{port} -> laptop port {port}")
            return True
    except Exception:
        pass
    return False


def start_server_in_background():
    """Starts the web server in a daemon background thread."""
    ip = get_local_ip()
    handler = CustomHTTPRequestHandler
    
    try:
        httpd = ThreadingServer(("0.0.0.0", PORT), handler)
    except Exception as e:
        print(f"[MOBILE ERROR] Could not bind port {PORT}: {e}")
        try:
            httpd = ThreadingServer(("0.0.0.0", 8080), handler)
            print(f"[MOBILE] Bound fallback port 8080")
        except Exception:
            return ip, PORT

    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    setup_adb_forwarding(PORT)
    print(f"[MOBILE] ULTRON Mobile Web Server running at: http://{ip}:{PORT}")
    return ip, PORT


if __name__ == "__main__":
    ip, port = start_server_in_background()
    print(f"\n==================================================")
    print(f"📲 CONNECT YOUR PHONE TO ULTRON:")
    print(f"Option 1 (Wi-Fi):  Open phone browser -> http://{ip}:{port}")
    print(f"Option 2 (USB/ADB): Open phone browser -> http://localhost:{port}")
    print(f"==================================================\n")
    import time
    while True:
        time.sleep(1)
