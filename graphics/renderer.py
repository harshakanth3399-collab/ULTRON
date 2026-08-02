"""Primary ModernGL renderer for the ULTRON holographic sphere."""

from __future__ import annotations

import math
import time

import moderngl
import numpy as np
from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from graphics.arc_system import ArcSystem
from graphics.audio_analyzer import AudioAnalyzer
from graphics.bloom import BloomPass
from graphics.constants import (
    COLOR_ARC,
    COLOR_CORE,
    COLOR_DEEP,
    COLOR_GLOW,
    FRAME_MS,
    SPHERE_RADIUS,
)
from graphics.particle_engine import ParticleEngine
from graphics.shaders import (
    ARC_FRAG,
    ARC_GEOM,
    ARC_VERT,
    PARTICLE_FRAG,
    PARTICLE_VERT,
    SPHERE_GLOW_FRAG,
    SPHERE_GLOW_VERT,
)
from graphics.state import StateManager, UltronState


def _perspective(fov_deg: float, aspect: float, near: float, far: float) -> np.ndarray:
    f = 1.0 / math.tan(math.radians(fov_deg) * 0.5)
    m = np.zeros((4, 4), dtype=np.float32)
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = (2.0 * far * near) / (near - far)
    m[3, 2] = -1.0
    return m


def _look_at(eye: np.ndarray, center: np.ndarray, up: np.ndarray) -> np.ndarray:
    f = center - eye
    f = f / np.linalg.norm(f)
    s = np.cross(f, up)
    s = s / np.linalg.norm(s)
    u = np.cross(s, f)
    m = np.eye(4, dtype=np.float32)
    m[0, :3] = s
    m[1, :3] = u
    m[2, :3] = -f
    m[0, 3] = -np.dot(s, eye)
    m[1, 3] = -np.dot(u, eye)
    m[2, 3] = np.dot(f, eye)
    return m


