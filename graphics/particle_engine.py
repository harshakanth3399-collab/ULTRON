"""
graphics/particle_engine.py - ULTRON Volumetric AI Core Particle Engine

REPLACED:
  - Old sun/atom shape is completely removed.
  - New volumetric AI core based on Tony Stark's J.A.R.V.I.S. consciousness matrix:
    1. Core (25%): A highly dense golden center pulsing with audio energy.
    2. Plasma Shell (45%): Turbulent spherical field warping along 3D simplex/FBM vector noise.
    3. Concentric HUD Tracks (30%): inclined ring arrays counter-rotating and rippling.

AUDIO-REACTIVITY:
  - Speech & playback audio amplitude drive the core size/glow, shell noise deformation,
    and HUD track orbital speeds.
"""
from __future__ import annotations

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


def _fibonacci_sphere(count: int, radius: float, jitter: float = 0.01) -> np.ndarray:
    """Golden ratio distribution of points on a sphere shell surface."""
    pts = np.zeros((count, 3), dtype=np.float32)
    golden = np.pi * (3.0 - np.sqrt(5.0))
    for i in range(count):
        y = 1.0 - (i / max(count - 1, 1)) * 2.0
        r = np.sqrt(max(1.0 - y * y, 0.0))
        theta = golden * i
        pts[i, 0] = np.cos(theta) * r
        pts[i, 1] = y
        pts[i, 2] = np.sin(theta) * r
    pts *= radius
    pts += np.random.normal(0.0, jitter, pts.shape).astype(np.float32)
    return pts


def _torus_ring(count: int, major_r: float, minor_r: float,
                tilt_x: float = 0.0, tilt_z: float = 0.0) -> np.ndarray:
    """Torus ring layout with orbital inclination tilt."""
    theta = np.random.uniform(0.0, 2.0 * np.pi, count).astype(np.float32)
    phi   = np.random.uniform(0.0, 2.0 * np.pi, count).astype(np.float32)

    x = (major_r + minor_r * np.cos(phi)) * np.cos(theta)
    y = (major_r + minor_r * np.cos(phi)) * np.sin(theta)
    z = minor_r * np.sin(phi)

    pts = np.stack([x, y, z], axis=1).astype(np.float32)

    if abs(tilt_x) > 0.001:
        cx, sx = np.cos(tilt_x), np.sin(tilt_x)
        y2 = pts[:, 1] * cx - pts[:, 2] * sx
        z2 = pts[:, 1] * sx + pts[:, 2] * cx
        pts[:, 1] = y2
        pts[:, 2] = z2

    if abs(tilt_z) > 0.001:
        cz, sz = np.cos(tilt_z), np.sin(tilt_z)
        x2 = pts[:, 0] * cz - pts[:, 1] * sz
        y2 = pts[:, 0] * sz + pts[:, 1] * cz
        pts[:, 0] = x2
        pts[:, 1] = y2

    return pts


def _generate_ai_core(count: int) -> np.ndarray:
    """
    Structured volumetric AI energy core layout:
      25% - Dense center core (Gaussian cluster)
      45% - Volumetric shell (Fibonacci lattice)
      30% - Counter-rotating inclined digital HUD tracks
    """
    pts = np.zeros((count, 3), dtype=np.float32)

    n_core   = int(count * 0.25)
    n_shell  = int(count * 0.45)
    n_tracks = count - n_core - n_shell

    radius = SPHERE_RADIUS

    # 1. Central dense core
    pts[:n_core] = np.random.normal(0.0, radius * 0.25, (n_core, 3)).astype(np.float32)

    # 2. Outer plasma shell surface
    pts[n_core:n_core + n_shell] = _fibonacci_sphere(n_shell, radius, jitter=0.012)

    # 3. Inclined concentric tracks
    n_per_track = n_tracks // 3
    cursor = n_core + n_shell
    for idx in range(3):
        n_this = n_per_track if idx < 2 else (count - cursor)
        maj = radius * (1.1 + idx * 0.16)
        tx = (idx * np.pi / 4.0) + 0.25
        tz = (idx * -np.pi / 6.0) - 0.12
        pts[cursor:cursor + n_this] = _torus_ring(n_this, maj, 0.004, tx, tz)
        cursor += n_this

    return pts.astype(np.float32)


