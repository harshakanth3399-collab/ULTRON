"""
graphics/particle_engine.py - ULTRON Voice-Reactive Turbulent Particle Core

ARCHITECTURE:
  - 25% Dense golden nucleus — breathes with audio energy
  - 45% Plasma shell — turbulent fluid-like FBM vector displacement
  - 30% Orbital HUD tracks — counter-rotating inclined rings

VOICE REACTIVITY:
  - audio_level 0..1 drives: orbit speed, particle size, brightness,
    plasma eruption radius, nucleus pulse amplitude
  - On voice spike: shockwave expansion ripples outward from center
  - SPEAKING state: rapid plasma eruption, larger points, bright glow
  - LISTENING state: particles lean toward mic direction, pulsing rings
  - IDLE state: slow breathing rotation with gentle turbulence
"""
from __future__ import annotations

import math
import numpy as np

from graphics.constants import (
    PARTICLE_COUNT,
    PARTICLE_MAX_SIZE,
    PARTICLE_MIN_SIZE,
    SPHERE_RADIUS,
    STATE_CONFIG,
)
from graphics.noise import fbm3, simplex3
from graphics.state import UltronState


# ── Geometry helpers ──────────────────────────────────────────────────────────

def _fibonacci_sphere(count: int, radius: float, jitter: float = 0.012) -> np.ndarray:
    """Golden ratio distribution of points on a sphere shell — even coverage."""
    golden = math.pi * (3.0 - math.sqrt(5.0))
    indices = np.arange(count, dtype=np.float32)
    y   = 1.0 - (indices / max(count - 1, 1)) * 2.0
    r   = np.sqrt(np.clip(1.0 - y * y, 0.0, 1.0))
    theta = golden * indices
    x = np.cos(theta) * r
    z = np.sin(theta) * r
    pts = np.stack([x, y, z], axis=1).astype(np.float32) * radius
    pts += np.random.normal(0.0, jitter, pts.shape).astype(np.float32)
    return pts


def _torus_ring(count: int, major_r: float, minor_r: float,
                tilt_x: float = 0.0, tilt_z: float = 0.0) -> np.ndarray:
    """Torus with orbital inclination tilt for holographic HUD rings."""
    theta = np.random.uniform(0.0, 2.0 * np.pi, count).astype(np.float32)
    phi   = np.random.uniform(0.0, 2.0 * np.pi, count).astype(np.float32)
    x = (major_r + minor_r * np.cos(phi)) * np.cos(theta)
    y = (major_r + minor_r * np.cos(phi)) * np.sin(theta)
    z = minor_r * np.sin(phi)
    pts = np.stack([x, y, z], axis=1).astype(np.float32)
    if abs(tilt_x) > 0.001:
        cx, sx = math.cos(tilt_x), math.sin(tilt_x)
        y2 = pts[:, 1] * cx - pts[:, 2] * sx
        z2 = pts[:, 1] * sx + pts[:, 2] * cx
        pts[:, 1] = y2
        pts[:, 2] = z2
    if abs(tilt_z) > 0.001:
        cz, sz = math.cos(tilt_z), math.sin(tilt_z)
        x2 = pts[:, 0] * cz - pts[:, 1] * sz
        y2 = pts[:, 0] * sz + pts[:, 1] * cz
        pts[:, 0] = x2
        pts[:, 1] = y2
    return pts


def _generate_ai_core(count: int) -> np.ndarray:
    """
    MCU J.A.R.V.I.S. Neural Matrix Core:
      Dense glowing spherical shell matrix matching the mobile 3D WebGL engine.
    """
    u = np.random.uniform(0.0, 1.0, count).astype(np.float32)
    v = np.random.uniform(0.0, 1.0, count).astype(np.float32)
    theta = u * (2.0 * math.pi)
    phi = np.arccos(2.0 * v - 1.0)
    r = 0.88 + np.random.uniform(0.0, 0.46, count).astype(np.float32)

    x = r * np.sin(phi) * np.cos(theta)
    y = r * np.sin(phi) * np.sin(theta)
    z = r * np.cos(phi)
    return np.stack([x, y, z], axis=1).astype(np.float32)


# ── Particle Engine ────────────────────────────────────────────────────────────

