"""ULTRON desktop holographic interface entry point."""

import sys

from PySide6.QtGui import QSurfaceFormat
from PySide6.QtWidgets import QApplication

from ui.main_window import UltronWindow


def _configure_gl() -> None:
    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.CoreProfile)
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    fmt.setSwapInterval(1)
    QSurfaceFormat.setDefaultFormat(fmt)


def main() -> int:
    _configure_gl()
    app = QApplication(sys.argv)
    app.setApplicationName("ULTRON")

    window = UltronWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
