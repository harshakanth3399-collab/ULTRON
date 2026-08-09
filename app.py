"""
ULTRON desktop holographic interface.
app.py only defines functions — it does NOT run any code at import time.
This ensures importing app from main.py never triggers re-initialization.
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
    from ui.main_window import UltronWindow

    print("[BOOT] launch_app entered", flush=True)
    _configure_gl()

    app = QApplication(sys.argv)
    app.setApplicationName("ULTRON")
    print("[BOOT] QApplication created", flush=True)

    window = UltronWindow()
    print("[BOOT] main window created", flush=True)
    window.show()
    print("[BOOT] window shown", flush=True)

    return app.exec()
