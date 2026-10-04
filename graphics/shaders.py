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

    // Delicate holographic stardust sparks orbiting the fluid core
    float atten = 1.0 / max(clip.w, 0.15);
    gl_PointSize = clamp(in_size * atten * 1.8 * (1.0 + u_glow * 0.25), 1.5, 6.0);

    v_brightness = in_brightness * (0.80 + u_glow * 0.35);
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

    if (dist > 0.5) {
        discard;
    }

    float core = exp(-dist * dist * 16.0);
    float halo = max(0.0, 0.5 - dist) * 1.5;
    float intensity = (core * 2.0 + halo) * v_brightness;
    float shimmer = 0.8 + 0.2 * sin(u_time * 12.0 + v_phase * 62.83);

    vec3 col = mix(u_color_core, u_color_glow, dist * 1.5);
    frag_color = vec4(col * intensity * shimmer, clamp(intensity * 0.9, 0.0, 1.0));
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

    // Protect against camera near-plane division artifacts
    if (p0.w <= 0.05 || p1.w <= 0.05) {
        return;
    }

    vec2 ndc0 = p0.xy / p0.w;
    vec2 ndc1 = p1.xy / p1.w;

    vec2 dir = ndc1 - ndc0;
    float len = length(dir);
    if (len < 1e-5) {
        return;
    }
    dir /= len;

    vec2 normal = vec2(-dir.y, dir.x);
    float half_w = (v_width[0] + v_width[1]) * 0.5;
    vec2 offset = normal * half_w / u_viewport * 2.0;

    float intensity = (v_intensity[0] + v_intensity[1]) * 0.5;
    g_intensity = intensity;

    gl_Position = vec4((ndc0 + offset) * p0.w, p0.z, p0.w);
    EmitVertex();

    gl_Position = vec4((ndc0 - offset) * p0.w, p0.z, p0.w);
    EmitVertex();

    gl_Position = vec4((ndc1 + offset) * p1.w, p1.z, p1.w);
    EmitVertex();

    gl_Position = vec4((ndc1 - offset) * p1.w, p1.z, p1.w);
    EmitVertex();

    EndPrimitive();
}
"""

ARC_FRAG = """
#version 330 core

in float v_intensity;

uniform vec3 u_color_arc;
uniform float u_time;

out vec4 frag_color;

