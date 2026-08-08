"""Graphics pipeline constants and tunables."""

# ── Particles ────────────────────────────────────────────────────────────
PARTICLE_COUNT = 150_000
SPHERE_RADIUS = 0.38
PARTICLE_MIN_SIZE = 1.5
PARTICLE_MAX_SIZE = 4.5

# ── Electric arcs ──────────────────────────────────────────────────────────
ARC_COUNT = 14
ARC_SEGMENTS = 32
ARC_MAX_LENGTH = 0.55

# ── Framebuffer / bloom ─────────────────────────────────────────────────────
BLOOM_THRESHOLD = 0.55
BLOOM_INTENSITY = 1.35
BLOOM_BLUR_PASSES = 6
BLOOM_DOWNSAMPLE = 2

# ── Audio smoothing ─────────────────────────────────────────────────────────
AUDIO_ATTACK = 0.42
AUDIO_RELEASE = 0.08
AUDIO_GAIN = 2.8

# ── Palette (linear RGB - J.A.R.V.I.S. Holographic Theme) ─────────────────────
COLOR_CORE = (0.0, 0.85, 1.0)     # Bright Cyan
COLOR_GLOW = (1.0, 0.75, 0.15)    # Jarvis Gold
COLOR_ARC = (0.2, 0.95, 1.0)     # Electric Holographic Cyan
COLOR_DEEP = (0.02, 0.12, 0.35)   # Deep Cosmic Blue

# ── State multipliers ───────────────────────────────────────────────────────
STATE_CONFIG = {
    "idle": {
        "pulse_speed": 0.65,
        "pulse_amp": 0.018,
        "turbulence": 0.85,
        "glow": 0.75,
        "arc_activity": 0.35,
        "rotation": 0.12,
        "audio_influence": 0.15,
    },
    "listening": {
        "pulse_speed": 1.4,
        "pulse_amp": 0.045,
        "turbulence": 1.35,
        "glow": 1.15,
        "arc_activity": 0.75,
        "rotation": 0.22,
        "audio_influence": 1.0,
    },
    "speaking": {
        "pulse_speed": 2.1,
        "pulse_amp": 0.065,
        "turbulence": 1.65,
        "glow": 1.45,
        "arc_activity": 1.0,
        "rotation": 0.35,
        "audio_influence": 0.85,
    },
}

# ── Mic button (normalized screen coords) ───────────────────────────────────
MIC_BUTTON_RADIUS = 36
MIC_BUTTON_Y_OFFSET = 90

# ── Target frame rate ───────────────────────────────────────────────────────
TARGET_FPS = 60
FRAME_MS = 1000 // TARGET_FPS
