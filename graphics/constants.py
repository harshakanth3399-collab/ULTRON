"""Graphics pipeline constants and tunables."""

# ── Particles ────────────────────────────────────────────────────────────
# 8,000 crisp, laser-like holographic particles (compact, elegant density — NO solid white blob)
PARTICLE_COUNT = 8_000
SPHERE_RADIUS  = 0.24
PARTICLE_MIN_SIZE = 1.0
PARTICLE_MAX_SIZE = 2.4

# ── Electric arcs ──────────────────────────────────────────────────────────
ARC_COUNT = 10
ARC_SEGMENTS = 24
ARC_MAX_LENGTH = 0.35

# ── Framebuffer / bloom ─────────────────────────────────────────────────────
BLOOM_THRESHOLD = 0.80
BLOOM_INTENSITY = 0.25
BLOOM_BLUR_PASSES = 2
BLOOM_DOWNSAMPLE = 2

# ── Audio smoothing ─────────────────────────────────────────────────────────
AUDIO_ATTACK = 0.42
AUDIO_RELEASE = 0.08
AUDIO_GAIN = 2.8

# ── Palette (ULTRON Warm Amber / Cyber Cyan Holographic HUD) ───────────────
COLOR_CORE = (0.91, 0.39, 0.04)     # Warm Amber Core (#E8630A)
COLOR_GLOW = (0.00, 0.80, 1.00)     # Cyber Cyan Glow (#00C8FF)
COLOR_ARC  = (1.00, 0.55, 0.10)     # Golden Arc Filaments (#FF8C1A)
COLOR_DEEP = (0.12, 0.04, 0.01)     # Quantum Void Shadow




# ── State multipliers ───────────────────────────────────────────────────────
STATE_CONFIG = {
    "idle": {
        "pulse_speed": 1.25,
        "pulse_amp": 0.035,
        "turbulence": 1.45,
        "glow": 0.85,
        "arc_activity": 0.45,
        "rotation": 0.45,
        "audio_influence": 0.25,
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
