"""Red glowing microphone control — no text, pure vector rendering."""

from __future__ import annotations

import math

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

from graphics.constants import MIC_BUTTON_RADIUS


class MicButton(QWidget):
    """Circular microphone button with pulsing red glow."""

    clicked_mic = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._radius = MIC_BUTTON_RADIUS
        self._pulse = 0.0
        self._active = False
        self._hover = False
        self._listening = False

        size = (self._radius + 24) * 2
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def set_active(self, active: bool) -> None:
        self._active = active
        self.update()

    def set_listening(self, listening: bool) -> None:
        self._listening = listening
        self.update()

    def set_pulse(self, phase: float) -> None:
        self._pulse = phase
        self.update()

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked_mic.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cx = self.width() * 0.5
        cy = self.height() * 0.5
        r = float(self._radius)

        pulse = 0.5 + 0.5 * math.sin(self._pulse * 3.0)
        listen_boost = 1.35 if self._listening else 1.0
        hover_boost = 1.15 if self._hover else 1.0
        active_boost = 1.25 if self._active else 1.0

        halo_r = r * (1.55 + pulse * 0.12) * listen_boost
        halo = QRadialGradient(cx, cy, halo_r)
        halo.setColorAt(0.0, QColor(255, 40, 20, int(90 * listen_boost)))
        halo.setColorAt(0.45, QColor(180, 10, 5, 35))
        halo.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(halo)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(cx - halo_r), int(cy - halo_r), int(halo_r * 2), int(halo_r * 2))

        body = QRadialGradient(cx, cy - r * 0.2, r * 1.2)
        body.setColorAt(0.0, QColor(255, int(60 * hover_boost), int(30 * active_boost)))
        body.setColorAt(0.55, QColor(int(180 * active_boost), 15, 8))
        body.setColorAt(1.0, QColor(80, 5, 2))
        painter.setBrush(body)
        pen = QPen(QColor(255, int(80 + pulse * 60), 40, 200))
        pen.setWidthF(2.0 + pulse * 0.8)
        painter.setPen(pen)
        painter.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 220, 210, 230))

        mic_w = r * 0.34
        mic_h = r * 0.48
        mic_x = cx - mic_w * 0.5
        mic_y = cy - mic_h * 0.55
        painter.drawRoundedRect(
            int(mic_x), int(mic_y), int(mic_w), int(mic_h), int(mic_w * 0.45), int(mic_w * 0.45)
        )

        arc_r = mic_w * 0.72
        arc_pen = QPen(QColor(255, 220, 210, 220))
        arc_pen.setWidthF(max(2.0, r * 0.07))
        arc_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(arc_pen)
        painter.setBrush(Qt.NoBrush)
        rect_x = cx - arc_r
        rect_y = cy - arc_r * 0.35
        painter.drawArc(
            int(rect_x),
            int(rect_y),
            int(arc_r * 2),
            int(arc_r * 2),
            30 * 16,
            120 * 16,
        )

        stem_pen = QPen(QColor(255, 220, 210, 220))
        stem_pen.setWidthF(max(2.0, r * 0.07))
        stem_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(stem_pen)
        painter.drawLine(int(cx), int(cy + arc_r * 0.55), int(cx), int(cy + r * 0.55))

        base_w = mic_w * 0.9
        painter.drawLine(
            int(cx - base_w * 0.5),
            int(cy + r * 0.55),
            int(cx + base_w * 0.5),
            int(cy + r * 0.55),
        )

        painter.end()
