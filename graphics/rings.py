"""3D Concentric Orbital Rings Generator for Jarvis/Ultron Holographic Visuals."""

from __future__ import annotations

import math
import numpy as np

from graphics.constants import SPHERE_RADIUS
from graphics.state import UltronState


class OrbitalRings:
    """Generates 3D concentric rotating holographic rings surrounding the core orb."""

    def __init__(self, ring_count: int = 4, segments_per_ring: int = 64) -> None:
        self.ring_count = ring_count
        self.segments = segments_per_ring
        self.total_vertices = ring_count * segments_per_ring * 2
        self._vertices = np.zeros((self.total_vertices, 5), dtype=np.float32)

        # Radii and tilt axes for each ring
        self.radii = [SPHERE_RADIUS * 1.25, SPHERE_RADIUS * 1.48, SPHERE_RADIUS * 1.72, SPHERE_RADIUS * 1.95]
        self.tilts = [
            (0.3, 0.5, 0.1),
            (-0.4, 0.2, 0.8),
            (0.6, -0.7, 0.3),
            (-0.2, -0.3, -0.6),
        ]
        self.speeds = [0.4, -0.6, 0.75, -0.3]

    def update(self, dt: float, time: float, state: UltronState, audio_level: float) -> None:
        v_idx = 0
        audio_boost = 1.0 + audio_level * 1.2

        for r_idx in range(self.ring_count):
            radius = self.radii[r_idx] * (1.0 + math.sin(time * 2.0 + r_idx) * 0.02 * audio_boost)
            speed = self.speeds[r_idx]
            rot_angle = time * speed
            tx, ty, tz = self.tilts[r_idx]

            # Rotation matrix for this ring
            cx, sx = math.cos(tx + rot_angle * 0.3), math.sin(tx + rot_angle * 0.3)
            cy, sy = math.cos(ty + rot_angle), math.sin(ty + rot_angle)
            cz, sz = math.cos(tz), math.sin(tz)

            # Combined 3D rotation matrix
            R = np.array([
                [cy * cz, -cy * sz, sy],
                [sx * sy * cz + cx * sz, -sx * sy * sz + cx * cz, -sx * cy],
                [-cx * sy * cz + sx * sz, cx * sy * sz + sx * cz, cx * cy],
            ], dtype=np.float32)

            width = 0.003 * audio_boost
            intensity = (0.6 + 0.4 * math.sin(time * 3.0 + r_idx)) * (0.6 + audio_level * 0.8)

            for s in range(self.segments):
                a0 = (s / self.segments) * 2.0 * math.pi
                a1 = ((s + 1) / self.segments) * 2.0 * math.pi

                # Ring wave distortion
                w0 = radius * (1.0 + 0.03 * math.sin(a0 * 6.0 + time * 5.0) * audio_boost)
                w1 = radius * (1.0 + 0.03 * math.sin(a1 * 6.0 + time * 5.0) * audio_boost)

                p0_local = np.array([math.cos(a0) * w0, math.sin(a0) * w0, 0.0], dtype=np.float32)
                p1_local = np.array([math.cos(a1) * w1, math.sin(a1) * w1, 0.0], dtype=np.float32)

                p0_world = R @ p0_local
                p1_world = R @ p1_local

                self._vertices[v_idx, 0:3] = p0_world
                self._vertices[v_idx, 3] = width
                self._vertices[v_idx, 4] = intensity
                v_idx += 1

                self._vertices[v_idx, 0:3] = p1_world
                self._vertices[v_idx, 3] = width
                self._vertices[v_idx, 4] = intensity * 0.95
                v_idx += 1

    @property
    def vertices(self) -> np.ndarray:
        return self._vertices

    @property
    def vertex_count(self) -> int:
        return self.total_vertices
