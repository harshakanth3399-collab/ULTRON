"""
ULTRON desktop holographic interface.
app.py only defines functions — it does NOT run any code at import time.
"""
import sys


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

    print("[BOOT] launch_app entered", flush=True)
    _configure_gl()

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("ULTRON")
    # Do NOT quit when last window closes — we control lifecycle
    app.setQuitOnLastWindowClosed(False)

    print("[BOOT] QApplication created", flush=True)

    # Auto-start Mobile Web Server
    try:
        from web_server import start_server_in_background
        ip, port = start_server_in_background()
        
        # Auto-index personal project data & memory in background
        try:
            import threading
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
    print("[BOOT] main window created", flush=True)

    # Step 1: Show as a NORMAL window first so Qt registers it
    # (showFullScreen directly from hidden state causes exit code 1 on some Intel drivers)
    window.show()
    print("[BOOT] window shown (normal)", flush=True)

    # Step 2: Go fullscreen 200ms later, after event loop starts and first paint completes
    def _go_fullscreen():
        print("[BOOT] switching to fullscreen", flush=True)
        window.showFullScreen()

    QTimer.singleShot(200, _go_fullscreen)

    # Step 3: Start voice pipeline 1.5s after event loop starts
    QTimer.singleShot(1500, window._start_pipeline)
    print("[BOOT] voice pipeline scheduled", flush=True)

    print("[DEBUG] app.exec() starting — UI is alive", flush=True)
    result = app.exec()
    print(f"[DEBUG] app.exec() returned {result}", flush=True)
    return result
