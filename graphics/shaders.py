"""GLSL shader sources for the ULTRON holographic renderer."""

FULLSCREEN_VERT = """
#version 330 core

layout(location = 0) in vec2 in_uv;
out vec2 v_uv;

void main() {
    v_uv = in_uv;
    gl_Position = vec4(in_uv * 2.0 - 1.0, 0.0, 1.0);
}
"""

PARTICLE_VERT = """
#version 330 core

layout(location = 0) in vec3 in_pos;
layout(location = 1) in float in_size;
layout(location = 2) in float in_brightness;

uniform mat4 u_mvp;
uniform float u_time;
uniform float u_glow;

out float v_brightness;
out float v_depth;
out float v_phase;

void main() {
    vec4 clip = u_mvp * vec4(in_pos, 1.0);
    gl_Position = clip;

    // Perspective attenuation: sharp 3D point scaling for crisp holographic stars (no pixel boxes!)
    float atten = 1.0 / max(clip.w, 0.08);
    gl_PointSize = clamp(in_size * atten * 4.5 * (1.0 + u_glow * 0.35), 1.5, 20.0);

    v_brightness = in_brightness * (0.85 + u_glow * 0.4);
    v_depth = clip.z;
    v_phase = fract(sin(dot(in_pos, vec3(12.9898, 78.233, 45.5432))) * 43758.5453);
}
"""

PARTICLE_FRAG = """
#version 330 core

in float v_brightness;
in float v_depth;
in float v_phase;

uniform vec3 u_color_core;
uniform vec3 u_color_glow;
uniform float u_time;

out vec4 frag_color;

void main() {
    vec2 uv = gl_PointCoord - 0.5;
    float dist = length(uv);

    // CRITICAL FIX: Cut off square quad corners so particles are 100% perfectly round glowing spheres, NOT pixel boxes!
    if (dist > 0.5) {
        discard;
    }

    // High-frequency stroboscopic scintillation twinkling
    float blink = 0.75 + 0.35 * sin(u_time * 24.0 + v_phase * 62.83);

    // Smooth radial gaussian energy core
    float core = exp(-dist * dist * 24.0);
    float halo = max(0.0, 0.5 - dist) * 1.8;
    float intensity = (core * 2.2 + halo) * v_brightness * blink;

    vec3 col = mix(u_color_glow, u_color_core, core);
    col *= (1.2 + intensity * 0.8);
    float alpha = clamp((0.5 - dist) * 2.0 * intensity, 0.0, 1.0);

    frag_color = vec4(col * intensity, alpha);
}
"""


ARC_VERT = """
#version 330 core

layout(location = 0) in vec3 in_pos;
layout(location = 1) in float in_width;
layout(location = 2) in float in_intensity;

uniform mat4 u_mvp;

out float v_intensity;
out float v_width;

void main() {
    gl_Position = u_mvp * vec4(in_pos, 1.0);
    v_intensity = in_intensity;
    v_width = in_width;
}
"""

ARC_GEOM = """
#version 330 core

layout(lines) in;
layout(triangle_strip, max_vertices = 4) out;

in float v_intensity[];
in float v_width[];

out float g_intensity;

uniform vec2 u_viewport;

void main() {
    vec4 p0 = gl_in[0].gl_Position;
    vec4 p1 = gl_in[1].gl_Position;

    vec2 dir = p1.xy / p1.w - p0.xy / p0.w;
    float len = length(dir);
    if (len < 1e-6) {
        return;
    }
    dir /= len;

    vec2 normal = vec2(-dir.y, dir.x);
    float half_w = (v_width[0] + v_width[1]) * 0.5;
    vec2 offset = normal * half_w / u_viewport * 2.0;

    float intensity = (v_intensity[0] + v_intensity[1]) * 0.5;
    g_intensity = intensity;

    gl_Position = vec4(p0.xy / p0.w + offset * p0.w, p0.z / p0.w, p0.w);
    EmitVertex();

    gl_Position = vec4(p0.xy / p0.w - offset * p0.w, p0.z / p0.w, p0.w);
    EmitVertex();

    gl_Position = vec4(p1.xy / p1.w + offset * p1.w, p1.z / p1.w, p1.w);
    EmitVertex();

    gl_Position = vec4(p1.xy / p1.w - offset * p1.w, p1.z / p1.w, p1.w);
    EmitVertex();

    EndPrimitive();
}
"""

ARC_FRAG = """
#version 330 core

in float g_intensity;

uniform vec3 u_color_arc;
uniform float u_time;

out vec4 frag_color;

void main() {
    float flicker = 0.75 + 0.25 * sin(u_time * 42.0 + g_intensity * 17.0);
    float intensity = g_intensity * flicker;
    vec3 col = u_color_arc * intensity * 2.2;
    float alpha = clamp(intensity * 1.4, 0.0, 1.0);
    frag_color = vec4(col, alpha);
}
"""

BLOOM_EXTRACT_FRAG = """
#version 330 core

in vec2 v_uv;
out vec4 frag_color;

uniform sampler2D u_source;
uniform float u_threshold;
uniform float u_knee;

void main() {
    vec3 color = texture(u_source, v_uv).rgb;
    float brightness = max(color.r, max(color.g, color.b));
    float soft = brightness - u_threshold + u_knee;
    soft = clamp(soft, 0.0, 2.0 * u_knee);
    soft = soft * soft / (4.0 * u_knee + 1e-6);
    float contribution = max(soft, brightness - u_threshold);
    contribution = max(contribution, 0.0);
    frag_color = vec4(color * contribution, 1.0);
}
"""

