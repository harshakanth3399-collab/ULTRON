"""Multi-pass HDR bloom post-processing."""

from __future__ import annotations

import moderngl
import numpy as np

from graphics.constants import BLOOM_BLUR_PASSES, BLOOM_DOWNSAMPLE, BLOOM_INTENSITY, BLOOM_THRESHOLD
from graphics.shaders import BLUR_FRAG, BLOOM_EXTRACT_FRAG, COMPOSITE_FRAG, FULLSCREEN_VERT


class BloomPass:
    """Extracts bright regions, blurs, and composites back onto the scene."""

    __slots__ = (
        "ctx",
        "width",
        "height",
        "extract_fbo",
        "blur_fbo",
        "ping",
        "pong",
        "extract_prog",
        "blur_prog",
        "composite_prog",
        "_quad",
        "_extract_vao",
        "_blur_vao",
        "_composite_vao",
        "supports_geom",
    )

    def __init__(self, ctx: moderngl.Context, width: int, height: int) -> None:
        self.ctx = ctx
        self.width = max(width, 1)
        self.height = max(height, 1)
        self.supports_geom = False

        self.extract_prog = ctx.program(
            vertex_shader=FULLSCREEN_VERT,
            fragment_shader=BLOOM_EXTRACT_FRAG,
        )
        self.blur_prog = ctx.program(
            vertex_shader=FULLSCREEN_VERT,
            fragment_shader=BLUR_FRAG,
        )
        self.composite_prog = ctx.program(
            vertex_shader=FULLSCREEN_VERT,
            fragment_shader=COMPOSITE_FRAG,
        )

        # fullscreen quad uvs (triangle strip)
        quad_uvs = np.array([
            [0.0, 0.0],
            [1.0, 0.0],
            [0.0, 1.0],
            [1.0, 1.0],
        ], dtype="f4")

        self._quad = ctx.buffer(quad_uvs.tobytes())
        # Create dedicated VAOs for each program once (reuse)
        self._extract_vao = ctx.simple_vertex_array(self.extract_prog, self._quad, "in_uv")
        self._blur_vao = ctx.simple_vertex_array(self.blur_prog, self._quad, "in_uv")
        self._composite_vao = ctx.simple_vertex_array(self.composite_prog, self._quad, "in_uv")

        self._build_targets()

    def _bloom_size(self) -> tuple[int, int]:
        return (
            max(self.width // BLOOM_DOWNSAMPLE, 1),
            max(self.height // BLOOM_DOWNSAMPLE, 1),
        )

    def _build_targets(self) -> None:
        bw, bh = self._bloom_size()
        components = 4
        self.extract_fbo = self.ctx.framebuffer(
            color_attachments=[self.ctx.texture((bw, bh), components, dtype="f4")]
        )
        self.ping = self.ctx.framebuffer(
            color_attachments=[self.ctx.texture((bw, bh), components, dtype="f4")]
        )
        self.pong = self.ctx.framebuffer(
            color_attachments=[self.ctx.texture((bw, bh), components, dtype="f4")]
        )
        self.blur_fbo = self.ping

    def resize(self, width: int, height: int) -> None:
        self.width = max(width, 1)
        self.height = max(height, 1)
        for fbo in (self.extract_fbo, self.ping, self.pong):
            for tex in fbo.color_attachments:
                tex.release()
            fbo.release()
        self._build_targets()

    def apply(self, scene_texture: moderngl.Texture, dest_fbo: moderngl.Framebuffer) -> None:
        bw, bh = self._bloom_size()
        knee = 0.25

        # Extract bright pixels
        self.extract_fbo.use()
        self.ctx.viewport = (0, 0, bw, bh)
        scene_texture.use(location=0)
        self.extract_prog["u_source"] = 0
        self.extract_prog["u_threshold"] = BLOOM_THRESHOLD
        self.extract_prog["u_knee"] = knee
        self._extract_vao.render(moderngl.TRIANGLE_STRIP)

        # Separable gaussian blur
        src = self.extract_fbo.color_attachments[0]
        texel = (1.0 / bw, 1.0 / bh)

        for i in range(BLOOM_BLUR_PASSES):
            scale = 1.0 + i * 0.5
            self.ping.use()
            src.use(location=0)
            self.blur_prog["u_source"] = 0
            self.blur_prog["u_direction"] = (scale, 0.0)
            self.blur_prog["u_texel"] = texel
            self._blur_vao.render(moderngl.TRIANGLE_STRIP)

            self.pong.use()
            self.ping.color_attachments[0].use(location=0)
            self.blur_prog["u_source"] = 0
            self.blur_prog["u_direction"] = (0.0, scale)
            self.blur_prog["u_texel"] = texel
            self._blur_vao.render(moderngl.TRIANGLE_STRIP)

            src = self.pong.color_attachments[0]

        # Composite to destination
        dest_fbo.use()
        self.ctx.viewport = (0, 0, self.width, self.height)
        scene_texture.use(location=0)
        src.use(location=1)
        self.composite_prog["u_scene"] = 0
        self.composite_prog["u_bloom"] = 1
        self.composite_prog["u_bloom_intensity"] = BLOOM_INTENSITY
        self._composite_vao.render(moderngl.TRIANGLE_STRIP)

    def release(self) -> None:
        for fbo in (self.extract_fbo, self.ping, self.pong):
            for tex in fbo.color_attachments:
                tex.release()
            fbo.release()
