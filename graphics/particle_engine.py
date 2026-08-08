"""
graphics/particle_engine.py - ULTRON AI Core Particle Engine

PREVIOUS PROBLEM:
  _generate_jarvis_matrix() used 3-arm spiral + 2 rings.
  At 2D projection this looked like a sun/atom/flower shape.
  This has been REMOVED.

NEW VISUAL:
  _generate_ai_core() creates a clean volumetric intelligence sphere:
    50% - Fibonacci sphere shell (uniform 3D sphere surface — "AI digital brain")
    30% - 4 inclined torus rings (electromagnetic field containment cage)
    20% - Neural filament threads (data flows from core outward)

  Result: A mathematically clean, professional AI-core visualization.
  No sun-rays. No flower petals. No random atom rings.
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
    """
    Uniformly distribute points on a sphere using Fibonacci (golden angle) lattice.
    Result: dense, ordered 3D sphere shell with no clustering/gaps.
    """
    pts = np.zeros((count, 3), dtype=np.float32)
    golden = np.pi * (3.0 - np.sqrt(5.0))
    for i in range(count):
        y = 1.0 - (i / max(count - 1, 1)) * 2.0
        r = np.sqrt(max(1.0 - y * y, 0.0))
        theta = golden * i
        pts[i, 0] = np.cos(theta) * r
        pts[i, 1] = y
        pts[i, 2] = np.sin(theta) * r
    # Scale to radius + small random jitter for organic feel
    pts *= radius
    pts += np.random.normal(0.0, jitter, pts.shape).astype(np.float32)
    return pts


def _torus_ring(count: int, major_r: float, minor_r: float,
                tilt_x: float = 0.0, tilt_z: float = 0.0) -> np.ndarray:
    """
    Generate a ring of particles forming a torus (donut) shape.
    major_r: distance from centre to ring centre
    minor_r: tube radius
    tilt_x/z: rotation angles for orbital inclination
    """
    theta = np.random.uniform(0.0, 2.0 * np.pi, count).astype(np.float32)
    phi   = np.random.uniform(0.0, 2.0 * np.pi, count).astype(np.float32)

    x = (major_r + minor_r * np.cos(phi)) * np.cos(theta)
    y = (major_r + minor_r * np.cos(phi)) * np.sin(theta)
    z = minor_r * np.sin(phi)

    pts = np.stack([x, y, z], axis=1).astype(np.float32)

    # Apply tilt (rotation around X and Z axes)
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


def _neural_filaments(count: int, radius: float) -> np.ndarray:
    """
    Sparse neural filaments: particles scattered along curved paths
    from sphere surface outward, simulating data/energy flows.
    Replaces the random sun-ray spikes with controlled outward threads.
    """
    pts = np.zeros((count, 3), dtype=np.float32)

    # Start from sphere surface points
    n_threads = max(count // 12, 1)
    pts_per_thread = count // n_threads

    golden = np.pi * (3.0 - np.sqrt(5.0))
    for t in range(n_threads):
        i_start = t * pts_per_thread
        i_end   = min(i_start + pts_per_thread, count)
        n       = i_end - i_start

        # Root point on sphere surface
        fi  = golden * t
        yi  = 1.0 - (t / max(n_threads - 1, 1)) * 2.0
        ri  = np.sqrt(max(1.0 - yi * yi, 0.0))
        ox  = np.cos(fi) * ri
        oy  = yi
        oz  = np.sin(fi) * ri

        # Thread extends outward from radius to radius*1.25
        t_vals = np.linspace(0.0, 1.0, n, dtype=np.float32)
        r_vals = radius + t_vals * (radius * 0.25)

        # Slight curve: add sinusoidal perpendicular wobble
        perp_x = -oz
        perp_z =  ox
        wobble  = np.sin(t_vals * np.pi * 2.0) * 0.03

        pts[i_start:i_end, 0] = ox * r_vals + perp_x * wobble
        pts[i_start:i_end, 1] = oy * r_vals + wobble * 0.5
        pts[i_start:i_end, 2] = oz * r_vals + perp_z * wobble

    return pts.astype(np.float32)


def _generate_ai_core(count: int) -> np.ndarray:
    """
    Builds the ULTRON AI Core particle distribution.

    Geometry breakdown:
      50% - Fibonacci sphere shell (clean 3D volumetric sphere surface)
      30% - 4 inclined torus rings (orbital containment structure)
      20% - Neural filament threads (energy/data flows)

    This replaces the old sun/atom/flower spiral shape entirely.
    """
    pts = np.zeros((count, 3), dtype=np.float32)

    n_sphere    = int(count * 0.50)
    n_torus     = int(count * 0.30)
    n_filaments = count - n_sphere - n_torus

    radius = SPHERE_RADIUS

    # ── 1. Fibonacci sphere shell ─────────────────────────────────────────────
    pts[:n_sphere] = _fibonacci_sphere(n_sphere, radius, jitter=0.008)

    # ── 2. Four inclined torus rings at different orbital angles ──────────────
    n_per_torus = n_torus // 4
    torus_configs = [
        # (major_r, minor_r, tilt_x, tilt_z)
        (radius * 1.08, 0.012, 0.00,         0.00),         # equatorial ring
        (radius * 1.12, 0.010, np.pi / 3.5,  0.00),         # 51° inclined
        (radius * 1.10, 0.009, -np.pi / 4.0, np.pi / 6.0),  # 45° + 30° twist
        (radius * 1.15, 0.008, np.pi / 6.0,  -np.pi / 4.0), # 30° + -45° twist
    ]
    cursor = n_sphere
    for idx, (maj, min_, tx, tz) in enumerate(torus_configs):
        n_this = n_per_torus if idx < 3 else (n_sphere + n_torus - cursor)
        pts[cursor:cursor + n_this] = _torus_ring(n_this, maj, min_, tx, tz)
        cursor += n_this

    # ── 3. Neural filament threads ─────────────────────────────────────────────
    pts[n_sphere + n_torus:] = _neural_filaments(n_filaments, radius)

    return pts.astype(np.float32)


class ParticleEngine:
    """
    Drives ULTRON's 150,000 AI-core particles.
    Particles respond in real-time to voice state and audio level.
    """

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

        self._rotation += dt * (rotation_spd + audio * 0.3)

        cos_r = np.cos(self._rotation)
        sin_r = np.sin(self._rotation)
        bx = self._base[:, 0]
        by = self._base[:, 1]
        bz = self._base[:, 2]

        # Rotate around Y axis
        rot_x = bx * cos_r - bz * sin_r
        rot_z = bx * sin_r + bz * cos_r

        # Organic noise displacement
        noise_scale = 1.4 + turbulence * 0.3 + audio * 0.6
        nx = rot_x * noise_scale + time * (0.22 + audio * 0.4)
        ny = by    * noise_scale + time * (0.19 + audio * 0.4)
        nz = rot_z * noise_scale + time * (0.17 + audio * 0.4)

        n1 = fbm3(nx, ny, nz, octaves=2)
        n2 = fbm3(nx + 11.3, ny + 6.7, nz + 3.9, octaves=2)
        n3 = simplex3(nx * 1.8 + 40.0, ny * 1.8, nz * 1.8 + time * (0.4 + audio))

        # Pulse: breathing sphere
        pulse  = np.sin(time * pulse_speed + self._phase) * pulse_amp
        pulse += np.sin(time * pulse_speed * 1.9 + self._phase * 1.5) * pulse_amp * 0.3
        audio_pulse = audio * 0.18 * (1.0 + np.sin(time * 10.0 + self._phase * 2.5))

        displacement = np.stack((n1, n2, n3), axis=1).astype(np.float32)
        displacement *= 0.025 * (turbulence + audio * 1.2)

        radius_mod = 1.0 + pulse + audio_pulse
        self._positions = self._base * radius_mod[:, np.newaxis] + displacement

        # Gentle swirl
        swirl = 0.003 * (turbulence + audio * 1.5)
        self._positions[:, 0] += n3 * swirl
        self._positions[:, 1] += n1 * swirl

        # Brightness
        glow = cfg["glow"] * max(activation, 0.55)
        self._brightness = np.clip(
            0.38
            + 0.42 * glow
            + 0.28 * np.abs(n1)
            + audio * 0.65
            + np.sin(time * 3.5 + self._phase) * 0.08,
            0.15, 1.0,
        ).astype(np.float32)

        size_boost = 1.0 + audio * 0.7 + glow * 0.2
        self._size = np.clip(
            self._size * 0.96
            + np.random.uniform(PARTICLE_MIN_SIZE, PARTICLE_MAX_SIZE, self.count) * 0.04,
            PARTICLE_MIN_SIZE,
            PARTICLE_MAX_SIZE * size_boost,
        ).astype(np.float32)

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
