import sys
from PySide6.QtWidgets import QApplication, QWidget, QPushButton
from PySide6.QtCore import Qt
from particle_engine import ParticleEngine


class UltronUI(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("ULTRON")
        self.setStyleSheet("background-color: black;")

        # Particle Engine
        self.engine = ParticleEngine()
        self.engine.setParent(self)

        # Mic Button
        self.mic = QPushButton("🎤", self)

        self.mic.setFixedSize(70, 70)

        self.mic.setStyleSheet("""
            QPushButton{
                background:#900000;
                color:white;
                border-radius:35px;
                border:2px solid red;
                font-size:26px;
            }

            QPushButton:hover{
                background:#c00000;
            }

            QPushButton:pressed{
                background:#ff0000;
            }
        """)

        # Show window AFTER everything is created
        self.showFullScreen()

    def resizeEvent(self, event):

        self.engine.setGeometry(self.rect())

        self.mic.move(
            self.width()//2 - 35,
            self.height()-100
        )

        super().resizeEvent(event)


if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = UltronUI()

    window.show()

    sys.exit(app.exec())