"""Futuristic UI Shell for ULTRON — hosting the locked 150,000 particle visualizer & real state HUD."""

from __future__ import annotations

import sys
from PySide6.QtCore import QTimer, Qt, Slot
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMainWindow, QVBoxLayout, QWidget

from graphics.constants import FRAME_MS
from graphics.renderer import UltronRenderer
from graphics.state import UltronState
from ui.mic_button import MicButton

from core.voice_state import VoiceState, voice_state_manager
from core.voice_pipeline import voice_pipeline


class UltronWindow(QMainWindow):
    """Production window hosting the locked particle renderer & futuristic HUD UI."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("ULTRON AI ASSISTANT")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: #000000;")

        self._container = QWidget(self)
        self.setCentralWidget(self._container)

        # 1. LOCKED Particle Renderer (Background Centerpiece)
        self._renderer = UltronRenderer(self._container)
        self._renderer.set_speaking_callback(self._is_speaking)

        # 2. Transparent UI Overlay Layout
        self._overlay = QWidget(self._container)
        self._overlay.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self._setup_ui()

        # Connect Voice State Machine and Pipeline
        voice_state_manager.add_listener(self._on_voice_state_changed)
        voice_pipeline.set_chat_callback(self._on_chat_message)

        self._pulse_time = 0.0
        self._is_floating = False

        self._ui_timer = QTimer(self)
        self._ui_timer.timeout.connect(self._update_ui)
        self._ui_timer.start(FRAME_MS)

        self.showFullScreen()

        # Start Voice Pipeline
        QTimer.singleShot(500, voice_pipeline.start)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self._overlay)
        main_layout.setContentsMargins(40, 30, 40, 20)
        main_layout.setSpacing(15)

        # ── Header Bar ────────────────────────────────────────────────────────
        header_layout = QHBoxLayout()

        title_vbox = QVBoxLayout()
        self._lbl_title = QLabel("ULTRON")
        self._lbl_title.setStyleSheet(
            "font-size: 32px; font-weight: 900; color: #00D9FF; letter-spacing: 4px; background: transparent;"
        )
        self._lbl_subtitle = QLabel("PERSONAL AI ASSISTANT")
        self._lbl_subtitle.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #64748B; letter-spacing: 3px; background: transparent;"
        )
        title_vbox.addWidget(self._lbl_title)
        title_vbox.addWidget(self._lbl_subtitle)
        header_layout.addLayout(title_vbox)

        header_layout.addStretch()

        # Status Pill Badge
        self._lbl_status_pill = QLabel("🟢 SYSTEM ONLINE")
        self._lbl_status_pill.setStyleSheet("""
            background: rgba(0, 217, 255, 0.12);
            border: 1px solid #00D9FF;
            border-radius: 16px;
            color: #00D9FF;
            font-size: 12px;
            font-weight: 700;
            padding: 6px 16px;
        """)
        header_layout.addWidget(self._lbl_status_pill)

        main_layout.addLayout(header_layout)

        main_layout.addStretch(1)

        # ── Subtitle / Real State Status Label ─────────────────────────────────
        self._lbl_state_status = QLabel("Listening for 'Hey Ultron'...")
        self._lbl_state_status.setAlignment(Qt.AlignCenter)
        self._lbl_state_status.setStyleSheet(
            "font-size: 20px; font-weight: 700; color: #FFBF26; letter-spacing: 2px; background: transparent;"
        )
        main_layout.addWidget(self._lbl_state_status)

        # ── Minimal Conversation Card ──────────────────────────────────────────
        self._chat_card = QFrame()
        self._chat_card.setStyleSheet("""
            QFrame {
                background: rgba(10, 15, 30, 0.85);
                border: 1px solid rgba(0, 217, 255, 0.25);
                border-radius: 16px;
                padding: 16px;
            }
        """)
        chat_layout = QVBoxLayout(self._chat_card)
        chat_layout.setContentsMargins(20, 14, 20, 14)
        chat_layout.setSpacing(8)

        self._lbl_chat_user = QLabel("USER: Say 'Hey Ultron' to start")
        self._lbl_chat_user.setStyleSheet(
            "font-size: 14px; font-weight: 600; color: #94A3B8; background: transparent;"
        )
        self._lbl_chat_ultron = QLabel("ULTRON: Online and ready for you, Harsha.")
        self._lbl_chat_ultron.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #00D9FF; background: transparent;"
        )
        chat_layout.addWidget(self._lbl_chat_user)
        chat_layout.addWidget(self._lbl_chat_ultron)

        self._chat_card.setFixedWidth(640)
        chat_wrapper = QHBoxLayout()
        chat_wrapper.addStretch()
        chat_wrapper.addWidget(self._chat_card)
        chat_wrapper.addStretch()
        main_layout.addLayout(chat_wrapper)

        # ── Microphone Control Button ─────────────────────────────────────────
        self._mic = MicButton(self._overlay)
        self._mic.clicked_mic.connect(self._on_mic_clicked)

        mic_wrapper = QHBoxLayout()
        mic_wrapper.addStretch()
        mic_wrapper.addWidget(self._mic)
        mic_wrapper.addStretch()
        main_layout.addLayout(mic_wrapper)

        main_layout.addStretch(1)

        # ── Footer Status Metrics ─────────────────────────────────────────────
        footer_layout = QHBoxLayout()
        self._lbl_footer = QLabel("Microphone: Active (Audio-Gated)  |  AI: Ollama Local  |  Voice: Christopher Deep")
        self._lbl_footer.setAlignment(Qt.AlignCenter)
        self._lbl_footer.setStyleSheet(
            "font-size: 12px; font-weight: 600; color: #475569; background: transparent;"
        )
        footer_layout.addWidget(self._lbl_footer)
        main_layout.addLayout(footer_layout)

    def _is_speaking(self) -> bool:
        try:
            from speech_engine import speaking
            return speaking()
        except Exception:
            return False

    def resizeEvent(self, event) -> None:
        self._renderer.setGeometry(self._container.rect())
        self._overlay.setGeometry(self._container.rect())
        super().resizeEvent(event)

    def _on_chat_message(self, speaker: str, text: str) -> None:
        """Updates UI chat card with actual conversation."""
        QTimer.singleShot(0, lambda: self._update_chat_ui(speaker, text))

    def _update_chat_ui(self, speaker: str, text: str) -> None:
        if speaker == "USER":
            self._lbl_chat_user.setText(f"USER: \"{text}\"")
        elif speaker == "ULTRON":
            self._lbl_chat_ultron.setText(f"ULTRON: \"{text}\"")

    def _on_voice_state_changed(self, state: VoiceState, message: str) -> None:
        """Receives real Voice State Machine events and updates UI."""
        QTimer.singleShot(0, lambda: self._apply_voice_state_ui(state, message))

    def _apply_voice_state_ui(self, state: VoiceState, message: str) -> None:
        # 1. Update Subtitle Status Label
        if state == VoiceState.IDLE:
            self._lbl_state_status.setText("Listening for 'Hey Ultron'...")
            self._lbl_status_pill.setText("🟢 SYSTEM ONLINE")
            self._lbl_status_pill.setStyleSheet("background: rgba(0, 217, 255, 0.12); border: 1px solid #00D9FF; color: #00D9FF;")
            self._renderer.set_state(UltronState.IDLE)

        elif state == VoiceState.WAKE_DETECTED:
            self._lbl_state_status.setText("Wake Word Detected!")
            self._lbl_status_pill.setText("⚡ WAKE DETECTED")
            self._lbl_status_pill.setStyleSheet("background: rgba(255, 191, 38, 0.2); border: 1px solid #FFBF26; color: #FFBF26;")

        elif state == VoiceState.GREETING:
            self._lbl_state_status.setText("Greeting...")
            self._lbl_status_pill.setText("🔊 SPEAKING")

        elif state in (VoiceState.LISTENING, VoiceState.RECORDING):
            self._lbl_state_status.setText("Listening to you...")
            self._lbl_status_pill.setText("🎙️ LISTENING")
            self._lbl_status_pill.setStyleSheet("background: rgba(255, 60, 40, 0.2); border: 1px solid #FF3C28; color: #FF3C28;")
            self._renderer.set_state(UltronState.LISTENING)

        elif state == VoiceState.TRANSCRIBING:
            self._lbl_state_status.setText("Understanding...")
            self._lbl_status_pill.setText("🧠 TRANSCRIBING")
            self._lbl_status_pill.setStyleSheet("background: rgba(168, 85, 247, 0.2); border: 1px solid #A855F7; color: #A855F7;")

        elif state == VoiceState.PROCESSING:
            self._lbl_state_status.setText("Thinking...")
            self._lbl_status_pill.setText("⚙️ THINKING")
            self._lbl_status_pill.setStyleSheet("background: rgba(255, 191, 38, 0.2); border: 1px solid #FFBF26; color: #FFBF26;")

        elif state == VoiceState.SPEAKING:
            self._lbl_state_status.setText("Speaking...")
            self._lbl_status_pill.setText("🔊 SPEAKING")
            self._lbl_status_pill.setStyleSheet("background: rgba(0, 217, 255, 0.2); border: 1px solid #00D9FF; color: #00D9FF;")
            self._renderer.set_state(UltronState.SPEAKING)

        elif state == VoiceState.ERROR:
            self._lbl_state_status.setText(f"Notice: {message}")
            self._lbl_status_pill.setText("⚠️ NOTICE")
            self._lbl_status_pill.setStyleSheet("background: rgba(239, 68, 68, 0.2); border: 1px solid #EF4444; color: #EF4444;")

    def _update_ui(self) -> None:
        self._pulse_time += FRAME_MS / 1000.0
        self._mic.set_pulse(self._pulse_time)
        self._mic.set_listening(self._renderer.state_manager.is_listening())
        self._mic.set_active(self._renderer.state_manager.is_speaking())

    def _on_mic_clicked(self) -> None:
        """Manual Mic Click Trigger."""
        if voice_pipeline._running:
            voice_state_manager.transition_to(VoiceState.LISTENING, "Manual mic activation.")

    def toggle_floating_mode(self) -> None:
        """Toggles between Fullscreen and 1-inch Always-on-Top Floating Desktop Widget mode."""
        self._is_floating = not self._is_floating
        if self._is_floating:
            self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
            screen_geo = self.screen().geometry()
            widget_w, widget_h = 180, 180
            self.setGeometry(screen_geo.width() - widget_w - 30, screen_geo.height() - widget_h - 60, widget_w, widget_h)
            self._lbl_title.hide()
            self._lbl_subtitle.hide()
            self._lbl_status_pill.hide()
            self._chat_card.hide()
            self._lbl_footer.hide()
            self.show()
        else:
            self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
            self._lbl_title.show()
            self._lbl_subtitle.show()
            self._lbl_status_pill.show()
            self._chat_card.show()
            self._lbl_footer.show()
            self.showFullScreen()

    def mouseDoubleClickEvent(self, event) -> None:
        self.toggle_floating_mode()
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            voice_pipeline.stop()
            self.close()
        elif event.key() in (Qt.Key_F11, Qt.Key_Tab):
            self.toggle_floating_mode()
        elif event.key() in (Qt.Key_Return, Qt.Key_Space):
            self._on_mic_clicked()
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        voice_pipeline.stop()
        self._renderer.shutdown()
        super().closeEvent(event)
