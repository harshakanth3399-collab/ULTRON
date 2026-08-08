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
    """Generates MCU J.A.R.V.I.S. consciousness matrix: 4 concentric orbital ring disks + radial filaments + core."""
    pts = np.zeros((count, 3), dtype=np.float32)

    # 1. 75% Concentric Orbital Ring Disks
    ring_count = int(count * 0.75)
    radii = [0.18, 0.30, 0.42, 0.54]
    tilts = [(0.35, 0.4), (-0.45, 0.25), (0.55, -0.65), (-0.25, -0.35)]

    per_ring = ring_count // 4
    for r_idx in range(4):
        start = r_idx * per_ring
        end = (r_idx + 1) * per_ring if r_idx < 3 else ring_count
        n_pts = end - start

        angles = np.random.uniform(0.0, 2.0 * np.pi, n_pts).astype(np.float32)
        r_var = (radii[r_idx] + np.random.normal(0.0, 0.015, n_pts)).astype(np.float32)
        h_var = np.random.normal(0.0, 0.01, n_pts).astype(np.float32)

        x_local = np.cos(angles) * r_var
        y_local = np.sin(angles) * r_var
        z_local = h_var

        pitch, yaw = tilts[r_idx]
        cp, sp = np.cos(pitch), np.sin(pitch)
        cy, sy = np.cos(yaw), np.sin(yaw)

        x = x_local * cy + z_local * sy
        y = y_local * cp - (z_local * cy - x_local * sy) * sp
        z = y_local * sp + (z_local * cy - x_local * sy) * cp

        pts[start:end] = np.stack((x, y, z), axis=1)

    # 2. 15% Radial Filament Spokes (Spikes bursting from center)
    spoke_count = int(count * 0.15)
    spoke_start = ring_count
    spoke_end = spoke_start + spoke_count

    spoke_angles = ((np.arange(spoke_count) % 36) * (2.0 * np.pi / 36.0) + np.random.normal(0.0, 0.02, spoke_count)).astype(np.float32)
    dist = np.random.uniform(0.05, 0.58, spoke_count).astype(np.float32)
    h_spoke = np.random.normal(0.0, 0.02, spoke_count).astype(np.float32)

    pts[spoke_start:spoke_end, 0] = np.cos(spoke_angles) * dist
    pts[spoke_start:spoke_end, 1] = np.sin(spoke_angles) * dist
    pts[spoke_start:spoke_end, 2] = h_spoke

    # 3. 10% Swirling Central Core Cluster
    core_start = spoke_end
    n_core = count - core_start
    core_r = np.random.uniform(0.0, 0.12, n_core).astype(np.float32)
    core_phi = np.random.uniform(0.0, 2.0 * np.pi, n_core).astype(np.float32)
    core_theta = np.random.uniform(0.0, np.pi, n_core).astype(np.float32)

    pts[core_start:, 0] = core_r * np.sin(core_theta) * np.cos(core_phi)
    pts[core_start:, 1] = core_r * np.sin(core_theta) * np.sin(core_phi)
    pts[core_start:, 2] = core_r * np.cos(core_theta)

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
