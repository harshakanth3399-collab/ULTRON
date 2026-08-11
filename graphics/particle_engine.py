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
    Structured volumetric AI energy core:
      25% — Dense golden nucleus (Gaussian cluster)
      45% — Turbulent plasma shell (Fibonacci sphere)
      30% — Counter-rotating inclined HUD orbital tracks (3 torus rings)
    """
    pts = np.zeros((count, 3), dtype=np.float32)
    n_core   = int(count * 0.25)
    n_shell  = int(count * 0.45)
    n_tracks = count - n_core - n_shell
    r = SPHERE_RADIUS

    # 1. Nucleus: tight Gaussian cluster
    pts[:n_core] = np.random.normal(0.0, r * 0.18, (n_core, 3)).astype(np.float32)

    # 2. Plasma shell
    pts[n_core:n_core + n_shell] = _fibonacci_sphere(n_shell, r, jitter=0.014)

    # 3. Three inclined orbital rings
    n_per = n_tracks // 3
    cursor = n_core + n_shell
    for i in range(3):
        n_this = n_per if i < 2 else (count - cursor)
        maj = r * (1.12 + i * 0.18)
        tx  = (i * math.pi / 4.0) + 0.3
        tz  = (i * -math.pi / 6.0) - 0.15
        pts[cursor:cursor + n_this] = _torus_ring(n_this, maj, 0.006, tx, tz)
        cursor += n_this

    return pts.astype(np.float32)


# ── Particle Engine ────────────────────────────────────────────────────────────

class ParticleEngine:
    """
    Real-time turbulent particle system with full voice reactivity.

    Every frame:
      1. FBM vector-noise displaces the plasma shell — fluid turbulent motion
      2. audio_level (0..1) from mic/TTS drives nucleus pulse, ring speed, glow
      3. Shockwave radius expands on voice spikes, particles scatter outward
      4. SPEAKING: rapid eruption, max glow, large point sizes
      5. LISTENING: particles lean and pulse with each syllable
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
        self._brightness  = np.random.uniform(0.4, 1.0, count).astype(np.float32)
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
        cfg          = STATE_CONFIG[state.name.lower()]
        turbulence   = cfg["turbulence"]
        pulse_speed  = cfg["pulse_speed"]
        pulse_amp    = cfg["pulse_amp"]
        rotation_spd = cfg["rotation"]
        audio        = audio_level * cfg["audio_influence"]

        # ── Shockwave on audio spike ──────────────────────────────────────────
        spike = audio_level - self._prev_audio
        if spike > 0.12:                  # voice onset detected
            self._shockwave = 1.0         # trigger expansion
        self._shockwave = max(0.0, self._shockwave - dt * 2.2)   # decay
        self._prev_audio = audio_level

        # ── Rotation accumulation (continuous kinetic fluid motion) ─────────────
        spin_boost = 1.5 + audio * 4.5
        self._rotation += dt * (rotation_spd * 3.8 + audio * 2.5) * spin_boost

        n_core   = int(self.count * 0.25)
        n_shell  = int(self.count * 0.45)
        n_tracks = self.count - n_core - n_shell

        cos_r = math.cos(self._rotation * 0.50)
        sin_r = math.sin(self._rotation * 0.50)

        # ─── 1. NUCLEUS: breathes & pulses dramatically with audio ─────────────
        nucleus_pulse = (
            1.0
            + math.sin(time * pulse_speed * 2.2) * pulse_amp * 0.8
            + audio * 0.75                      # voice pushes nucleus outward
            + self._shockwave * 0.45            # shockwave expands nucleus
        )
        self._positions[:n_core] = self._base[:n_core] * nucleus_pulse

        # ─── 2. PLASMA SHELL: turbulent FBM fluid vector motion ─────────────
        bx = self._base[n_core:n_core + n_shell, 0]
        by = self._base[n_core:n_core + n_shell, 1]
        bz = self._base[n_core:n_core + n_shell, 2]

        # Swirling rotation around vertical Y-axis
        rot_x = bx * cos_r - bz * sin_r
        rot_z = bx * sin_r + bz * cos_r

        # Noise coordinates: time offset creates flowing fluid motion
        noise_scale = 1.8 + turbulence * 0.6 + audio * 1.5
        nx = rot_x * noise_scale + time * (0.45 + audio * 0.85)
        ny = by    * noise_scale + time * (0.35 + audio * 0.75)
        nz = rot_z * noise_scale + time * (0.30 + audio * 0.75)

        # Three FBM layers for rich fluid turbulence
        n1 = fbm3(nx,         ny,         nz,         octaves=3)
        n2 = fbm3(nx + 17.3,  ny + 8.1,   nz + 5.7,   octaves=2)
        n3 = simplex3(nx * 2.1 + 42.0, ny * 2.1, nz * 2.1 + time * (0.8 + audio * 2.0))

        # Displacement magnitude scales hard with audio — plasma erupts on voice!
        disp_scale = 0.09 * (turbulence + audio * 3.5 + self._shockwave * 1.5) * SPHERE_RADIUS
        disp = np.stack((n1, n2, n3), axis=1).astype(np.float32) * disp_scale

        # Shell breathing pulse — each particle oscillates at its own phase
        shell_ph  = self._phase[n_core:n_core + n_shell]
        shell_pulse = (
            1.0
            + np.sin(time * pulse_speed + shell_ph) * pulse_amp
            + audio * 0.50
            + self._shockwave * np.sin(shell_ph) * 0.3
        )
        self._positions[n_core:n_core + n_shell] = (
            self._base[n_core:n_core + n_shell] * shell_pulse[:, np.newaxis] + disp
        )


        # ─── 3. ORBITAL TRACKS: counter-rotate, ripple on voice ──────────────
        n_per = n_tracks // 3
        cursor = n_core + n_shell
        for idx in range(3):
            n_this = n_per if idx < 2 else (self.count - cursor)
            seg = slice(cursor, cursor + n_this)

            # Adjacent rings counter-rotate; audio boosts orbit speed
            dir_mult = 1.0 if idx % 2 == 0 else -1.35
            orbit_speed = (rotation_spd * 2.5 + audio * 2.2) * dir_mult
            angle = self._rotation * orbit_speed * 0.28 + idx * 0.55

            ca, sa = math.cos(angle), math.sin(angle)
            bx_t = self._base[seg, 0]
            by_t = self._base[seg, 1]
            bz_t = self._base[seg, 2]

            rx = bx_t * ca - bz_t * sa
            rz = bx_t * sa + bz_t * ca

            # Synaptic wave: ripples outward along ring arc on voice
            ph_t = self._phase[seg]
            wave_freq = 4.5 + idx * 1.2
            ripple = (
                1.0
                + np.sin(time * wave_freq + ph_t) * 0.012 * (1.0 + audio * 4.0)
                + self._shockwave * np.abs(np.sin(ph_t)) * 0.25
            )
            self._positions[seg] = (
                np.stack((rx, by_t, rz), axis=1).astype(np.float32) * ripple[:, np.newaxis]
            )
            cursor += n_this

        # ─── Brightness: voice makes everything glow brighter ─────────────────
        glow = cfg["glow"] * max(activation, 0.4)
        shock_glow = self._shockwave * 0.5

        # Nucleus: gold core glows intensely on voice
        self._brightness[:n_core] = np.clip(
            0.8 + audio * 0.55 + shock_glow, 0.5, 1.0
        )
        # Shell: energy maps directly to brightness
        self._brightness[n_core:n_core + n_shell] = np.clip(
            0.35 + 0.5 * glow + 0.45 * np.abs(n1) + audio * 0.95 + shock_glow,
            0.15, 1.0
        )
        # Tracks: subtle glow that brightens on voice spikes
        self._brightness[n_core + n_shell:] = np.clip(
            0.25 + 0.4 * glow + audio * 0.6 + shock_glow,
            0.10, 1.0
        )

        # ─── Size: particles grow dramatically with voice ──────────────────────
        voice_scale = 1.0 + audio * 1.8 + self._shockwave * 0.6

        # Core: dense and tight
        self._size[:n_core] = np.clip(
            PARTICLE_MIN_SIZE * 0.8 * voice_scale,
            PARTICLE_MIN_SIZE * 0.5, PARTICLE_MAX_SIZE * 0.7
        )
        # Shell: reactive — grows visibly on every syllable
        base_shell = self._size[n_core:n_core + n_shell]
        self._size[n_core:n_core + n_shell] = np.clip(
            PARTICLE_MIN_SIZE + (PARTICLE_MAX_SIZE - PARTICLE_MIN_SIZE) * (
                0.3 + audio * 0.7 + np.abs(n1) * 0.4
            ) * voice_scale,
            PARTICLE_MIN_SIZE, PARTICLE_MAX_SIZE * 2.0
        )
        # Tracks: fine digital lines
        self._size[n_core + n_shell:] = np.clip(
            PARTICLE_MIN_SIZE * voice_scale,
            PARTICLE_MIN_SIZE * 0.6, PARTICLE_MAX_SIZE * 0.9
        )

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
