"""
ULTRON LiveLink Mobile & Web Cross-Device Server.
Includes strict Gatekeeper permission enforcement, bi-directional drag-and-drop file transfers,
touchpad remote, clipboard synchronization, and ULTRON command routing.
"""

from __future__ import annotations

import base64
import http.server
import json
import os
import queue
import socket
import socketserver
import threading
import time
from urllib.parse import parse_qs, urlparse

from modules.cross_device_sync import cross_device_sync
from modules.livelink_gatekeeper import MASTER_TOKEN, livelink_gatekeeper
from modules.livelink_stream import livelink_stream_hub

_CHUNK_STORE: dict[str, dict] = {}
_CHUNK_LOCK = threading.Lock()

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

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization, X-LiveLink-Token, X-Filename, X-Target-Folder",
        )
        self.end_headers()

    def _send_json(self, data: dict, status_code: int = 200) -> None:
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-LiveLink-Token, X-Filename, X-Target-Folder")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _send_forbidden(self, msg: str = "Access restricted. You must be authorized by Harsha to control ULTRON.") -> None:
        self._send_json({"error": msg, "restricted": True, "status": "DENIED"}, status_code=403)

    def _extract_token(self, post_data_dict: dict | None = None) -> str:
        # 1. Authorization header: Bearer <token>
        auth_hdr = self.headers.get("Authorization", "")
        if auth_hdr.lower().startswith("bearer "):
            return auth_hdr[7:].strip()

        # 2. X-LiveLink-Token header
        custom_hdr = self.headers.get("X-LiveLink-Token", "").strip()
        if custom_hdr:
            return custom_hdr

        # 3. URL Query Parameter
        if "?" in self.path:
            query = parse_qs(urlparse(self.path).query)
            if "token" in query and query["token"]:
                return query["token"][0].strip()

        # 4. JSON Body
        if post_data_dict and isinstance(post_data_dict, dict):
            return str(post_data_dict.get("token", "")).strip()

        return ""

    def _is_authorized(self, post_data_dict: dict | None = None) -> bool:
        client_ip = self.client_address[0]
        token = self._extract_token(post_data_dict)
        return livelink_gatekeeper.verify_access(token, client_ip)

    def do_GET(self):
        clean_path = self.path.split("?")[0]

        # ── Health & System Status ──
        if clean_path == "/api/status":
            self._send_json({
                "status": "online",
                "system": "ULTRON Holographic Matrix",
                "local_ip": get_local_ip(),
                "livelink": "active",
            })
            return

        # ── LiveLink Verification Status Polling ──
        if clean_path == "/api/livelink/check_status":
            token = self._extract_token()
            res = livelink_gatekeeper.check_status(token)
            self._send_json(res)
            return

        # ── LiveLink Requests List (Admin only) ──
        if clean_path == "/api/livelink/requests":
            client_ip = self.client_address[0]
            token = self._extract_token()
            if client_ip in ("127.0.0.1", "localhost", "::1") or token == MASTER_TOKEN:
                requests = livelink_gatekeeper.list_requests()
                self._send_json({"success": True, "requests": requests})
            else:
                self._send_forbidden("Only Admin Harsha can review LiveLink access requests.")
            return

        # ── LiveLink Server-Sent Events (SSE) Live Stream ──
        if clean_path == "/api/livelink/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            client_q = livelink_stream_hub.add_client()
            try:
                while True:
                    try:
                        msg = client_q.get(timeout=10.0)
                        ev = msg.get("event", "message")
                        data_str = json.dumps(msg.get("data", {}))
                        payload = f"event: {ev}\ndata: {data_str}\n\n".encode("utf-8")
                        self.wfile.write(payload)
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, Exception):
                pass
            finally:
                livelink_stream_hub.remove_client(client_q)
            return

        # ── LiveLink System Hardware Telemetry ──
        if clean_path == "/api/livelink/telemetry":
            telemetry = livelink_stream_hub.get_system_telemetry()
            self._send_json({"success": True, "telemetry": telemetry})
            return

        # ── Clipboard Retrieval (Protected) ──
        if clean_path == "/api/clipboard":
            if not self._is_authorized():
                self._send_forbidden()
                return
            clip_text = cross_device_sync.get_laptop_clipboard_for_phone()
            self._send_json({"clipboard": clip_text})
            return

        # ── LiveLink File List: Laptop -> Phone (Protected) ──
        if clean_path == "/api/livelink/files":
            if not self._is_authorized():
                self._send_forbidden()
                return
            query = parse_qs(urlparse(self.path).query)
            folder = query.get("folder", ["downloads"])[0]
            files = cross_device_sync.list_laptop_files(folder)
            self._send_json({"success": True, "folder": folder, "files": files})
            return

        # ── LiveLink File Download: Laptop -> Phone (Protected) ──
        if clean_path == "/api/livelink/download":
            if not self._is_authorized():
                self._send_forbidden()
                return
            query = parse_qs(urlparse(self.path).query)
            filename = query.get("file", [""])[0]
            folder = query.get("folder", ["downloads"])[0]

            filepath = cross_device_sync.get_file_path(filename, folder)
            if not filepath or not os.path.isfile(filepath):
                self._send_json({"error": f"File '{filename}' not found on laptop."}, status_code=404)
                return

            try:
                with open(filepath, "rb") as f:
                    file_bytes = f.read()

                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", f'attachment; filename="{os.path.basename(filepath)}"')
                self.send_header("Content-Length", str(len(file_bytes)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(file_bytes)
                return
            except Exception as e:
                self._send_json({"error": f"Failed to transfer file: {e}"}, status_code=500)
                return

        # ── Root UI Serving ──
        if clean_path in ["", "/", "/index.html"]:
            index_path = os.path.join(DOCS_DIR, "index.html")
            try:
                with open(index_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(content)
                return
            except Exception as e:
                print(f"[SERVER ERROR] Serving index.html failed: {e}")

        super().do_GET()

    def do_POST(self):
        clean_path = self.path.split("?")[0]
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b""

        # ── 1. LiveLink Access Request (Unauthenticated Gateway) ──
        if clean_path == "/api/livelink/request_access":
            try:
                data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
                name = data.get("name", "")
                phone = data.get("phone", "")
                purpose = data.get("purpose", "")
                client_ip = self.client_address[0]
                user_agent = self.headers.get("User-Agent", "")

                result = livelink_gatekeeper.request_access(
                    name=name,
                    phone=phone,
                    purpose=purpose,
                    client_ip=client_ip,
                    user_agent=user_agent,
                )
                status_code = 200 if result.get("success") else 400
                self._send_json(result, status_code=status_code)
            except Exception as e:
                self._send_json({"error": f"Request processing error: {e}"}, status_code=500)
            return

        # ── 2. LiveLink Admin Action (Approve / Deny / Revoke) ──
        if clean_path == "/api/livelink/admin_action":
            try:
                data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
                client_ip = self.client_address[0]
                admin_token = self._extract_token(data)

                # Admin authentication check
                if client_ip not in ("127.0.0.1", "localhost", "::1") and admin_token != MASTER_TOKEN:
                    self._send_forbidden("Only Admin Harsha can perform administrative actions.")
                    return

                action = data.get("action", "").lower().strip()
                target = data.get("target", "").strip()

                if action == "approve":
                    ok, msg = livelink_gatekeeper.approve_user(target)
                elif action == "deny":
                    ok, msg = livelink_gatekeeper.deny_user(target)
                elif action == "revoke":
                    ok, msg = livelink_gatekeeper.revoke_user(target)
                else:
                    ok, msg = False, f"Unknown action: '{action}'"

                self._send_json({"success": ok, "message": msg})
            except Exception as e:
                self._send_json({"error": str(e)}, status_code=500)
            return

        # ── 3. Drag-and-Drop File Upload: Phone -> Laptop (Protected) ──
        if clean_path == "/api/livelink/upload":
            content_type = self.headers.get("Content-Type", "")

            # Check JSON upload first
            data_dict = {}
            if "application/json" in content_type:
                try:
                    data_dict = json.loads(raw_body.decode("utf-8"))
                except Exception:
                    pass

            if not self._is_authorized(data_dict):
                self._send_forbidden()
                return

            try:
                # Format A: JSON base64
                if "application/json" in content_type and "data" in data_dict:
                    filename = data_dict.get("filename", f"livelink_{int(time.time())}.bin")
                    target_folder = data_dict.get("folder", "downloads")
                    b64_str = data_dict.get("data", "")
                    if "," in b64_str:
                        b64_str = b64_str.split(",", 1)[1]
                    file_bytes = base64.b64decode(b64_str)
                    ok, msg = cross_device_sync.save_file_from_phone(filename, file_bytes, target_folder)
                    if ok:
                        livelink_stream_hub.notify_file_event(filename, "uploaded", target_folder)
                    self._send_json({"success": ok, "message": msg, "filename": filename})
                    return

                # Format B: Raw Binary with Headers
                filename = self.headers.get("X-Filename", f"livelink_drop_{int(time.time())}.bin")
                target_folder = self.headers.get("X-Target-Folder", "downloads")
                ok, msg = cross_device_sync.save_file_from_phone(filename, raw_body, target_folder)
                if ok:
                    livelink_stream_hub.notify_file_event(filename, "uploaded", target_folder)
                self._send_json({"success": ok, "message": msg, "filename": filename})
                return
            except Exception as e:
                self._send_json({"error": f"File upload failed: {e}"}, status_code=500)
            return

        # ── 3B. Chunked File Upload Engine for Large Media (Protected) ──
        if clean_path == "/api/livelink/upload_chunk":
            data_dict = {}
            try:
                data_dict = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            except Exception:
                pass

            if not self._is_authorized(data_dict):
                self._send_forbidden()
                return

            try:
                upload_id = data_dict.get("upload_id", "")
                chunk_index = int(data_dict.get("chunk_index", 0))
                total_chunks = int(data_dict.get("total_chunks", 1))
                filename = data_dict.get("filename", f"livelink_chunk_{int(time.time())}.bin")
                target_folder = data_dict.get("folder", "downloads")
                b64_chunk = data_dict.get("data", "")
                if "," in b64_chunk:
                    b64_chunk = b64_chunk.split(",", 1)[1]
                chunk_bytes = base64.b64decode(b64_chunk)

                with _CHUNK_LOCK:
                    if upload_id not in _CHUNK_STORE:
                        _CHUNK_STORE[upload_id] = {
                            "chunks": {},
                            "total": total_chunks,
                            "filename": filename,
                            "folder": target_folder,
                            "created": time.time(),
                        }
                    _CHUNK_STORE[upload_id]["chunks"][chunk_index] = chunk_bytes

                    if len(_CHUNK_STORE[upload_id]["chunks"]) == total_chunks:
                        full_data = bytearray()
                        for i in range(total_chunks):
                            full_data.extend(_CHUNK_STORE[upload_id]["chunks"][i])
                        del _CHUNK_STORE[upload_id]
                        ok, msg = cross_device_sync.save_file_from_phone(filename, bytes(full_data), target_folder)
                        livelink_stream_hub.notify_file_event(filename, "uploaded", target_folder)
                        self._send_json({"success": ok, "completed": True, "message": msg, "filename": filename})
                        return

                percent = round(((chunk_index + 1) / total_chunks) * 100)
                self._send_json({"success": True, "completed": False, "chunk_index": chunk_index, "progress_percent": percent})
                return
            except Exception as e:
                self._send_json({"error": f"Chunk upload failed: {e}"}, status_code=500)
                return

        # ── 4. Remote PC Multimedia & Power Controls (Protected) ──
        if clean_path == "/api/livelink/control":
            data = {}
            try:
                data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            except Exception:
                pass

            if not self._is_authorized(data):
                self._send_forbidden()
                return

            action = data.get("action", "")
            ok, msg = cross_device_sync.handle_remote_control(action)
            self._send_json({"success": ok, "message": msg})
            return

        # ── 5. Cross-Device Clipboard Push: Phone -> Laptop (Protected) ──
        if clean_path == "/api/clipboard":
            data = {}
            try:
                data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            except Exception:
                pass

            if not self._is_authorized(data):
                self._send_forbidden()
                return

            text = data.get("text", "")
            auto_paste = data.get("auto_paste", False)
            ok, msg = cross_device_sync.set_clipboard_from_phone(text, auto_paste)
            if ok:
                livelink_stream_hub.notify_clipboard(text)
            self._send_json({"success": ok, "message": msg})
            return

        # ── 6. Wireless Mobile Touchpad (Protected) ──
        if clean_path == "/api/touchpad":
            data = {}
            try:
                data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            except Exception:
                pass

            if not self._is_authorized(data):
                self._send_forbidden()
                return

            dx = int(data.get("dx", 0))
            dy = int(data.get("dy", 0))
            action = data.get("action", "move")
            ok = cross_device_sync.handle_touchpad_input(dx, dy, action)
            self._send_json({"success": ok})
            return

        # ── 7. Voice / Text Command Execution (Protected) ──
        if clean_path == "/api/command":
            data = {}
            try:
                data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            except Exception:
                pass

            if not self._is_authorized(data):
                self._send_forbidden()
                return

            cmd = data.get("command", "")
            print(f"[LIVELINK ROUTER] Web server received: '{cmd}'")
            from router import process
            _flag, response = process(cmd)
            reply = response or "Command executed, Harsha!"
            try:
                from speech_engine import speak
                speak(reply)
            except Exception as sp_err:
                print(f"[LIVELINK ROUTER] Speech error: {sp_err}")

            # Mobile deep-linking & ADB execution
            mobile_app = None
            mobile_url = None
            cmd_lower = (cmd or "").lower()

            app_schemes = {
                "whatsapp": ("com.whatsapp", "whatsapp://"),
                "youtube": ("com.google.android.youtube", "vnd.youtube://"),
                "instagram": ("com.instagram.android", "instagram://"),
                "camera": ("com.android.camera", None),
                "spotify": ("com.spotify.music", "spotify://"),
                "settings": ("com.android.settings", None),
                "gallery": ("com.google.android.apps.photos", None),
                "photos": ("com.google.android.apps.photos", None),
                "maps": ("com.google.android.apps.maps", "geo:0,0?q="),
                "chrome": ("com.android.chrome", "googlechrome://"),
            }

            for app_key, (pkg, url_scheme) in app_schemes.items():
                if app_key in cmd_lower:
                    mobile_app = app_key
                    mobile_url = url_scheme
                    try:
                        from modules.adb_bridge import adb_bridge
                        adb_bridge.open_app(app_key)
                    except Exception:
                        pass
                    break

            self._send_json({
                "reply": reply,
                "response": reply,
                "mobile_app": mobile_app,
                "mobile_url": mobile_url,
            })
            return

        super().do_POST()


class ThreadingServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def setup_adb_forwarding(port: int = PORT) -> bool:
    """Sets up ADB reverse and forward port bridge so phone connects directly via USB or Wi-Fi."""
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
    """Starts the LiveLink web server locked to host '0.0.0.0' with fallback port selection."""
    ip = get_local_ip()
    handler = CustomHTTPRequestHandler

    active_port = PORT
    httpd = None

    for candidate_port in [PORT, 8001, 8080, 8888]:
        try:
            httpd = ThreadingServer((HOST, candidate_port), handler)
            active_port = candidate_port
            break
        except Exception:
            continue

    if httpd is None:
        print("[SERVER ERROR] Could not bind web server to any available port.")
        return ip, PORT

    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    setup_adb_forwarding(active_port)
    print(f"[LIVELINK SERVER] Mobile Access Link -> http://{ip}:{active_port}")
    return ip, active_port


if __name__ == "__main__":
    ip, port = start_server_in_background()
    print(f"\n==================================================")
    print(f"[LIVELINK] Mobile Access Link -> http://{ip}:{port}")
    print(f"[LIVELINK] USB ADB Link        -> http://localhost:{port}")
    print(f"==================================================\n")
    import time
    while True:
        time.sleep(1)