class ParticleEngine:
    """Drives particle kinematics with dynamic vector fields and audio-reactivity."""

    __slots__ = (
        "count", "_base", "_positions",
        "_velocity", "_size", "_brightness", "_phase", "_rotation",
    )

    def __init__(self, count: int = PARTICLE_COUNT) -> None:
        self.count       = count
        self._base       = _generate_ai_core(count)
        self._positions  = self._base.copy()
        self._velocity   = np.zeros((count, 3), dtype=np.float32)
        self._phase      = np.random.uniform(0.0, 6.28318, count).astype(np.float32)
        self._size       = np.random.uniform(
            PARTICLE_MIN_SIZE, PARTICLE_MAX_SIZE, count
        ).astype(np.float32)
        self._brightness = np.random.uniform(0.35, 1.0, count).astype(np.float32)
        self._rotation   = 0.0

    def update(
        self,
        dt: float,
        time: float,
        state: UltronState,
        audio_level: float,
        activation: float,
    ) -> None:
        cfg = STATE_CONFIG[state.name.lower()]
        turbulence   = cfg["turbulence"]
        pulse_speed  = cfg["pulse_speed"]
        pulse_amp    = cfg["pulse_amp"]
        rotation_spd = cfg["rotation"]
        audio        = audio_level * cfg["audio_influence"]

        # Base rotation
        self._rotation += dt * (rotation_spd + audio * 0.35)

        # Partitions
        n_core   = int(self.count * 0.25)
        n_shell  = int(self.count * 0.45)
        n_tracks = self.count - n_core - n_shell

        # ── 1. Update Core (Dense Center) ─────────────────────────────────────
        # Tight breathing pulse driven by audio
        core_pulse = 1.0 + np.sin(time * pulse_speed * 1.4) * pulse_amp * 0.35 + audio * 0.15
        self._positions[:n_core] = self._base[:n_core] * core_pulse

        # ── 2. Update Shell (Plasma Filaments) ────────────────────────────────
        # Simplex noise vector displacement
        bx_shell = self._base[n_core:n_core + n_shell, 0]
        by_shell = self._base[n_core:n_core + n_shell, 1]
        bz_shell = self._base[n_core:n_core + n_shell, 2]

        cos_s = np.cos(self._rotation * 0.25)
        sin_s = np.sin(self._rotation * 0.25)
        rot_xs = bx_shell * cos_s - bz_shell * sin_s
        rot_zs = bx_shell * sin_s + bz_shell * cos_s

        noise_scale = 1.5 + turbulence * 0.35 + audio * 0.75
        nx = rot_xs * noise_scale + time * (0.24 + audio * 0.3)
        ny = by_shell * noise_scale + time * (0.20 + audio * 0.3)
        nz = rot_zs * noise_scale + time * (0.16 + audio * 0.3)

        n1 = fbm3(nx, ny, nz, octaves=2)
        n2 = fbm3(nx + 10.0, ny + 5.0, nz + 3.0, octaves=2)
        n3 = simplex3(nx * 1.9 + 35.0, ny * 1.9, nz * 1.9 + time * (0.45 + audio))

        disp = np.stack((n1, n2, n3), axis=1).astype(np.float32)
        disp *= 0.04 * (turbulence + audio * 1.4) * SPHERE_RADIUS

        shell_pulse = 1.0 + np.sin(time * pulse_speed + self._phase[n_core:n_core + n_shell]) * pulse_amp + audio * 0.22
        self._positions[n_core:n_core + n_shell] = (
            self._base[n_core:n_core + n_shell] * shell_pulse[:, np.newaxis] + disp
        )

        # ── 3. Update concentric tracks (Orbital Bands) ────────────────────────
        n_per_track = n_tracks // 3
        cursor = n_core + n_shell
        for idx in range(3):
            n_this = n_per_track if idx < 2 else (self.count - cursor)
            # Counter-rotate adjacent tracks
            dir_mult = 1.0 if idx % 2 == 0 else -1.25
            angle = self._rotation * dir_mult + (idx * 0.45)

            cos_t = np.cos(angle)
            sin_t = np.sin(angle)

            bx_t = self._base[cursor:cursor + n_this, 0]
            by_t = self._base[cursor:cursor + n_this, 1]
            bz_t = self._base[cursor:cursor + n_this, 2]

            rx = bx_t * cos_t - bz_t * sin_t
            rz = bx_t * sin_t + bz_t * cos_t

            # Synaptic wave ripples
            ripple = 1.0 + np.sin(time * 3.5 + float(idx) + self._phase[cursor:cursor + n_this]) * 0.008 * (1.0 + audio * 2.2)

            self._positions[cursor:cursor + n_this] = np.stack((rx, by_t, rz), axis=1).astype(np.float32) * ripple[:, np.newaxis]
            cursor += n_this

        # ── Brightness & Sizing ────────────────────────────────────────────────
        glow = cfg["glow"] * max(activation, 0.5)

        # Core is extremely bright
        self._brightness[:n_core] = np.clip(0.85 + audio * 0.15 + np.abs(n1[:n_core]) * 0.08, 0.6, 1.0)
        # Shell matches voice energy
        self._brightness[n_core:n_core + n_shell] = np.clip(
            0.42 + 0.45 * glow + 0.28 * np.abs(n1[n_core:n_core + n_shell]) + audio * 0.75,
            0.18, 1.0
        )
        # Tracks glow subtly
        self._brightness[n_core + n_shell:] = np.clip(
            0.32 + 0.38 * glow + audio * 0.45,
            0.12, 0.95
        )

        # Sizes: Core small/dense, Shell expansive/reactive, Tracks fine/digital
        self._size[:n_core] = np.clip(self._size[:n_core] * 0.75, PARTICLE_MIN_SIZE, PARTICLE_MAX_SIZE * 0.65)
        self._size[n_core:n_core + n_shell] = np.clip(
            self._size[n_core:n_core + n_shell] * (1.0 + audio * 0.9),
            PARTICLE_MIN_SIZE, PARTICLE_MAX_SIZE * 1.8
        )
        self._size[n_core + n_shell:] = np.clip(
            self._size[n_core + n_shell:] * 0.55,
            PARTICLE_MIN_SIZE * 0.5, PARTICLE_MAX_SIZE * 0.75
        )

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