BLUR_FRAG = """
#version 330 core

in vec2 v_uv;
out vec4 frag_color;

uniform sampler2D u_source;
uniform vec2 u_direction;
uniform vec2 u_texel;

void main() {
    vec3 result = vec3(0.0);
    float weights[5] = float[](0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);
    result += texture(u_source, v_uv).rgb * weights[0];
    for (int i = 1; i < 5; ++i) {
        vec2 offset = u_direction * u_texel * float(i);
        result += texture(u_source, v_uv + offset).rgb * weights[i];
        result += texture(u_source, v_uv - offset).rgb * weights[i];
    }
    frag_color = vec4(result, 1.0);
}
"""

COMPOSITE_FRAG = """
#version 330 core

in vec2 v_uv;
out vec4 frag_color;

uniform sampler2D u_scene;
uniform sampler2D u_bloom;
uniform float u_bloom_intensity;

void main() {
    vec3 scene = texture(u_scene, v_uv).rgb;
    vec3 bloom = texture(u_bloom, v_uv).rgb;
    vec3 color = scene + bloom * u_bloom_intensity;
    color = color / (color + vec3(1.0));
    color = pow(color, vec3(1.0 / 2.2));
    frag_color = vec4(color, 1.0);
}
"""

SPHERE_GLOW_VERT = """
#version 330 core

layout(location = 0) in vec2 in_uv;

uniform mat4 u_mvp;
uniform float u_radius;
uniform float u_time;
uniform float u_intensity;

out vec2 v_uv;
out float v_intensity;

void main() {
    v_uv = in_uv;
    vec3 pos = vec3(in_uv * u_radius * 2.2, 0.0);
    float pulse = sin(u_time * 1.8) * 0.04 + sin(u_time * 3.7) * 0.02;
    pos.xy *= 1.0 + pulse * u_intensity;
    gl_Position = u_mvp * vec4(pos, 1.0);
    v_intensity = u_intensity;
}
"""

SPHERE_GLOW_FRAG = """
#version 330 core

in vec2 v_uv;
in float v_intensity;

uniform vec3 u_color_deep;
uniform float u_time;

out vec4 frag_color;

void main() {
    float dist = length(v_uv - 0.5) * 2.0;
    float core = exp(-dist * dist * 3.5);
    float outer = exp(-dist * 1.8) * 0.35;
    float pulse = 0.85 + 0.15 * sin(u_time * 2.2);
    float alpha = (core * 0.55 + outer) * v_intensity * pulse;
    vec3 col = u_color_deep * (core * 2.0 + outer);
    frag_color = vec4(col, alpha);
}
"""

# Simple debug particle shader: outputs clip position directly and a large white point
DEBUG_PARTICLE_VERT = """
#version 330 core

layout(location = 0) in vec3 in_pos;

uniform mat4 u_mvp;

void main() {
    gl_Position = u_mvp * vec4(in_pos, 1.0);
    gl_PointSize = 40.0;
}
"""

DEBUG_PARTICLE_FRAG = """
#version 330 core

out vec4 frag_color;

void main() {
    frag_color = vec4(1.0, 1.0, 1.0, 1.0);
}
"""

BLIT_FRAG = """
#version 330 core

in vec2 v_uv;
out vec4 frag_color;

uniform sampler2D u_tex;

void main() {
    frag_color = texture(u_tex, v_uv);
}
"""

BILLBOARD_VERT = """
#version 330 core

layout(location = 0) in vec2 in_quad;
layout(location = 1) in vec3 in_pos;
layout(location = 2) in float in_size;
layout(location = 3) in float in_brightness;

uniform mat4 u_mvp;
uniform vec2 u_viewport;
uniform float u_glow;

out float v_brightness;
out vec2 v_uv;

void main() {
    v_uv = in_quad + 0.5;
    vec4 clip_center = u_mvp * vec4(in_pos, 1.0);
    float perspective = clamp(1.8 / max(clip_center.w, 0.05), 0.4, 3.5);
    float size_pixels = in_size * perspective * (1.0 + u_glow * 0.35);
    vec2 offset = (in_quad * size_pixels) / u_viewport * 2.0 * clip_center.w;

    gl_Position = clip_center + vec4(offset, 0.0, 0.0);
    v_brightness = in_brightness * (0.85 + u_glow * 0.4);
}
"""

BILLBOARD_FRAG = """
#version 330 core

in float v_brightness;
in vec2 v_uv;

uniform vec3 u_color_core;
uniform vec3 u_color_glow;

out vec4 frag_color;

void main() {
    vec2 uv = v_uv - 0.5;
    float dist = length(uv);
    float core = exp(-dist * dist * 16.0);
    float halo = exp(-dist * 6.0) * 0.6;
    float intensity = (core * 1.5 + halo) * v_brightness;
    vec3 col = mix(u_color_glow, u_color_core, core);
    col *= (1.0 + intensity * 0.8);
    float alpha = clamp(intensity * 0.9, 0.0, 1.0);
    frag_color = vec4(col * intensity, alpha);
}
"""

