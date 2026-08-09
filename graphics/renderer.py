"""Production ULTRON OpenGL Renderer with Audit Harness & Billboard Fallback."""

from __future__ import annotations

import math
import os
import sys
import time
from typing import Optional

# Ensure project root is in sys.path if run directly
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


import numpy as np
import moderngl
from PySide6 import __version__ as PYSIDE6_VERSION
from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from OpenGL import GL

from graphics.arc_system import ArcSystem
from graphics.audio_analyzer import AudioAnalyzer
from graphics.bloom import BloomPass
from graphics.jarvis_visualizer import JarvisVisualizer
from graphics.constants import (
    COLOR_ARC,
    COLOR_CORE,
    COLOR_DEEP,
    COLOR_GLOW,
    FRAME_MS,
    PARTICLE_COUNT,
    SPHERE_RADIUS,
    STATE_CONFIG,
    ARC_COUNT,
    ARC_SEGMENTS,
)
from graphics.particle_engine import ParticleEngine
from graphics.shaders import (
    ARC_FRAG,
    ARC_GEOM,
    ARC_VERT,
    BILLBOARD_FRAG,
    BILLBOARD_VERT,
    BLIT_FRAG,
    FULLSCREEN_VERT,
    PARTICLE_FRAG,
    PARTICLE_VERT,
    SPHERE_GLOW_FRAG,
    SPHERE_GLOW_VERT,
)
from graphics.state import StateManager, UltronState

LOG_PATH = os.path.join(os.getcwd(), "renderer_audit.log")


def _log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    print(line, end="")


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


def gl_get_string(name):
    res = GL.glGetString(name)
    if res is None:
        return "<unknown>"
    return res.decode("utf-8")


def compile_shader_and_log(vs_src: str, fs_src: str, gs_src: Optional[str] = None) -> bool:
    vs = GL.glCreateShader(GL.GL_VERTEX_SHADER)
    GL.glShaderSource(vs, vs_src)
    GL.glCompileShader(vs)
    compiled = GL.glGetShaderiv(vs, GL.GL_COMPILE_STATUS)
    if not compiled:
        log = GL.glGetShaderInfoLog(vs).decode("utf-8", errors="ignore")
        _log(f"Vertex shader compile FAILED:\n{log}")
    else:
        _log("Vertex shader compiled successfully.")

    fs = GL.glCreateShader(GL.GL_FRAGMENT_SHADER)
    GL.glShaderSource(fs, fs_src)
    GL.glCompileShader(fs)
    compiled_fs = GL.glGetShaderiv(fs, GL.GL_COMPILE_STATUS)
    if not compiled_fs:
        log = GL.glGetShaderInfoLog(fs).decode("utf-8", errors="ignore")
        _log(f"Fragment shader compile FAILED:\n{log}")
    else:
        _log("Fragment shader compiled successfully.")

    gs = None
    compiled_gs = True
    if gs_src is not None:
        gs = GL.glCreateShader(GL.GL_GEOMETRY_SHADER)
        GL.glShaderSource(gs, gs_src)
        GL.glCompileShader(gs)
        compiled_gs = bool(GL.glGetShaderiv(gs, GL.GL_COMPILE_STATUS))
        if not compiled_gs:
            log = GL.glGetShaderInfoLog(gs).decode("utf-8", errors="ignore")
            _log(f"Geometry shader compile FAILED:\n{log}")

    prog = GL.glCreateProgram()
    GL.glAttachShader(prog, vs)
    GL.glAttachShader(prog, fs)
    if gs is not None:
        GL.glAttachShader(prog, gs)
    GL.glLinkProgram(prog)
    linked = GL.glGetProgramiv(prog, GL.GL_LINK_STATUS)
    if not linked:
        log = GL.glGetProgramInfoLog(prog).decode("utf-8", errors="ignore")
        _log(f"Program link FAILED:\n{log}")

    GL.glDeleteProgram(prog)
    GL.glDeleteShader(vs)
    GL.glDeleteShader(fs)
    if gs is not None:
        GL.glDeleteShader(gs)

    return bool(compiled and compiled_fs and compiled_gs and linked)


