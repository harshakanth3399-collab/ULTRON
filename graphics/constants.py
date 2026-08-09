"""Graphics pipeline constants and tunables."""

# ── Particles ────────────────────────────────────────────────────────────
# 6000 particles — optimal for Intel Iris Xe (150k caused VBO shape crash)
PARTICLE_COUNT = 6_000
SPHERE_RADIUS = 0.38
PARTICLE_MIN_SIZE = 1.2
PARTICLE_MAX_SIZE = 2.8

# ── Electric arcs ──────────────────────────────────────────────────────────
ARC_COUNT = 14
ARC_SEGMENTS = 32
ARC_MAX_LENGTH = 0.55

# ── Framebuffer / bloom ─────────────────────────────────────────────────────
BLOOM_THRESHOLD = 0.75
BLOOM_INTENSITY = 0.35
BLOOM_BLUR_PASSES = 2
BLOOM_DOWNSAMPLE = 2

# ── Audio smoothing ─────────────────────────────────────────────────────────
AUDIO_ATTACK = 0.42
AUDIO_RELEASE = 0.08
AUDIO_GAIN = 2.8

# ── Palette (linear RGB - MCU J.A.R.V.I.S. Amber Gold Matrix) ───────────────
COLOR_CORE = (1.0, 0.65, 0.12)     # Radiant Amber Gold Core
COLOR_GLOW = (1.0, 0.42, 0.05)     # Fiery Copper Orange Glow
COLOR_ARC = (1.0, 0.78, 0.22)      # Glowing Electric Gold Filaments
COLOR_DEEP = (0.25, 0.06, 0.01)    # Deep Amber Space Shadow

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
    # All remaining states map to one of the above
    "recording":     None,  # resolved below
    "transcribing":  None,
    "understanding": None,
    "processing":    None,
    "wake_detected": None,
    "greeting":      None,
    "error":         None,
}
# Fill alias states
STATE_CONFIG["recording"]     = STATE_CONFIG["listening"]
STATE_CONFIG["transcribing"]  = STATE_CONFIG["idle"]
STATE_CONFIG["understanding"] = STATE_CONFIG["idle"]
STATE_CONFIG["processing"]    = STATE_CONFIG["idle"]
STATE_CONFIG["wake_detected"] = STATE_CONFIG["speaking"]
STATE_CONFIG["greeting"]      = STATE_CONFIG["speaking"]
STATE_CONFIG["error"]         = STATE_CONFIG["idle"]


# ── Mic button (normalized screen coords) ───────────────────────────────────
MIC_BUTTON_RADIUS = 36
MIC_BUTTON_Y_OFFSET = 90

# ── Target frame rate ───────────────────────────────────────────────────────
TARGET_FPS = 60
FRAME_MS = 1000 // TARGET_FPS