class UltronRenderer(QOpenGLWidget):
    """Fullscreen OpenGL widget rendering the holographic energy sphere."""

    state_changed = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setMinimumSize(640, 480)
        self.setFocusPolicy(Qt.StrongFocus)

        self._ctx: moderngl.Context | None = None
        self._engine = ParticleEngine()
        self._arcs = ArcSystem()
        self._states = StateManager()
        self._audio = AudioAnalyzer()

        self._time = 0.0
        self._last_frame = time.perf_counter()
        self._audio_level = 0.0
        self._width = 1
        self._height = 1
        self._ready = False
        self._use_geom_shader = False
        self._speaking_fn = lambda: False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def set_speaking_callback(self, fn) -> None:
        self._speaking_fn = fn

    def set_state(self, state: UltronState) -> None:
        self._states.set_state(state)
        self.state_changed.emit(state)

    @property
    def state_manager(self) -> StateManager:
        return self._states

    @property
    def audio_level(self) -> float:
        return self._audio_level

    def initializeGL(self) -> None:
        try:
            self._init_gl()
        except Exception as exc:
            import sys
            print(f"ULTRON GL init failed: {exc}", file=sys.stderr)
            raise

    def _init_gl(self) -> None:
        self._ctx = moderngl.create_context()
        ctx = self._ctx
        self._width = max(self.width(), 1)
        self._height = max(self.height(), 1)
        ctx.enable(moderngl.BLEND)
        ctx.enable(moderngl.DEPTH_TEST)
        ctx.depth_func = "<"
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE

        self._particle_prog = ctx.program(
            vertex_shader=PARTICLE_VERT,
            fragment_shader=PARTICLE_FRAG,
        )
        self._glow_prog = ctx.program(
            vertex_shader=SPHERE_GLOW_VERT,
            fragment_shader=SPHERE_GLOW_FRAG,
        )

        self._try_init_arc_shader(ctx)

        stride = 5 * 4
        self._particle_vbo = ctx.buffer(reserve=self._engine.count * stride)
        self._particle_vao = ctx.vertex_array(
            self._particle_prog,
            [
                (self._particle_vbo, "3f 1f 1f", "in_pos", "in_size", "in_brightness"),
            ],
            mode=moderngl.POINTS,
        )

        arc_stride = 5 * 4
        self._arc_vbo = ctx.buffer(reserve=self._arcs.vertex_count * arc_stride)
        if self._use_geom_shader:
            self._arc_vao = ctx.vertex_array(
                self._arc_prog,
                [
                    (self._arc_vbo, "3f 1f 1f", "in_pos", "in_width", "in_intensity"),
                ],
                mode=moderngl.LINES,
            )
        else:
            self._arc_vao = ctx.vertex_array(
                self._arc_prog,
                [
                    (self._arc_vbo, "3f 1f 1f", "in_pos", "in_width", "in_intensity"),
                ],
                mode=moderngl.TRIANGLES,
            )

        glow_verts = np.array(
            [
                [0.0, 0.0],
                [1.0, 0.0],
                [1.0, 1.0],
                [0.0, 0.0],
                [1.0, 1.0],
                [0.0, 1.0],
            ],
            dtype="f4",
        )
        self._glow_vbo = ctx.buffer(glow_verts.tobytes())
        self._glow_vao = ctx.vertex_array(
            self._glow_prog,
            [(self._glow_vbo, "2f", "in_uv")],
        )

        self._scene_fbo = self._create_scene_fbo(self._width, self._height)
        self._bloom = BloomPass(ctx, self._width, self._height)
        self._ready = True
        self._timer.start(FRAME_MS)
        self.update()

    def _try_init_arc_shader(self, ctx: moderngl.Context) -> None:
        try:
            self._arc_prog = ctx.program(
                vertex_shader=ARC_VERT,
                geometry_shader=ARC_GEOM,
                fragment_shader=ARC_FRAG,
            )
            self._use_geom_shader = True
        except moderngl.Error:
            self._arc_prog = ctx.program(
                vertex_shader=ARC_VERT,
                fragment_shader=ARC_FRAG,
            )
            self._use_geom_shader = False

    def _create_scene_fbo(self, width: int, height: int) -> moderngl.Framebuffer:
        color = self._ctx.texture((width, height), 4, dtype="f4")
        depth = self._ctx.depth_renderbuffer((width, height))
        return self._ctx.framebuffer(color_attachments=[color], depth_attachment=depth)

    def resizeGL(self, width: int, height: int) -> None:
        self._width = max(width, 1)
        self._height = max(height, 1)
        if self._ctx is None:
            return
        self._ctx.viewport = (0, 0, self._width, self._height)

        if hasattr(self, "_scene_fbo"):
            for tex in self._scene_fbo.color_attachments:
                tex.release()
            if self._scene_fbo.depth_attachment:
                self._scene_fbo.depth_attachment.release()
            self._scene_fbo.release()
            self._scene_fbo = self._create_scene_fbo(self._width, self._height)
            self._bloom.resize(self._width, self._height)

    def _tick(self) -> None:
        self.update()

    def _compute_mvp(self) -> np.ndarray:
        aspect = self._width / self._height
        proj = _perspective(42.0, aspect, 0.05, 8.0)
        eye = np.array([0.0, 0.05, 1.35], dtype=np.float32)
        view = _look_at(eye, np.zeros(3, dtype=np.float32), np.array([0.0, 1.0, 0.0], dtype=np.float32))
        return (proj @ view).astype(np.float32)

    def _build_arc_triangles(self, line_verts: np.ndarray) -> np.ndarray:
        """Expand line pairs into camera-facing quads (two triangles each)."""
        count = len(line_verts) // 2
        if count == 0:
            return np.zeros((0, 5), dtype=np.float32)

        tris = np.zeros((count * 6, 5), dtype=np.float32)
        for i in range(count):
            a = line_verts[i * 2]
            b = line_verts[i * 2 + 1]
            if a[4] <= 0.001 and b[4] <= 0.001:
                continue

            pa = a[0:3]
            pb = b[0:3]
            mid = (pa + pb) * 0.5
            view_dir = np.array([0.0, -0.05, -1.35], dtype=np.float32)
            view_dir = view_dir / np.linalg.norm(view_dir)
            tangent = pb - pa
            tangent = tangent / max(np.linalg.norm(tangent), 1e-6)
            normal = np.cross(tangent, view_dir)
            n_len = np.linalg.norm(normal)
            if n_len < 1e-6:
                normal = np.cross(tangent, np.array([0.0, 1.0, 0.0], dtype=np.float32))
                n_len = np.linalg.norm(normal)
            normal = normal / max(n_len, 1e-6)

            half_w = (a[3] + b[3]) * 0.5 * 0.65
            intensity = (a[4] + b[4]) * 0.5

            v0 = pa - normal * half_w
            v1 = pa + normal * half_w
            v2 = pb + normal * half_w
            v3 = pb - normal * half_w

            base = i * 6
            for j, v in enumerate((v0, v1, v2, v0, v2, v3)):
                tris[base + j, 0:3] = v
                tris[base + j, 3] = half_w
                tris[base + j, 4] = intensity

        return tris

    def paintGL(self) -> None:
       
        if not self._ready or self._ctx is None:
            return

        now = time.perf_counter()
        dt = min(now - self._last_frame, 0.05)
        self._last_frame = now
        self._time += dt

        self._states.update(dt)
        self._audio_level = self._audio.update(dt, self._states.state, self._speaking_fn)

        cfg_name = self._states.state.name.lower()
        from graphics.constants import STATE_CONFIG

        cfg = STATE_CONFIG[cfg_name]
        activation = self._states.activation()

        self._engine.update(
            dt,
            self._time,
            self._states.state,
            self._audio_level,
            activation,
        )
        self._arcs.update(
            dt,
            self._time,
            self._states.state,
            self._audio_level,
            activation,
            self._engine.positions,
        )

        mvp = self._compute_mvp()
        glow = cfg["glow"] * activation

        # Render scene to HDR framebuffer
        self._scene_fbo.use()
        self._ctx.clear(0.0, 0.0, 0.0, 1.0)
        self._ctx.enable(moderngl.DEPTH_TEST)

        # Inner volumetric glow
        self._glow_prog["u_mvp"].write(mvp.tobytes())
        self._glow_prog["u_radius"].value = SPHERE_RADIUS
        self._glow_prog["u_time"].value = self._time
        self._glow_prog["u_intensity"].value = glow * (0.6 + self._audio_level * 0.5)
        self._glow_prog["u_color_deep"].value = COLOR_DEEP
        self._glow_vao.render()

        # Electric arcs
        arc_data = self._arcs.vertices
        if self._use_geom_shader:
            self._arc_vbo.write(arc_data.tobytes())
            self._arc_prog["u_mvp"].write(mvp.tobytes())
            self._arc_prog["u_viewport"].value = (float(self._width), float(self._height))
            self._arc_prog["u_time"].value = self._time
            self._arc_prog["u_color_arc"].value = COLOR_ARC
            self._arc_vao.render(moderngl.LINES, vertices=len(arc_data))
        else:
            tri_data = self._build_arc_triangles(arc_data)
            if len(tri_data):
                self._arc_vbo.write(tri_data.tobytes())
                self._arc_prog["u_mvp"].write(mvp.tobytes())
                self._arc_prog["u_time"].value = self._time
                self._arc_prog["u_color_arc"].value = COLOR_ARC
                self._arc_vao.render(moderngl.TRIANGLES, vertices=len(tri_data))

        # Particles
        packed = self._engine.interleaved_buffer()
        self._particle_vbo.write(packed.tobytes())
        self._particle_prog["u_mvp"].write(mvp.tobytes())
        self._particle_prog["u_time"].value = self._time
        self._particle_prog["u_glow"].value = glow
        self._particle_prog["u_color_core"].value = COLOR_CORE
        self._particle_prog["u_color_glow"].value = COLOR_GLOW
        print("Particle Count:", self._engine.count)
        self._particle_vao.render(moderngl.POINTS, vertices=self._engine.count)

        # Bloom composite to default framebuffer
        self._ctx.screen.use()
        self._ctx.viewport = (0, 0, self._width, self._height)
        self._bloom.apply(self._scene_fbo.color_attachments[0], self._ctx.screen)

    def initializeGL(self) -> None:
      try:
        self._init_gl()
      except Exception as exc:
       import sys
       print(f"ULTRON GL init failed: {exc}", file=sys.stderr)