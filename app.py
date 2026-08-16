"""
ULTRON desktop holographic interface.
app.py only defines functions — it does NOT run any code at import time.
"""
from __future__ import annotations

import os
import socket
import sys
import threading

_SINGLE_INSTANCE_PORT = 9899


def _check_single_instance(window_holder: list) -> socket.socket | None:
    """
    Ensures single instance behavior.
    If ULTRON is already running, brings the existing window to front and exits this new process.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(('127.0.0.1', _SINGLE_INSTANCE_PORT))
        s.listen(1)

        def _listen_loop():
            while True:
                try:
                    conn, _ = s.accept()
                    data = conn.recv(1024).decode('utf-8', errors='ignore')
                    if "FOREGROUND" in data and window_holder and window_holder[0]:
                        w = window_holder[0]
                        w.showNormal()
                        w.raise_()
                        w.activateWindow()
                    conn.close()
                except Exception:
                    break

        t = threading.Thread(target=_listen_loop, daemon=True, name="SingleInstanceListener")
        t.start()
        return s
    except (OSError, socket.error):
        print("[SINGLE INSTANCE] ULTRON is already running! Bringing existing window to foreground...", flush=True)
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('127.0.0.1', _SINGLE_INSTANCE_PORT))
            client.sendall(b"FOREGROUND")
            client.close()
        except Exception:
            pass
        sys.exit(0)


def _configure_gl() -> None:
    from PySide6.QtGui import QSurfaceFormat
    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.CoreProfile)
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    fmt.setSwapInterval(1)
    QSurfaceFormat.setDefaultFormat(fmt)


def main() -> int:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer, Qt

    window_holder = [None]
    _check_single_instance(window_holder)

    print("[BOOT] launch_app entered", flush=True)
    _configure_gl()

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("ULTRON")
    app.setQuitOnLastWindowClosed(True)

    print("[BOOT] QApplication created", flush=True)

    # Auto-start Mobile Web Server
    try:
        from web_server import start_server_in_background
        ip, port = start_server_in_background()

        # Auto-index personal project data & memory in background
        try:
            from modules.memory.vector_memory import vector_memory
            threading.Thread(target=vector_memory.index_workspace, args=(".",), daemon=True).start()
            print("[BOOT] Long-Term Semantic Vector Memory active & indexing workspace.", flush=True)
        except Exception as e:
            print(f"[VECTOR MEMORY BOOT] Note: {e}", flush=True)

        print(f"\n==================================================", flush=True)
        print(f"[MOBILE] ULTRON MOBILE WEB SERVER ACTIVE!", flush=True)
        print(f"[MOBILE] Open your phone Chrome browser and go to:", flush=True)
        print(f" -> Option 1 (USB Cable / ADB): http://localhost:{port}", flush=True)
        print(f" -> Option 2 (Wi-Fi / Hotspot): http://{ip}:{port}", flush=True)
        print(f"==================================================\n", flush=True)
    except Exception as e:
        print(f"[WEB SERVER] Server startup note: {e}", flush=True)

    from ui.main_window import UltronWindow

    window = UltronWindow()
    window_holder[0] = window
    print("[BOOT] main window created", flush=True)

    # Bring UI visibly to foreground
    window.showNormal()
    window.raise_()
    window.activateWindow()
    print("[BOOT] window shown (visible foreground)", flush=True)

    def _go_fullscreen():
        print("[BOOT] switching to fullscreen", flush=True)
        window.showFullScreen()
        window.raise_()
        window.activateWindow()

    QTimer.singleShot(200, _go_fullscreen)
    QTimer.singleShot(1500, window._start_pipeline)
    print("[BOOT] voice pipeline scheduled", flush=True)

    print("[DEBUG] app.exec() starting — UI is alive", flush=True)
    result = app.exec()
    print(f"[DEBUG] app.exec() returned {result}", flush=True)
    return result