void main() {
    float flicker = 0.75 + 0.25 * sin(u_time * 42.0 + v_intensity * 17.0);
    float intensity = v_intensity * flicker;
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
out vec2 v_uv;

void main() {
    v_uv = in_uv;
    gl_Position = vec4(in_uv, 0.0, 1.0);
}
"""

SPHERE_GLOW_FRAG = """
#version 330 core

in vec2 v_uv;
out vec4 frag_color;

uniform float u_time;
uniform float u_audio;
uniform float u_aspect;
uniform vec3 u_color_core;
uniform vec3 u_color_glow;
uniform vec3 u_color_arc;

// High-speed 3D Simplex noise
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

float snoise(vec3 v) {
    const vec2 C = vec2(1.0/6.0, 1.0/3.0);
    const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
    vec3 i  = floor(v + dot(v, C.yyy));
    vec3 x0 = v - i + dot(i, C.xxx);
    vec3 g = step(x0.yzx, x0.xyz);
    vec3 l = 1.0 - g;
    vec3 i1 = min(g.xyz, l.zxy);
    vec3 i2 = max(g.xyz, l.zxy);
    vec3 x1 = x0 - i1 + C.xxx;
    vec3 x2 = x0 - i2 + C.yyy;
    vec3 x3 = x0 - D.yyy;
    i = mod289(i);
    vec4 p = permute(permute(permute(
              i.z + vec4(0.0, i1.z, i2.z, 1.0))
            + i.y + vec4(0.0, i1.y, i2.y, 1.0))
            + i.x + vec4(0.0, i1.x, i2.x, 1.0));
    float n_ = 0.142857142857;
    vec3 ns = n_ * D.wyz - D.xzx;
    vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
    vec4 x_ = floor(j * ns.z);
    vec4 y_ = floor(j - 7.0 * x_);
    vec4 x = x_ *ns.x + ns.yyyy;
    vec4 y = y_ *ns.x + ns.yyyy;
    vec4 h = 1.0 - abs(x) - abs(y);
    vec4 b0 = vec4(x.xy, y.xy);
    vec4 b1 = vec4(x.zw, y.zw);
    vec4 s0 = floor(b0)*2.0 + 1.0;
    vec4 s1 = floor(b1)*2.0 + 1.0;
    vec4 sh = -step(h, vec4(0.0));
    vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
    vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
    vec3 p0 = vec3(a0.xy, h.x);
    vec3 p1 = vec3(a0.zw, h.y);
    vec3 p2 = vec3(a1.xy, h.z);
    vec3 p3 = vec3(a1.zw, h.w);
    vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
    p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
    vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
    m = m * m;
    return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
}

float fbm(vec3 p) {
    float f = 0.0;
    f += 0.5000 * snoise(p); p *= 2.02;
    f += 0.2500 * snoise(p); p *= 2.03;
    f += 0.1250 * snoise(p); p *= 2.01;
    f += 0.0625 * snoise(p);
    return f;
}

void main() {
    vec2 p = v_uv;
    p.x *= u_aspect;

    // Camera ray
    vec3 ro = vec3(0.0, 0.0, 2.5);
    vec3 rd = normalize(vec3(p, -1.9));

    // Dynamic radius breathing with voice audio
    float base_radius = 0.28 + u_audio * 0.05 + sin(u_time * 1.5) * 0.008;

    float b = dot(ro, rd);
    float c = dot(ro, ro) - base_radius * base_radius;
    float disc = b * b - c;

    vec3 col = vec3(0.0);
    float alpha = 0.0;

    // Atmospheric coronal glow around sphere
    float d_center = length(p);
    float corona_dist = max(0.0, d_center - base_radius * 0.80);
    float corona = exp(-corona_dist * corona_dist * 28.0) * (0.35 + u_audio * 0.40);
    vec3 corona_col = mix(u_color_glow, u_color_core, clamp(corona * 1.4, 0.0, 1.0));
    col += corona_col * corona;
    alpha += corona * 0.6;

    if (disc > 0.0) {
        float t = -b - sqrt(disc);
        vec3 hit = ro + t * rd;
        vec3 norm = normalize(hit);

        // Multi-frequency fluid displacement
        float t_flow = u_time * 0.45;
        vec3 noise_coord = norm * 2.5 + vec3(0.0, t_flow, t_flow * 0.5);
        float fluid = fbm(noise_coord);
        float audio_ripple = sin(norm.y * 14.0 - u_time * 5.0 + fluid * 4.0) * (0.04 + u_audio * 0.12);

        // Modulate normal with fluid turbulence
        vec3 displaced_norm = normalize(norm + vec3(fluid * 0.30, fluid * 0.20, audio_ripple));

        // High-end Fresnel rim lighting
        float fresnel = pow(1.0 - max(0.0, dot(norm, -rd)), 2.5);
        float rim_edge = pow(1.0 - max(0.0, dot(norm, -rd)), 4.5);

        // Core soft illumination (saturated, not blown-out white)
        float core_light = pow(max(0.0, dot(norm, vec3(0.0, 0.0, 1.0))), 2.2);

        // Iridescent multi-layer color blending (Gemini Electric Cyan & Celestial Violet)
        float color_t = clamp(fluid * 0.75 + norm.y * 0.35 + fresnel * 0.55, 0.0, 1.0);
        vec3 surface_col = mix(u_color_core, u_color_glow, color_t);
        
        // Chromatic dispersion accent on outer rim
        surface_col = mix(surface_col, u_color_arc, rim_edge * 0.6);

        // Soft internal caustics
        vec3 core_glow = mix(u_color_core * 1.3, u_color_glow * 1.2, 0.5 + 0.5 * sin(u_time * 2.0));
        surface_col = mix(surface_col, core_glow, core_light * (0.35 + u_audio * 0.35));

        // Subtle specular highlight
        vec3 light_dir = normalize(vec3(0.35, 0.55, 1.0));
        vec3 h = normalize(-rd + light_dir);
        float spec = pow(max(0.0, dot(displaced_norm, h)), 32.0);
        surface_col += vec3(spec * 0.45);

        float sphere_alpha = clamp(0.85 + fresnel * 0.15, 0.0, 1.0);
        col = mix(col, surface_col, sphere_alpha);
        alpha = max(alpha, sphere_alpha);
    }

    if (alpha <= 0.005) {
        discard;
    }

    frag_color = vec4(col, clamp(alpha, 0.0, 1.0));
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

