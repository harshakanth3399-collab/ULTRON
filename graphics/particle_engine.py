"""GPU-ready holographic sphere particle field with plasma dynamics."""

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


def _generate_jarvis_matrix(count: int) -> np.ndarray:
    """Generates MCU J.A.R.V.I.S. consciousness matrix matching Tony Stark's lab screenshot."""
    pts = np.zeros((count, 3), dtype=np.float32)

    # 1. 40% Swirling Spiral Galaxy Core (Center Swirl from photo)
    core_count = int(count * 0.40)
    theta = np.linspace(0, 16.0 * np.pi, core_count, dtype=np.float32)
    r_spiral = 0.02 + (theta / (16.0 * np.pi)) * 0.26 + np.random.normal(0.0, 0.008, core_count).astype(np.float32)
    # 3 Spiral arms
    arm_offset = (np.arange(core_count) % 3) * (2.0 * np.pi / 3.0)
    final_theta = theta + arm_offset

    pts[0:core_count, 0] = np.cos(final_theta) * r_spiral
    pts[0:core_count, 1] = np.sin(final_theta) * r_spiral
    pts[0:core_count, 2] = np.random.normal(0.0, 0.01, core_count).astype(np.float32)

    # 2. 35% 2 Concentric Ring Tracks with Tick Marks (Inner Track r=0.32, Outer Track r=0.45)
    track_count = int(count * 0.35)
    t_start = core_count
    t_end = t_start + track_count
    n_track = t_end - t_start

    t_angles = np.random.uniform(0.0, 2.0 * np.pi, n_track).astype(np.float32)
    # Choose track 1 or track 2
    track_select = np.random.choice([0.32, 0.45], size=n_track, p=[0.45, 0.55]).astype(np.float32)
    track_r = track_select + np.random.normal(0.0, 0.006, n_track).astype(np.float32)

    pts[t_start:t_end, 0] = np.cos(t_angles) * track_r
    pts[t_start:t_end, 1] = np.sin(t_angles) * track_r
    pts[t_start:t_end, 2] = np.random.normal(0.0, 0.008, n_track).astype(np.float32)

    # 3. 25% Organic Neural Filaments & Curved Wave Arcs (Movie Neural Matrix)
    spike_start = t_end
    n_spike = count - spike_start

    sp_angles = np.random.uniform(0.0, 2.0 * np.pi, n_spike).astype(np.float32)
    # Logarithmic curved filaments bridging across tracks
    curve_wave = 0.42 + 0.12 * np.sin(sp_angles * 7.0 + np.cos(sp_angles * 3.0) * 2.0)
    sp_dist = (curve_wave + np.random.normal(0.0, 0.012, n_spike)).astype(np.float32)

    pts[spike_start:, 0] = np.cos(sp_angles) * sp_dist
    pts[spike_start:, 1] = np.sin(sp_angles) * sp_dist
    pts[spike_start:, 2] = np.random.normal(0.0, 0.008, n_spike).astype(np.float32)

    # Global subtle 3D tilt plane (like the screenshot perspective)
    pitch, yaw = 0.25, 0.15
    cp, sp = np.cos(pitch), np.sin(pitch)
    cy, sy = np.cos(yaw), np.sin(yaw)

    x_orig, y_orig, z_orig = pts[:, 0].copy(), pts[:, 1].copy(), pts[:, 2].copy()
    pts[:, 0] = x_orig * cy + z_orig * sy
    pts[:, 1] = y_orig * cp - (z_orig * cy - x_orig * sy) * sp
    pts[:, 2] = y_orig * sp + (z_orig * cy - x_orig * sy) * cp

    return pts


class ParticleEngine:
    """Maintains tens of thousands of particles forming the MCU J.A.R.V.I.S. Matrix."""

    __slots__ = (
        "count",
        "_base",
        "_positions",
        "_velocity",
        "_size",
        "_brightness",
        "_phase",
        "_rotation",
    )

    def __init__(self, count: int = PARTICLE_COUNT) -> None:
        self.count = count
        self._base = _generate_jarvis_matrix(count)
        self._positions = self._base.copy()
        self._velocity = np.zeros((count, 3), dtype=np.float32)
        self._phase = np.random.uniform(0.0, 6.28318, count).astype(np.float32)
        self._size = np.random.uniform(PARTICLE_MIN_SIZE, PARTICLE_MAX_SIZE, count).astype(np.float32)
        self._brightness = np.random.uniform(0.35, 1.0, count).astype(np.float32)
        self._rotation = 0.0

    def update(
        self,
        dt: float,
        time: float,
        state: UltronState,
        audio_level: float,
        activation: float,
    ) -> None:
        cfg = STATE_CONFIG[state.name.lower()]
        turbulence = cfg["turbulence"]
        pulse_speed = cfg["pulse_speed"]
        pulse_amp = cfg["pulse_amp"]
        rotation_speed = cfg["rotation"]
        audio = audio_level * cfg["audio_influence"]
        self._rotation += dt * (rotation_speed + audio * 0.45)

        cos_r = np.cos(self._rotation)
        sin_r = np.sin(self._rotation)
        bx = self._base[:, 0]
        by = self._base[:, 1]
        bz = self._base[:, 2]

        rot_x = bx * cos_r - bz * sin_r
        rot_z = bx * sin_r + bz * cos_r

        noise_scale = 1.6 + turbulence * 0.4 + audio * 0.8
        nx = rot_x * noise_scale + time * (0.31 + audio * 0.5)
        ny = by * noise_scale + time * (0.27 + audio * 0.5)
        nz = rot_z * noise_scale + time * (0.23 + audio * 0.5)

        n1 = fbm3(nx, ny, nz, octaves=3)
        n2 = fbm3(nx + 13.7, ny + 7.3, nz + 4.1, octaves=2)
        n3 = simplex3(nx * 2.1 + 50.0, ny * 2.1, nz * 2.1 + time * (0.5 + audio * 1.5))

        pulse = np.sin(time * pulse_speed + self._phase) * pulse_amp
        pulse += np.sin(time * pulse_speed * 2.3 + self._phase * 1.7) * pulse_amp * 0.35
        audio_pulse = audio * 0.22 * (1.0 + np.sin(time * 12.0 + self._phase * 3.0))

        displacement = np.stack((n1, n2, n3), axis=1).astype(np.float32)
        displacement *= 0.035 * (turbulence + audio * 1.5)

        radius_mod = 1.0 + pulse + audio_pulse
        self._positions = self._base * radius_mod[:, np.newaxis] + displacement

        # Plasma swirl along orbital plane
        swirl_strength = 0.004 * (turbulence + audio * 2.0)
        self._positions[:, 0] += n3 * swirl_strength
        self._positions[:, 1] += n1 * swirl_strength

        # Brightness reacts dynamically to audio level and state
        glow = cfg["glow"] * max(activation, 0.6)
        self._brightness = np.clip(
            0.4
            + 0.45 * glow
            + 0.3 * np.abs(n1)
            + audio * 0.75
            + np.sin(time * 4.0 + self._phase) * 0.1,
            0.2,
            1.0,
        ).astype(np.float32)

        size_boost = 1.0 + audio * 0.85 + glow * 0.25
        self._size = np.clip(
            self._size * 0.96 + np.random.uniform(PARTICLE_MIN_SIZE, PARTICLE_MAX_SIZE, self.count) * 0.04,
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
        out[:, 0:3] = self._positions
        out[:, 3] = self._size
        out[:, 4] = self._brightness

        return out
