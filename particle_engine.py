from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget
import math


class ParticleEngine(QWidget):

    def __init__(self):
        super().__init__()

        self.angle = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(16)      # ~60 FPS

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing)

        painter.fillRect(self.rect(), Qt.black)

        cx = self.width() / 2
        cy = self.height() / 2

        pen = QPen(QColor(255, 30, 30))
        pen.setWidth(2)

        painter.setPen(pen)

        for ring in range(5):

            radius = 70 + ring * 30

            offset = self.angle * (ring + 1)

            for i in range(180):

                a = math.radians(i * 2 + offset)

                x = cx + radius * math.cos(a)

                y = cy + radius * math.sin(a)

                painter.drawPoint(int(x), int(y))

        painter.setBrush(QColor(255, 40, 40))

        painter.setPen(Qt.NoPen)

        painter.drawEllipse(int(cx - 8), int(cy - 8), 16, 16)

        self.angle += 0.5