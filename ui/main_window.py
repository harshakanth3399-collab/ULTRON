"""Fullscreen ULTRON shell — holographic renderer + microphone control."""

from __future__ import annotations

import threading
import time

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QMainWindow, QWidget

from graphics.constants import FRAME_MS, MIC_BUTTON_Y_OFFSET
from graphics.renderer import UltronRenderer
from graphics.state import UltronState
from ui.mic_button import MicButton


class UltronWindow(QMainWindow):
    """Production fullscreen window hosting the GPU renderer and mic button."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: #000000;")

        self._container = QWidget(self)
        self.setCentralWidget(self._container)

        self._renderer = UltronRenderer(self._container)
        self._mic = MicButton(self._container)

        self._renderer.set_speaking_callback(self._is_speaking)
        self._mic.clicked_mic.connect(self._on_mic_pressed)

        self._pulse_time = 0.0
        self._busy = False
        self._is_floating = False
        self._listen_thread: threading.Thread | None = None

        self._ui_timer = QTimer(self)
        self._ui_timer.timeout.connect(self._update_ui)
        self._ui_timer.start(FRAME_MS)

        self.showFullScreen()
        QTimer.singleShot(800, self._greet_harsha)

    def _greet_harsha(self) -> None:
        def _speak_greeting():
            try:
                from speech_engine import speak
                self._set_state(UltronState.SPEAKING)
                speak("Hey Harsha, what's up bro? ULTRON online and ready for you.")
                self._set_state(UltronState.IDLE)
            except Exception:
                self._set_state(UltronState.IDLE)

        threading.Thread(target=_speak_greeting, daemon=True).start()

    def toggle_floating_mode(self) -> None:
        """Toggles between Fullscreen and 1-inch Always-on-Top Floating Desktop Widget mode."""
        self._is_floating = not self._is_floating
        if self._is_floating:
            self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
            screen_geo = self.screen().geometry()
            widget_w, widget_h = 160, 160
            self.setGeometry(screen_geo.width() - widget_w - 30, screen_geo.height() - widget_h - 60, widget_w, widget_h)
            self._mic.hide()
            self.show()
        else:
            self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
            self._mic.show()
            self.showFullScreen()

    def mouseDoubleClickEvent(self, event) -> None:
        self.toggle_floating_mode()
        super().mouseDoubleClickEvent(event)

    def _is_speaking(self) -> bool:
        try:
            from speech_engine import speaking

            return speaking()
        except Exception:
            return False

    def resizeEvent(self, event) -> None:
        self._renderer.setGeometry(self._container.rect())
        if not self._is_floating:
            mic_x = self.width() - self._mic.width() - 40
            mic_y = self.height() - self._mic.height() - 40
            self._mic.move(mic_x, mic_y)
        super().resizeEvent(event)

    def _update_ui(self) -> None:
        self._pulse_time += FRAME_MS / 1000.0
        self._mic.set_pulse(self._pulse_time)
        self._mic.set_listening(self._renderer.state_manager.is_listening())
        self._mic.set_active(self._renderer.state_manager.is_speaking())

    def _on_mic_pressed(self) -> None:
        if self._busy:
            return
        self._busy = True
        self._listen_thread = threading.Thread(target=self._listen_and_respond, daemon=True)
        self._listen_thread.start()

    def _listen_and_respond(self) -> None:
        try:
            self._set_state(UltronState.LISTENING)

            from speech import listen
            from router import process
            from speech_engine import speak

            command = listen()
            if not command:
                self._set_state(UltronState.IDLE)
                return

            running, answer = process(command)

            if answer:
                self._set_state(UltronState.SPEAKING)
                speak(answer)
                self._wait_until_done_speaking()

            self._set_state(UltronState.IDLE)

            if running is False:
                QTimer.singleShot(0, self.close)

        except Exception:
            self._set_state(UltronState.IDLE)
        finally:
            self._busy = False

    def _wait_until_done_speaking(self) -> None:
        deadline = time.time() + 120.0
        while time.time() < deadline:
            if not self._is_speaking():
                break
            time.sleep(0.05)

    def _set_state(self, state: UltronState) -> None:
        QTimer.singleShot(0, lambda: self._renderer.set_state(state))

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() in (Qt.Key_F11, Qt.Key_Tab):
            self.toggle_floating_mode()
        elif event.key() in (Qt.Key_Return, Qt.Key_Space):
            self._on_mic_pressed()
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        self._renderer.shutdown()
        super().closeEvent(event)
