"""Graphics pipeline constants and tunables."""

# ── Particles ────────────────────────────────────────────────────────────
# Volumetric Google Gemini Aurora Liquid Orb (soft fluid light blobs that merge seamlessly)
PARTICLE_COUNT = 3_200
SPHERE_RADIUS  = 0.28
PARTICLE_MIN_SIZE = 14.0
PARTICLE_MAX_SIZE = 36.0

# ── Electric arcs / Halos ──────────────────────────────────────────────────
ARC_COUNT = 6
ARC_SEGMENTS = 32
ARC_MAX_LENGTH = 0.38

# ── Framebuffer / bloom ─────────────────────────────────────────────────────
BLOOM_THRESHOLD = 0.70
BLOOM_INTENSITY = 0.40
BLOOM_BLUR_PASSES = 3
BLOOM_DOWNSAMPLE = 2

# ── Audio smoothing ─────────────────────────────────────────────────────────
AUDIO_ATTACK = 0.42
AUDIO_RELEASE = 0.08
AUDIO_GAIN = 2.8

# ── Palette (Google Gemini Signature Holographic Colors) ───────────────────
COLOR_CORE = (0.00, 0.88, 1.00)     # Luminous Electric Cyan (#00E0FF)
COLOR_GLOW = (0.58, 0.20, 0.98)     # Celestial Gemini Violet (#9433FA)
COLOR_ARC  = (0.20, 0.70, 1.00)     # Ethereal Azure Stream
COLOR_DEEP = (0.04, 0.02, 0.12)     # Deep Celestial Void

# ── Dynamic Cinema Hologram State Palettes (Google Gemini AI Aesthetic) ──
STATE_PALETTES = {
    "idle": {
        "core": (0.00, 0.88, 1.00),   # Vibrant Electric Cyan (#00E0FF)
        "glow": (0.58, 0.20, 0.98),   # Celestial Gemini Violet (#9433FA)
        "arc":  (0.20, 0.70, 1.00),   # Ethereal Azure Stream
    },
    "listening": {
        "core": (0.00, 1.00, 0.82),   # Turquoise Luminous Cyan
        "glow": (0.15, 0.75, 1.00),   # Deep Sky Blue Aura
        "arc":  (0.40, 1.00, 0.85),   # Radiant Cyan Halo
    },
    "speaking": {
        "core": (1.00, 0.18, 0.65),   # Glowing Magenta / Fuchsia
        "glow": (1.00, 0.62, 0.10),   # Luminous Golden Amber
        "arc":  (0.75, 0.25, 0.95),   # Violet Harmonic Waves
    },
}




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
