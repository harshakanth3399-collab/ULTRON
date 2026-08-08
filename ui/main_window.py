"""
ui/main_window.py — ULTRON Cinematic Interface.

Design language from reference images:
  - Pure matte black fullscreen background
  - Particle visualizer as the entire canvas (no frame, no border)
  - Minimal transparent overlay: only ULTRON wordmark top-left,
    status badge top-right, conversation bottom-left, mic button bottom-right
  - All overlay elements are glass-style: near-transparent, zero border boxes
  - Real voice states reflected in color and text — no fake animations
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt, QTimer, Slot
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from graphics.constants import FRAME_MS
from graphics.renderer import UltronRenderer
from graphics.state import UltronState
from core.voice_state import VoiceState, voice_state_manager
from core.voice_pipeline import voice_pipeline


# ─── Inline Mic Button ────────────────────────────────────────────────────────

class _MicButton(QPushButton):
    """Minimal circular microphone button — red when listening, dim when idle."""

    _SIZE = 56

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(self._SIZE, self._SIZE)
        self.setCursor(Qt.PointingHandCursor)
        self._listening = False
        self._pulse = 0.0
        self._apply_style()

    def set_listening(self, v: bool) -> None:
        if self._listening != v:
            self._listening = v
            self._apply_style()

    def set_pulse(self, t: float) -> None:
        self._pulse = t
        self.update()

    def _apply_style(self) -> None:
        if self._listening:
            self.setStyleSheet("""
                QPushButton {
                    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                        fx:0.5, fy:0.5, stop:0 #FF4422, stop:1 #CC2200);
                    border: 2px solid rgba(255, 80, 40, 0.9);
                    border-radius: 28px;
                }
                QPushButton:hover {
                    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                        fx:0.5, fy:0.5, stop:0 #FF6644, stop:1 #EE3300);
                    border: 2px solid #FF6644;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                        fx:0.5, fy:0.5, stop:0 #441111, stop:1 #220808);
                    border: 2px solid rgba(180, 40, 20, 0.5);
                    border-radius: 28px;
                }
                QPushButton:hover {
                    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                        fx:0.5, fy:0.5, stop:0 #882222, stop:1 #550E0E);
                    border: 2px solid rgba(220, 60, 30, 0.8);
                }
            """)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Mic icon
        if self._listening:
            col = QColor(255, 255, 255, 230)
        else:
            col = QColor(200, 80, 60, 180)

        painter.setPen(QPen(col, 2))
        cx, cy = self._SIZE // 2, self._SIZE // 2

        # mic body
        painter.drawRoundedRect(cx - 5, cy - 12, 10, 16, 5, 5)
        # stand arc
        painter.drawArc(cx - 8, cy - 4, 16, 14, 0, -180 * 16)
        # stem
        painter.drawLine(cx, cy + 10, cx, cy + 15)
        # base
        painter.drawLine(cx - 5, cy + 15, cx + 5, cy + 15)


# ─── Main Window ─────────────────────────────────────────────────────────────

class UltronWindow(QMainWindow):
    """
    ULTRON cinematic fullscreen window.

    Layout (fullscreen, all transparent overlay on top of particle renderer):
      ┌─ wordmark (top-left) ──────────── status badge (top-right) ─┐
      │                                                               │
      │              [PARTICLE RENDERER — full canvas]               │
      │                                                               │
      │   conversation (bottom-left)         [MIC BUTTON] (bottom-right) │
      └───────────────── state label (bottom-center) ────────────────┘
    """

    _PAD = 32
    _BADGE_H = 36

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ULTRON")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setStyleSheet("background: #000000;")

        # ── Central container ─────────────────────────────────────
        self._root = QWidget(self)
        self.setCentralWidget(self._root)
        self._root.setStyleSheet("background: #000000;")

        # ── Particle renderer (full canvas background) ────────────
        self._renderer = UltronRenderer(self._root)
        self._renderer.set_speaking_callback(self._is_speaking_cb)

        # ── Transparent overlay (all UI floats on top) ────────────
        self._overlay = QWidget(self._root)
        self._overlay.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self._overlay.setStyleSheet("background: transparent;")

        # ── Build overlay elements ────────────────────────────────
        self._build_wordmark()
        self._build_status_badge()
        self._build_state_label()
        self._build_conversation()
        self._build_mic_button()

        # ── Wire voice state machine ──────────────────────────────
        voice_state_manager.add_listener(self._on_voice_state)
        voice_pipeline.set_chat_callback(self._on_chat)

        # ── Pulse timer ───────────────────────────────────────────
        self._pulse_t = 0.0
        self._ui_timer = QTimer(self)
        self._ui_timer.timeout.connect(self._tick)
        self._ui_timer.start(FRAME_MS)

        self.showFullScreen()

        # ── Start voice after window is shown ─────────────────────
        QTimer.singleShot(800, voice_pipeline.start)

    # ── Widget builders ───────────────────────────────────────────────────────

    def _build_wordmark(self) -> None:
        """Top-left: ULTRON wordmark + tagline."""
        self._wm = QLabel(self._overlay)
        self._wm.setText(
            '<span style="font-size:26px; font-weight:900; '
            'color:#E8600A; letter-spacing:6px;">ULTRON</span>'
            '<br>'
            '<span style="font-size:9px; font-weight:600; '
            'color:rgba(200,100,10,0.5); letter-spacing:4px;">PERSONAL AI</span>'
        )
        self._wm.setStyleSheet("background: transparent;")

    def _build_status_badge(self) -> None:
        """Top-right: compact amber status badge."""
        self._badge = QLabel("● ONLINE", self._overlay)
        self._badge.setStyleSheet("""
            background: rgba(232, 96, 10, 0.12);
            border: 1px solid rgba(232, 96, 10, 0.45);
            border-radius: 14px;
            color: rgba(232, 96, 10, 0.9);
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 2px;
            padding: 4px 14px;
        """)
        self._badge.setAttribute(Qt.WA_TranslucentBackground)

    def _build_state_label(self) -> None:
        """Bottom-center: current pipeline state text."""
        self._state_lbl = QLabel("Say  'Hey Ultron'  to begin", self._overlay)
        self._state_lbl.setAlignment(Qt.AlignCenter)
        self._state_lbl.setStyleSheet("""
            color: rgba(232, 96, 10, 0.65);
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 3px;
            background: transparent;
        """)

    def _build_conversation(self) -> None:
        """Bottom-left: last USER and ULTRON utterances."""
        self._conv = QLabel("", self._overlay)
        self._conv.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        self._conv.setWordWrap(True)
        self._conv.setStyleSheet("""
            color: rgba(255, 255, 255, 0.0);
            font-size: 13px;
            font-weight: 500;
            background: transparent;
            letter-spacing: 0.5px;
        """)
        self._last_user = ""
        self._last_ultron = ""

    def _build_mic_button(self) -> None:
        """Bottom-right: red mic button."""
        self._mic = _MicButton(self._overlay)
        self._mic.clicked.connect(self._on_mic_clicked)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(255, 60, 20, 160))
        shadow.setOffset(0, 0)
        self._mic.setGraphicsEffect(shadow)

    # ── Layout ────────────────────────────────────────────────────────────────

    def resizeEvent(self, event) -> None:
        self._renderer.setGeometry(self._root.rect())
        self._overlay.setGeometry(self._root.rect())
        self._reposition()
        super().resizeEvent(event)

    def _reposition(self) -> None:
        W, H = self._overlay.width(), self._overlay.height()
        P = self._PAD

        # Wordmark — top-left
        self._wm.adjustSize()
        self._wm.move(P, P)

        # Status badge — top-right
        self._badge.adjustSize()
        bw = self._badge.width()
        self._badge.move(W - bw - P, P + 4)

        # Mic button — bottom-right
        mb = self._mic.width()
        self._mic.move(W - mb - P, H - mb - P)

        # State label — bottom-center
        self._state_lbl.adjustSize()
        slw = self._state_lbl.width()
        self._state_lbl.move((W - slw) // 2, H - 60)

        # Conversation — bottom-left
        self._conv.setFixedWidth(min(480, W // 2))
        self._conv.adjustSize()
        self._conv.move(P, H - self._conv.height() - P - 10)

    # ── Voice state callbacks ─────────────────────────────────────────────────

    def _on_voice_state(self, state: VoiceState, message: str) -> None:
        QTimer.singleShot(0, lambda: self._apply_state(state, message))

    def _apply_state(self, state: VoiceState, message: str) -> None:
        AMBER = "rgba(232, 96, 10, 0.9)"
        DIM   = "rgba(232, 96, 10, 0.5)"
        RED   = "rgba(255, 60, 30, 0.9)"
        CYAN  = "rgba(0, 210, 255, 0.9)"
        WHITE = "rgba(255, 255, 255, 0.85)"
        GOLD  = "rgba(255, 200, 50, 0.9)"

        if state == VoiceState.IDLE:
            self._set_badge("● ONLINE", AMBER)
            self._set_state("Say  'Hey Ultron'  to begin", DIM)
            self._renderer.set_state(UltronState.IDLE)
            self._mic.set_listening(False)

        elif state == VoiceState.WAKE_DETECTED:
            self._set_badge("⚡ WAKE", GOLD)
            self._set_state("Wake detected...", GOLD)

        elif state == VoiceState.GREETING:
            self._set_badge("◎ GREETING", AMBER)
            self._set_state("", AMBER)
            self._renderer.set_state(UltronState.SPEAKING)

        elif state in (VoiceState.LISTENING, VoiceState.RECORDING):
            self._set_badge("● LISTENING", RED)
            self._set_state("Listening...", RED)
            self._renderer.set_state(UltronState.LISTENING)
            self._mic.set_listening(True)

        elif state == VoiceState.TRANSCRIBING:
            self._set_badge("◌ UNDERSTANDING", WHITE)
            self._set_state("Understanding...", WHITE)
            self._mic.set_listening(False)

        elif state == VoiceState.PROCESSING:
            self._set_badge("◌ THINKING", GOLD)
            self._set_state("Thinking...", GOLD)

        elif state == VoiceState.SPEAKING:
            self._set_badge("◎ SPEAKING", CYAN)
            self._set_state("", CYAN)
            self._renderer.set_state(UltronState.SPEAKING)
            self._mic.set_listening(False)

        elif state == VoiceState.ERROR:
            self._set_badge("⚠ ERROR", RED)
            self._set_state(message[:60] if message else "Error — recovering...", RED)
            self._renderer.set_state(UltronState.IDLE)

        self._reposition()

    def _set_badge(self, text: str, color: str) -> None:
        self._badge.setText(text)
        self._badge.setStyleSheet(f"""
            background: rgba(232, 96, 10, 0.10);
            border: 1px solid {color.replace('0.9', '0.4').replace('0.85', '0.4')};
            border-radius: 14px;
            color: {color};
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 2px;
            padding: 4px 14px;
        """)

    def _set_state(self, text: str, color: str) -> None:
        self._state_lbl.setText(text)
        self._state_lbl.setStyleSheet(f"""
            color: {color};
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 3px;
            background: transparent;
        """)

    # ── Chat callback ─────────────────────────────────────────────────────────

    def _on_chat(self, speaker: str, text: str) -> None:
        QTimer.singleShot(0, lambda: self._update_chat(speaker, text))

    def _update_chat(self, speaker: str, text: str) -> None:
        if speaker == "USER":
            self._last_user = text
        elif speaker == "ULTRON":
            self._last_ultron = text

        html = ""
        if self._last_user:
            u = self._last_user[:120]
            html += f'<span style="color:rgba(200,200,200,0.7); font-size:12px;">YOU&nbsp;&nbsp;</span>'
            html += f'<span style="color:rgba(240,240,240,0.9); font-size:13px;">{u}</span><br>'
        if self._last_ultron:
            r = self._last_ultron[:140]
            html += f'<span style="color:rgba(232,96,10,0.7); font-size:12px;">ULTRON&nbsp;</span>'
            html += f'<span style="color:rgba(255,160,60,0.95); font-size:13px;">{r}</span>'

        self._conv.setText(html)
        self._conv.setTextFormat(Qt.RichText)
        self._conv.setStyleSheet("background: transparent;")
        self._reposition()

    # ── Tick ──────────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        self._pulse_t += FRAME_MS / 1000.0
        self._mic.set_pulse(self._pulse_t)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _is_speaking_cb(self) -> bool:
        try:
            from speech_engine import speaking
            return speaking()
        except Exception:
            return False

    # ── Mic button ────────────────────────────────────────────────────────────

    def _on_mic_clicked(self) -> None:
        """Manual push-to-talk: sets pipeline session active."""
        if voice_pipeline._running:
            from core.voice_state import VoiceState
            voice_state_manager.transition_to(VoiceState.LISTENING, "Manual activation")

    # ── Keys ──────────────────────────────────────────────────────────────────

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            voice_pipeline.stop()
            self.close()
        elif event.key() in (Qt.Key_Return, Qt.Key_Space):
            self._on_mic_clicked()
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        voice_pipeline.stop()
        try:
            self._renderer.shutdown()
        except Exception:
            pass
        super().closeEvent(event)