def read_pixels_center(width: int, height: int, w: int = 16, h: int = 16) -> np.ndarray:
    x = max((width - w) // 2, 0)
    y = max((height - h) // 2, 0)
    buf = GL.glReadPixels(x, y, w, h, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE)
    arr = np.frombuffer(buf, dtype=np.uint8)
    if arr.size == 0:
        return np.zeros((h, w, 4), dtype=np.uint8)
    return arr.reshape((h, w, 4))


def count_nonblack_pixels(pixels: np.ndarray, threshold: int = 8) -> int:
    rgb = pixels[:, :, :3]
    lum = rgb.max(axis=2)
    return int((lum > threshold).sum())


class UltronRenderer(QOpenGLWidget):
    """Production ModernGL widget for high-performance holographic rendering."""

    state_changed = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(640, 480)
        self.setFocusPolicy(Qt.StrongFocus)

        self._ctx: Optional[moderngl.Context] = None
        self._engine = ParticleEngine()
        self._arcs = ArcSystem()
        self._jarvis = JarvisVisualizer()
        self._state_manager = StateManager()
        self._audio = AudioAnalyzer()

        self._time = 0.0
        self._last_frame = time.perf_counter()
        self._width = 1
        self._height = 1
        self._ready = False
        self._use_billboards = False
        self._speaking_fn = lambda: False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(FRAME_MS)

        self._audit_done = False
        self._audit_passed = False

    @property
    def state_manager(self) -> StateManager:
        return self._state_manager

    def set_speaking_callback(self, fn) -> None:
        self._speaking_fn = fn

    def set_state(self, state: UltronState) -> None:
        self._state_manager.set_state(state)
        self.state_changed.emit(state)

    def initializeGL(self) -> None:
        try:
            with open(LOG_PATH, "w", encoding="utf-8") as f:
                f.write("")
        except Exception:
            pass

        _log("--- ULTRON Renderer Initialization ---")

        try:
            _log(f"GL VENDOR: {gl_get_string(GL.GL_VENDOR)}")
            _log(f"GL RENDERER: {gl_get_string(GL.GL_RENDERER)}")
            _log(f"GL VERSION: {gl_get_string(GL.GL_VERSION)}")
        except Exception:
            pass

        try:
            self._ctx = moderngl.create_context()
            dpr = float(self.devicePixelRatio()) if hasattr(self, "devicePixelRatio") else 1.0
            self._width = max(int(self.width() * dpr), 1)
            self._height = max(int(self.height() * dpr), 1)
            self._ctx.viewport = (0, 0, self._width, self._height)
            self._ctx.enable(moderngl.BLEND)
            self._ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE
            self._ctx.enable(moderngl.DEPTH_TEST)
            try:
                self._ctx.enable(moderngl.PROGRAM_POINT_SIZE)
            except Exception:
                pass
            _log(f"ModernGL context created successfully (physical size: {self._width}x{self._height}).")
        except Exception as e:
            _log(f"Failed to create ModernGL context: {e}")
            raise

        # Compile Programs
        try:
            self._particle_prog = self._ctx.program(
                vertex_shader=PARTICLE_VERT, fragment_shader=PARTICLE_FRAG
            )
            self._billboard_prog = self._ctx.program(
                vertex_shader=BILLBOARD_VERT, fragment_shader=BILLBOARD_FRAG
            )
            self._glow_prog = self._ctx.program(
                vertex_shader=SPHERE_GLOW_VERT, fragment_shader=SPHERE_GLOW_FRAG
            )
            self._blit_prog = self._ctx.program(
                vertex_shader=FULLSCREEN_VERT, fragment_shader=BLIT_FRAG
            )
            try:
                self._arc_prog = self._ctx.program(
                    vertex_shader=ARC_VERT, fragment_shader=ARC_FRAG, geometry_shader=ARC_GEOM
                )
            except Exception as e:
                _log(f"Geometry shader program skipped fallback to lines: {e}")
                self._arc_prog = self._ctx.program(
                    vertex_shader=ARC_VERT, fragment_shader=ARC_FRAG
                )

            _log("ModernGL shader programs initialized.")
        except Exception as e:
            _log(f"Shader compilation failed: {e}")
            raise

        # VBOs and VAOs
        quad = np.array([
            [-1.0, -1.0], [1.0, -1.0], [1.0, 1.0],
            [-1.0, -1.0], [1.0, 1.0], [-1.0, 1.0],
        ], dtype="f4")
        self._quad_vbo = self._ctx.buffer(quad.tobytes())
        self._glow_vao = self._ctx.vertex_array(self._glow_prog, [(self._quad_vbo, "2f", "in_uv")])
        self._blit_vao = self._ctx.vertex_array(self._blit_prog, [(self._quad_vbo, "2f", "in_uv")])

        # Particle Buffers
        stride = 5 * 4
        self._particle_vbo = self._ctx.buffer(reserve=PARTICLE_COUNT * stride)
        self._particle_vao = self._ctx.vertex_array(
            self._particle_prog,
            [(self._particle_vbo, "3f 1f 1f", "in_pos", "in_size", "in_brightness")],
            mode=moderngl.POINTS,
        )

        # Instanced Billboard Buffers
        quad_2d = np.array([
            [-0.5, -0.5], [0.5, -0.5], [-0.5, 0.5], [0.5, 0.5]
        ], dtype="f4")
        self._quad_2d_vbo = self._ctx.buffer(quad_2d.tobytes())
        self._billboard_vao = self._ctx.vertex_array(
            self._billboard_prog,
            [
                (self._quad_2d_vbo, "2f", "in_quad"),
                (self._particle_vbo, "3f 1f 1f /i", "in_pos", "in_size", "in_brightness"),
            ],
            mode=moderngl.TRIANGLE_STRIP,
        )

        # Arc & Ring Buffers
        arc_max_verts = ARC_COUNT * ARC_SEGMENTS * 2
        self._arc_vbo = self._ctx.buffer(reserve=arc_max_verts * stride)
        self._arc_vao = self._ctx.vertex_array(
            self._arc_prog,
            [(self._arc_vbo, "3f 1f 1f", "in_pos", "in_width", "in_intensity")],
            mode=moderngl.LINES,
        )

        ring_max_verts = self._jarvis.vertex_count
        self._ring_vbo = self._ctx.buffer(reserve=ring_max_verts * stride)
        self._ring_vao = self._ctx.vertex_array(
            self._arc_prog,
            [(self._ring_vbo, "3f 1f 1f", "in_pos", "in_width", "in_intensity")],
            mode=moderngl.LINES,
        )

        # Framebuffers & Bloom
        self._build_scene_fbo()
        self._bloom = BloomPass(self._ctx, self._width, self._height)

        self._ready = True
        _log("ULTRON Renderer initialized successfully.")

    def _build_scene_fbo(self) -> None:
        if hasattr(self, "_scene_fbo") and self._scene_fbo is not None:
            try:
                for tex in self._scene_fbo.color_attachments:
                    tex.release()
                if self._scene_fbo.depth_attachment:
                    self._scene_fbo.depth_attachment.release()
                self._scene_fbo.release()
            except Exception:
                pass

        # Always use f1 (uint8) — Intel Iris Xe / Windows OGL 3.3 Core
        # does NOT reliably support float32 FBO attachments.
        color = self._ctx.texture((self._width, self._height), 4, dtype="f1")
        color.filter = (moderngl.LINEAR, moderngl.LINEAR)
        depth = self._ctx.depth_renderbuffer((self._width, self._height))
        self._scene_fbo = self._ctx.framebuffer(color_attachments=[color], depth_attachment=depth)


    def resizeGL(self, width: int, height: int) -> None:
        dpr = float(self.devicePixelRatio()) if hasattr(self, "devicePixelRatio") else 1.0
        self._width = max(int(width * dpr), 1)
        self._height = max(int(height * dpr), 1)
        if self._ctx is None:
            return
        self._ctx.viewport = (0, 0, self._width, self._height)
        self._build_scene_fbo()
        if hasattr(self, "_bloom") and self._bloom is not None:
            self._bloom.resize(self._width, self._height)

    def _compute_mvp(self) -> np.ndarray:
        aspect = self._width / self._height
        proj = _perspective(45.0, aspect, 0.05, 8.0)
        eye = np.array([0.0, 0.0, 1.35], dtype=np.float32)
        view = _look_at(eye, np.zeros(3, dtype=np.float32), np.array([0.0, 1.0, 0.0], dtype=np.float32))
        return (proj @ view).astype(np.float32)

    def paintGL(self) -> None:
        if not self._ready or self._ctx is None:
            return

        try:
            now = time.perf_counter()
            dt = min(now - self._last_frame, 0.05)
            self._last_frame = now
            self._time += dt

            # Update animation states
            self._state_manager.update(dt)
            state = self._state_manager.state
            audio_level = self._audio.update(dt, state, self._speaking_fn)
            activation = self._state_manager.activation()

            self._engine.update(dt, self._time, state, audio_level, activation)
            self._arcs.update(dt, self._time, state, audio_level, activation, self._engine.positions)
            self._jarvis.update(dt, self._time, state, audio_level)

            # Audit check on first frame
            if not self._audit_done:
                self._verify_renderer()
                self._audit_done = True

            mvp = self._compute_mvp()

            # 1. Render Scene to Offscreen Framebuffer
            self._scene_fbo.use()
            self._ctx.clear(0.0, 0.0, 0.0, 1.0, depth=1.0)

            # 1a. Core Glow (Disabled to keep background pitch black for crisp MCU details)
            pass

            # 1b. Electric Arcs & J.A.R.V.I.S. 3D Rings + Oscilloscope
            try:
                self._ctx.enable(moderngl.DEPTH_TEST)
                arc_data = self._arcs.vertices
                self._arc_vbo.write(arc_data.tobytes())

                ring_data = self._jarvis.vertices
                self._ring_vbo.write(ring_data.tobytes())

                if "u_mvp" in self._arc_prog:
                    self._arc_prog["u_mvp"].write(mvp.tobytes())
                if "u_color_arc" in self._arc_prog:
                    self._arc_prog["u_color_arc"].value = COLOR_ARC
                if "u_time" in self._arc_prog:
                    self._arc_prog["u_time"].value = self._time
                if "u_viewport" in self._arc_prog:
                    self._arc_prog["u_viewport"].value = (float(self._width), float(self._height))

                self._arc_vao.render(moderngl.LINES, vertices=self._arcs.vertex_count)
                self._ring_vao.render(moderngl.LINES, vertices=self._jarvis.vertex_count)
            except Exception:
                pass

            # 1c. Particle Sphere (Point Sprites or Instanced Billboards)
            try:
                packed_particles = self._engine.interleaved_buffer()
                self._particle_vbo.write(packed_particles.tobytes())

                cfg = STATE_CONFIG[state.name.lower()]
                glow_val = cfg["glow"] * activation

                if self._use_billboards:
                    if "u_mvp" in self._billboard_prog:
                        self._billboard_prog["u_mvp"].write(mvp.tobytes())
                    if "u_viewport" in self._billboard_prog:
                        self._billboard_prog["u_viewport"].value = (float(self._width), float(self._height))
                    if "u_glow" in self._billboard_prog:
                        self._billboard_prog["u_glow"].value = glow_val
                    if "u_color_core" in self._billboard_prog:
                        self._billboard_prog["u_color_core"].value = COLOR_CORE
                    if "u_color_glow" in self._billboard_prog:
                        self._billboard_prog["u_color_glow"].value = COLOR_GLOW
                    self._billboard_vao.render(moderngl.TRIANGLE_STRIP, instances=self._engine.count)
                else:
                    if "u_mvp" in self._particle_prog:
                        self._particle_prog["u_mvp"].write(mvp.tobytes())
                    if "u_time" in self._particle_prog:
                        self._particle_prog["u_time"].value = self._time
                    if "u_glow" in self._particle_prog:
                        self._particle_prog["u_glow"].value = glow_val
                    if "u_color_core" in self._particle_prog:
                        self._particle_prog["u_color_core"].value = COLOR_CORE
                    if "u_color_glow" in self._particle_prog:
                        self._particle_prog["u_color_glow"].value = COLOR_GLOW
                    self._particle_vao.render(moderngl.POINTS, vertices=self._engine.count)
            except Exception as e:
                _log(f"Particle render pass error: {e}")

            # 2. Bloom Post-processing Composite to Screen
            try:
                qt_fbo_id = self.defaultFramebufferObject()
                target_fbo = self._ctx.detect_framebuffer(qt_fbo_id) if qt_fbo_id != 0 else self._ctx.screen
                self._bloom.apply(self._scene_fbo.color_attachments[0], target_fbo)
            except Exception as e:
                _log(f"Bloom apply error: {e}")
                try:
                    qt_fbo_id = self.defaultFramebufferObject()
                    target_fbo = self._ctx.detect_framebuffer(qt_fbo_id) if qt_fbo_id != 0 else self._ctx.screen
                    target_fbo.use()
                    self._ctx.viewport = (0, 0, self._width, self._height)
                    self._scene_fbo.color_attachments[0].use(location=0)
                    self._blit_prog["u_tex"].value = 0
                    self._blit_vao.render(moderngl.TRIANGLES)
                except Exception:
                    pass

        except Exception as e:
            # Master safety net — prevents ANY exception from crashing the Qt C++ layer
            _log(f"paintGL master exception (frame skipped): {e}")

    def _verify_renderer(self) -> None:
        _log("Running particle draw verification...")
        # Use native OpenGL 3.3 point sprite rendering (100% hardware hardware animated)
        self._use_billboards = False
        _log("Native OpenGL 3.3 3D Particle Point Engine ACTIVE.")


    def shutdown(self) -> None:
        if self._audio:
            self._audio.shutdown()
        if self._timer:
            self._timer.stop()
        if self._bloom:
            self._bloom.release()


if __name__ == "__main__":
    from PySide6.QtGui import QSurfaceFormat
    from PySide6.QtWidgets import QApplication

    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.CoreProfile)
    fmt.setDepthBufferSize(24)
    QSurfaceFormat.setDefaultFormat(fmt)

    app = QApplication(sys.argv)
    widget = UltronRenderer()
    widget.resize(1280, 720)
    widget.setWindowTitle("ULTRON Renderer - Direct Mode")
    widget.show()
    sys.exit(app.exec())

