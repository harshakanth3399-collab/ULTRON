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


def _fibonacci_sphere(count: int, radius: float) -> np.ndarray:
    """Even distribution of points on a sphere."""
    golden = np.pi * (3.0 - np.sqrt(5.0))
    i = np.arange(count, dtype=np.float32)
    y = 1.0 - (2.0 * i + 1.0) / count
    r = np.sqrt(np.clip(1.0 - y * y, 0.0, None))
    theta = golden * i
    x = np.cos(theta) * r
    z = np.sin(theta) * r
    return np.stack((x, y, z), axis=1) * radius


class ParticleEngine:
    """Maintains tens of thousands of particles locked to a turbulent sphere shell."""

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
        self._base = _fibonacci_sphere(count, SPHERE_RADIUS).astype(np.float32)
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
        displacement *= 0.055 * (turbulence + audio * 1.8)

        radius_mod = SPHERE_RADIUS * (1.0 + pulse + audio_pulse)
        direction = self._base / (np.linalg.norm(self._base, axis=1, keepdims=True) + 1e-8)

        self._positions = direction * radius_mod[:, np.newaxis] + displacement

        # Plasma swirl: tangential drift along surface (Jarvis/Ultron orb effect)
        tangent = np.cross(direction, np.array([0.0, 1.0, 0.0], dtype=np.float32))
        t_len = np.linalg.norm(tangent, axis=1, keepdims=True)
        fallback = np.cross(direction, np.array([1.0, 0.0, 0.0], dtype=np.float32))
        tangent = np.where(t_len > 1e-4, tangent / np.maximum(t_len, 1e-4), fallback)

        swirl_strength = 0.006 * (turbulence + audio * 2.5)
        self._positions += tangent * (n3 * swirl_strength)[:, np.newaxis]

        # Re-normalize to shell with voice-driven thickness expansion
        shell_radius = np.linalg.norm(self._positions, axis=1, keepdims=True)
        target_r = SPHERE_RADIUS * (1.0 + pulse[:, np.newaxis] * 0.5 + audio * 0.18)
        self._positions *= target_r / np.maximum(shell_radius, 1e-6)

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
