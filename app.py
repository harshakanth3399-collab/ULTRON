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
    from PySide6.QtCore import QTimer

    print("[BOOT] launch_app entered", flush=True)

    # Must be set before QApplication
    _configure_gl()

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("ULTRON")

    # Prevent Qt from quitting when window is closed (safety guard)
    app.setQuitOnLastWindowClosed(False)

    print("[BOOT] QApplication created", flush=True)

    # Import window here (triggers speech/whisper init exactly once)
    from ui.main_window import UltronWindow
    window = UltronWindow()
    print("[BOOT] main window created", flush=True)

    # Show fullscreen AFTER __init__ completes and BEFORE app.exec()
    window.showFullScreen()
    print("[BOOT] window shown — entering event loop", flush=True)

    # Start voice pipeline 1.2s after event loop starts
    # (gives initializeGL time to complete on first paint)
    QTimer.singleShot(1200, window._start_pipeline)
    print("[BOOT] voice pipeline scheduled to start in 1.2s", flush=True)

    # Re-enable quit-on-close after 3s (so Esc / close button works normally)
    QTimer.singleShot(3000, lambda: app.setQuitOnLastWindowClosed(True))

    print("[DEBUG] app.exec() starting — UI is alive", flush=True)
    return app.exec()
