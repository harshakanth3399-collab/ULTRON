"""
ui/main_window.py - ULTRON Cinematic Interface

Design from reference images:
  - Pure matte black fullscreen (no frames, no borders)
  - Particle renderer occupies the entire canvas
  - Minimal transparent amber/gold overlay:
      top-left:     ULTRON wordmark
      top-right:    live status badge
      bottom-center: state text (LISTENING... THINKING... etc.)
      bottom-left:  clean conversation (YOU / ULTRON lines)
      bottom-right: red mic button
  - Zero debug info shown to user
  - All states connected to real voice state machine
"""
from __future__ import annotations

import math

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QLabel,
    QMainWindow,
    QPushButton,
    QWidget,
)

from graphics.constants import FRAME_MS
from graphics.renderer import UltronRenderer
from graphics.state import UltronState
from core.voice_state import VoiceState, voice_state_manager
from core.voice_pipeline import voice_pipeline


# ── Mic Button ────────────────────────────────────────────────────────────────

class _MicButton(QPushButton):
    SIZE = 60

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.PointingHandCursor)
        self._active   = False
        self._pulse_t  = 0.0
        self._apply_style()

    def set_active(self, v: bool) -> None:
        if self._active != v:
            self._active = v
            self._apply_style()

    def set_pulse(self, t: float) -> None:
        self._pulse_t = t
        if self._active:
            self.update()

    def _apply_style(self) -> None:
        if self._active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qradialgradient(cx:0.5,cy:0.5,radius:0.5,
                        fx:0.5,fy:0.5,stop:0 #FF3311,stop:1 #AA1100);
                    border: 2px solid rgba(255,60,20,0.95);
                    border-radius: {self.SIZE//2}px;
                }}
                QPushButton:hover {{
                    background: qradialgradient(cx:0.5,cy:0.5,radius:0.5,
                        fx:0.5,fy:0.5,stop:0 #FF5533,stop:1 #CC2200);
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qradialgradient(cx:0.5,cy:0.5,radius:0.5,
                        fx:0.5,fy:0.5,stop:0 #3A0E00,stop:1 #1A0500);
                    border: 1px solid rgba(180,40,15,0.55);
                    border-radius: {self.SIZE//2}px;
                }}
                QPushButton:hover {{
                    background: qradialgradient(cx:0.5,cy:0.5,radius:0.5,
                        fx:0.5,fy:0.5,stop:0 #6A1A00,stop:1 #3A0800);
                    border: 1px solid rgba(220,60,20,0.8);
                }}
            """)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Pulsing ring when active
        if self._active:
            pulse = 0.5 + 0.5 * math.sin(self._pulse_t * 5.0)
            alpha = int(60 + 120 * pulse)
            radius = self.SIZE // 2 + int(6 * pulse)
            painter.setPen(QPen(QColor(255, 60, 20, alpha), 2))
            painter.drawEllipse(
                self.SIZE // 2 - radius,
                self.SIZE // 2 - radius,
                radius * 2, radius * 2
            )

        # Mic icon
        col = QColor(255, 255, 255, 210) if self._active else QColor(180, 60, 40, 160)
        painter.setPen(QPen(col, 2))
        cx, cy = self.SIZE // 2, self.SIZE // 2
        # body
        painter.drawRoundedRect(cx - 5, cy - 11, 10, 15, 5, 5)
        # arc
        painter.drawArc(cx - 8, cy - 2, 16, 14, 0, -180 * 16)
        # stem
        painter.drawLine(cx, cy + 12, cx, cy + 16)
        # base
        painter.drawLine(cx - 5, cy + 16, cx + 5, cy + 16)


# ── Main Window ──────────────────────────────────────────────────────────────

class UltronWindow(QMainWindow):
    PAD = 36

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ULTRON")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setStyleSheet("background:#000000;")

        self._root = QWidget(self)
        self.setCentralWidget(self._root)
        self._root.setStyleSheet("background:#000000;")

        # ── Particle renderer — full canvas ───────────────────────────────
        self._renderer = UltronRenderer(self._root)
        self._renderer.set_speaking_callback(self._is_speaking)

        # ── Transparent overlay (child of renderer to guarantee 60 FPS repaints) ──
        self._ov = QWidget(self._renderer)
        self._ov.setStyleSheet("background:transparent;")


        # ── Wordmark ──────────────────────────────────────────────────────
        self._wm = QLabel(self._ov)
        self._wm.setText(
            '<span style="font-size:28px;font-weight:900;color:#E8630A;'
            'letter-spacing:7px;">ULTRON</span>'
            '<br>'
            '<span style="font-size:9px;font-weight:700;'
            'color:rgba(232,99,10,0.45);letter-spacing:5px;">PERSONAL AI</span>'
        )
        self._wm.setStyleSheet("background:transparent;")

        # ── Status badge ──────────────────────────────────────────────────
        self._badge = QLabel("● ONLINE", self._ov)
        self._badge.setStyleSheet(self._badge_style("rgba(232,99,10,0.9)"))

        # ── Cancel / Exit Button ─────────────────────────────────────────
        self._close_btn = QPushButton("✕ EXIT", self._ov)
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(220, 30, 20, 0.2);
                border: 1px solid rgba(255, 60, 40, 0.6);
                border-radius: 12px;
                color: rgba(255, 120, 100, 0.95);
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 2px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background: rgba(255, 40, 30, 0.4);
                border: 1px solid rgba(255, 80, 60, 0.9);
                color: #FFFFFF;
            }
        """)
        self._close_btn.clicked.connect(self.clean_shutdown)

        # ── State label ───────────────────────────────────────────────────

        self._state = QLabel("Say  'Hey Ultron'  to begin", self._ov)
        self._state.setAlignment(Qt.AlignCenter)
        self._state.setStyleSheet(
            "color:rgba(232,99,10,0.5);font-size:13px;"
            "font-weight:700;letter-spacing:4px;background:transparent;"
        )

        # ── Conversation labels ───────────────────────────────────────────
        self._conv_you = QLabel("", self._ov)
        self._conv_you.setWordWrap(True)
        self._conv_you.setStyleSheet(
            "color:rgba(210,210,210,0.75);font-size:13px;"
            "font-weight:500;background:transparent;letter-spacing:0.3px;"
        )
        self._conv_ai = QLabel("", self._ov)
        self._conv_ai.setWordWrap(True)
        self._conv_ai.setStyleSheet(
            "color:rgba(255,160,55,0.95);font-size:13px;"
            "font-weight:600;background:transparent;letter-spacing:0.3px;"
        )

        # ── Mic button ────────────────────────────────────────────────────
        self._mic = _MicButton(self._ov)
        self._mic.clicked.connect(self._on_mic)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(255, 60, 20, 140))
        shadow.setOffset(0, 0)
        self._mic.setGraphicsEffect(shadow)

        print("[BOOT] renderer created", flush=True)
        # ── Wire state machine ────────────────────────────────────────────
        voice_state_manager.add_listener(self._on_voice_state)
        voice_pipeline.set_chat_callback(self._on_chat)

        # ── Tick timer ────────────────────────────────────────────────────
        self._pulse_t = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(FRAME_MS)

        # ── Heartbeat timer (silent background health check) ─────────────
        self._heartbeat_count = 0
        self._heartbeat = QTimer(self)
        self._heartbeat.timeout.connect(self._on_heartbeat)
        self._heartbeat.start(30_000)  # Every 30s, silent

        print("[BOOT] renderer initialized", flush=True)
        # NOTE: showFullScreen() is called by app.py AFTER __init__ returns.
        # Do NOT call it here — doing so before app.exec() can cause Qt to
        # collapse the window and immediately fire lastWindowClosed -> quit.

    def _on_heartbeat(self) -> None:
        self._heartbeat_count += 1
        # Only log every 60th beat (~30 min) to avoid console flood
        if self._heartbeat_count % 60 == 1:
            print(f"[HEALTH] ULTRON alive — heartbeat #{self._heartbeat_count}", flush=True)

    def _start_pipeline(self) -> None:
        print("[BOOT] QTimer trigger: starting voice pipeline", flush=True)
        voice_pipeline.start()

    # ── Layout ────────────────────────────────────────────────────────────────

    def resizeEvent(self, event) -> None:
        self._renderer.setGeometry(self._root.rect())
        self._ov.setGeometry(self._root.rect())
        self._layout_widgets()
        super().resizeEvent(event)

    def _layout_widgets(self) -> None:
        W, H = self._ov.width(), self._ov.height()
        P = self.PAD

        # Wordmark — top-left
        self._wm.adjustSize()
        self._wm.move(P, P)

        # Exit button & Badge — top-right
        self._close_btn.adjustSize()
        self._badge.adjustSize()
        self._close_btn.move(W - self._close_btn.width() - P, P + 6)
        self._badge.move(W - self._close_btn.width() - self._badge.width() - P - 10, P + 6)

        # Mic button — bottom-right
        mb = self._mic.SIZE
        self._mic.move(W - mb - P, H - mb - P)

        # State label — bottom-center
        self._state.adjustSize()
        self._state.move((W - self._state.width()) // 2, H - 65)

        # Conversation — bottom-left (stacked)
        max_w = min(500, W // 2 - P)
        self._conv_you.setFixedWidth(max_w)
        self._conv_you.adjustSize()
        self._conv_ai.setFixedWidth(max_w)
        self._conv_ai.adjustSize()
        conv_h = self._conv_you.height() + self._conv_ai.height() + 6
        self._conv_you.move(P, H - conv_h - P - 8)
        self._conv_ai.move(P, H - self._conv_ai.height() - P - 8)

    # ── Clean Shutdown ────────────────────────────────────────────────────────

    def clean_shutdown(self) -> None:
        print("[SHUTDOWN] Terminating ULTRON cleanly...", flush=True)
        try:
            from core.voice_pipeline import voice_pipeline
            voice_pipeline.stop()
        except Exception:
            pass
        try:
            from speech_engine import stop as stop_tts
            stop_tts()
        except Exception:
            pass
        try:
            self._timer.stop()
            self._heartbeat.stop()
            self._renderer.shutdown()
        except Exception:
            pass
        try:
            from PySide6.QtWidgets import QApplication
            QApplication.quit()
        except Exception:
            pass
        import os
        os._exit(0)

    # ── Mic button handler ────────────────────────────────────────────────────

    def _on_mic(self) -> None:
        try:
            from speech_engine import stop as stop_tts
            stop_tts()
        except Exception:
            pass
        if voice_pipeline._running:
            voice_state_manager.transition_to(VoiceState.LISTENING, "Manual activation")

    # ── Keys & Close ──────────────────────────────────────────────────────────

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.clean_shutdown()
        elif event.key() in (Qt.Key_Return, Qt.Key_Space):
            self._on_mic()
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        self.clean_shutdown()
        super().closeEvent(event)