class ParticleEngine:
    """
    Real-time MCU J.A.R.V.I.S. neural matrix particle engine with voice reactivity.
    Matches the mobile phone undulating wave visualizer 1:1.
    """

    __slots__ = (
        "count", "_base", "_positions",
        "_velocity", "_size", "_brightness", "_phase",
        "_rotation", "_shockwave", "_prev_audio",
    )

    def __init__(self, count: int = PARTICLE_COUNT) -> None:
        self.count        = count
        self._base        = _generate_ai_core(count)
        self._positions   = self._base.copy()
        self._velocity    = np.zeros((count, 3), dtype=np.float32)
        self._phase       = np.random.uniform(0.0, 6.28318, count).astype(np.float32)
        self._size        = np.random.uniform(PARTICLE_MIN_SIZE, PARTICLE_MAX_SIZE, count).astype(np.float32)
        self._brightness  = np.random.uniform(0.5, 1.0, count).astype(np.float32)
        self._rotation    = 0.0
        self._shockwave   = 0.0   # 0..1 shockwave expansion state
        self._prev_audio  = 0.0

    # ── Per-frame update ──────────────────────────────────────────────────────

    def update(
        self,
        dt: float,
        time: float,
        state: UltronState,
        audio_level: float,
        activation: float,
    ) -> None:
        cfg          = STATE_CONFIG.get(state.name.lower(), STATE_CONFIG["idle"])
        audio        = audio_level * cfg["audio_influence"]

        # ── Shockwave on audio spike ──────────────────────────────────────────
        spike = audio_level - self._prev_audio
        if spike > 0.12:                  # voice onset detected
            self._shockwave = 1.0         # trigger expansion
        self._shockwave = max(0.0, self._shockwave - dt * 2.2)   # decay
        self._prev_audio = audio_level

        bx = self._base[:, 0]
        by = self._base[:, 1]
        bz = self._base[:, 2]

        # ── Fluid undulating wave ripple across particle grid (matches mobile 1:1) ──
        wave = (
            np.sin(time * 2.0 + bx * 3.0 + bz * 2.5) * 0.07
            + np.cos(time * 1.4 + by * 3.5) * 0.05
        )
        # Voice reactivity modulates wave
        wave_amp = 1.0 + audio * 2.5 + self._shockwave * 1.5
        wave = wave * wave_amp

        self._positions[:, 0] = bx * (1.0 + wave * 0.35)
        self._positions[:, 1] = by + wave
        self._positions[:, 2] = bz * (1.0 + wave * 0.35)

        # ── Brightness & Size: glowing voice reactivity ───────────────────────
        glow = cfg["glow"] * max(activation, 0.4)
        self._brightness = np.clip(
            0.55 + 0.35 * glow + audio * 0.8 + self._shockwave * 0.4,
            0.3, 1.0
        ).astype(np.float32)

        voice_scale = 1.0 + audio * 1.5 + self._shockwave * 0.5
        self._size = np.clip(
            (PARTICLE_MIN_SIZE + (PARTICLE_MAX_SIZE - PARTICLE_MIN_SIZE) * (0.4 + audio * 0.6)) * voice_scale,
            PARTICLE_MIN_SIZE, PARTICLE_MAX_SIZE * 1.8
        ).astype(np.float32)

    def model_matrix(self, time: float, state: UltronState, audio_level: float) -> np.ndarray:
        """Computes the 4x4 model matrix for full 3D sphere revolution and tilt (hardware accelerated)."""
        speed = 1.8 if state == UltronState.SPEAKING else (1.25 if state == UltronState.LISTENING else 0.75)
        # Continuous visible revolution matching mobile phone
        rot_y = time * 0.38 * speed + audio_level * 0.5
        rot_x = math.sin(time * 0.22) * 0.18
        rot_z = math.cos(time * 0.18) * 0.15

        pulse_scale = (
            1.0
            + math.sin(time * 3.0) * (0.09 if state == UltronState.SPEAKING else 0.035)
            + audio_level * 0.20
            + self._shockwave * 0.15
        )

        cy, sy = math.cos(rot_y), math.sin(rot_y)
        cx, sx = math.cos(rot_x), math.sin(rot_x)
        cz, sz = math.cos(rot_z), math.sin(rot_z)

        Ry = np.array([[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]], dtype=np.float32)
        Rx = np.array([[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]], dtype=np.float32)
        Rz = np.array([[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]], dtype=np.float32)
        R = (Ry @ Rx @ Rz) * pulse_scale

        M = np.eye(4, dtype=np.float32)
        M[:3, :3] = R
        return M

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def positions(self) -> np.ndarray:
        return self._positions

    @property
    def sizes(self) -> np.ndarray:
        return self._size

    @property
    def brightness(self) -> np.ndarray:
        return self._brightness

    def interleaved_buffer(self) -> np.ndarray:
        """Pack pos(3) + size(1) + brightness(1) per particle for GPU upload."""
        out = np.empty((self.count, 5), dtype=np.float32)
        out[:, :3] = self._positions
        out[:, 3]  = self._size
        out[:, 4]  = self._brightness
        return out
