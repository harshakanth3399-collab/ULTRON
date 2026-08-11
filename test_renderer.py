"""Smoke test for the ULTRON holographic renderer."""

import sys

from PySide6.QtGui import QSurfaceFormat
from PySide6.QtWidgets import QApplication

from graphics.renderer import UltronRenderer
# 

def _configure_gl() -> None:
    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.CoreProfile)
    fmt.setDepthBufferSize(24)
    QSurfaceFormat.setDefaultFormat(fmt)


def main() -> int:
    _configure_gl()
    app = QApplication(sys.argv)

    widget = UltronRenderer()
    widget.resize(1280, 720)
    widget.setWindowTitle("")
    widget.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
