"""3D Holographic J.A.R.V.I.S. Visualizer Matrix with Concentric Rings & Audio Waveform Oscilloscope."""

from __future__ import annotations

import math
import numpy as np

from graphics.constants import SPHERE_RADIUS
from graphics.state import UltronState


class JarvisVisualizer:
    """Renders 3D concentric holographic rings, orbital nodes, and real-time audio waveform bars."""

    def __init__(self, ring_count: int = 4, segments_per_ring: int = 96, wave_bars: int = 64) -> None:
        self.ring_count = ring_count
        self.segments = segments_per_ring
        self.wave_bars = wave_bars

        # Vertices for rings: ring_count * segments * 2
        # Vertices for wave bars: wave_bars * 2
        self.ring_vert_count = ring_count * segments_per_ring * 2
        self.wave_vert_count = wave_bars * 2
        self.total_vertices = self.ring_vert_count + self.wave_vert_count

        self._vertices = np.zeros((self.total_vertices, 5), dtype=np.float32)

        # Concentric Radii (Hollow J.A.R.V.I.S. structure)
        self.radii = [
            SPHERE_RADIUS * 1.15,
            SPHERE_RADIUS * 1.45,
            SPHERE_RADIUS * 1.75,
            SPHERE_RADIUS * 2.05,
        ]

        self.tilts = [
            (0.35, 0.4, 0.1),
            (-0.45, 0.25, 0.75),
            (0.55, -0.65, 0.25),
            (-0.25, -0.35, -0.55),
        ]
        self.speeds = [0.35, -0.5, 0.65, -0.28]

    def update(self, dt: float, time: float, state: UltronState, audio_level: float) -> None:
        v_idx = 0
        audio_boost = 1.0 + audio_level * 1.8

        # 1. Update Concentric Orbital Rings
        for r_idx in range(self.ring_count):
            radius = self.radii[r_idx] * (1.0 + math.sin(time * 2.5 + r_idx) * 0.02 * audio_boost)
            speed = self.speeds[r_idx]
            rot_angle = time * speed
            tx, ty, tz = self.tilts[r_idx]

            cx, sx = math.cos(tx + rot_angle * 0.3), math.sin(tx + rot_angle * 0.3)
            cy, sy = math.cos(ty + rot_angle), math.sin(ty + rot_angle)
            cz, sz = math.cos(tz), math.sin(tz)

            R = np.array([
                [cy * cz, -cy * sz, sy],
                [sx * sy * cz + cx * sz, -sx * sy * sz + cx * cz, -sx * cy],
                [-cx * sy * cz + sx * sz, cx * sy * sz + sx * cz, cx * cy],
            ], dtype=np.float32)

            width = 0.0035 * audio_boost
            intensity = (0.7 + 0.3 * math.sin(time * 3.5 + r_idx)) * (0.7 + audio_level * 0.9)

            for s in range(self.segments):
                a0 = (s / self.segments) * 2.0 * math.pi
                a1 = ((s + 1) / self.segments) * 2.0 * math.pi

                # Voice-driven harmonic wave ripple
                w0 = radius * (1.0 + 0.04 * math.sin(a0 * 8.0 + time * 6.0) * audio_boost)
                w1 = radius * (1.0 + 0.04 * math.sin(a1 * 8.0 + time * 6.0) * audio_boost)

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

        # 2. Update 3D Audio Frequency Waveform Oscilloscope Bars
        equator_radius = SPHERE_RADIUS * 1.35
        for b in range(self.wave_bars):
            angle = (b / self.wave_bars) * 2.0 * math.pi + time * 0.2
            # Frequency wave height driven by audio_level + harmonic noise
            wave_h = 0.02 + audio_level * 0.22 * (0.5 + 0.5 * math.sin(b * 0.4 + time * 12.0))

            x = math.cos(angle) * equator_radius
            z = math.sin(angle) * equator_radius

            # Bottom of waveform bar
            self._vertices[v_idx, 0:3] = [x, -wave_h * 0.5, z]
            self._vertices[v_idx, 3] = 0.004
            self._vertices[v_idx, 4] = 0.8 + audio_level * 0.5
            v_idx += 1

            # Top of waveform bar
            self._vertices[v_idx, 0:3] = [x, wave_h * 0.5, z]
            self._vertices[v_idx, 3] = 0.004
            self._vertices[v_idx, 4] = 1.0 + audio_level * 0.8
            v_idx += 1

    @property
    def vertices(self) -> np.ndarray:
        return self._vertices

    @property
    def vertex_count(self) -> int:
        return self.total_vertices
