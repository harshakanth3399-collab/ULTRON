"""Graphics pipeline constants and tunables."""

# ── Particles ────────────────────────────────────────────────────────────
# 6,500 MCU J.A.R.V.I.S. neural matrix particles — compact dense golden sphere
PARTICLE_COUNT = 6500
SPHERE_RADIUS  = 1.0       # Exact Three.js world radius
PARTICLE_MIN_SIZE = 1.5    # Delicate glowing neural specks
PARTICLE_MAX_SIZE = 3.0    # Tight and dense, not scattered stars

# ── Electric arcs / Halos ──────────────────────────────────────────────────
ARC_COUNT = 6
ARC_SEGMENTS = 32
ARC_MAX_LENGTH = 0.38

# ── Framebuffer / bloom ─────────────────────────────────────────────────────
BLOOM_THRESHOLD = 0.70
BLOOM_INTENSITY = 0.22     # Crisp cinematic glow
BLOOM_BLUR_PASSES = 2      # Fast 2-pass gaussian blur
BLOOM_DOWNSAMPLE = 2

# ── Audio smoothing ─────────────────────────────────────────────────────────
AUDIO_ATTACK = 0.42
AUDIO_RELEASE = 0.08
AUDIO_GAIN = 2.8

# ── Palette (MCU J.A.R.V.I.S. Signature Gold & Amber Palette) ──────────────
COLOR_CORE = (1.00, 0.84, 0.15)     # Incandescent Gold (#FFD700)
COLOR_GLOW = (1.00, 0.45, 0.02)     # Radiant Amber Orange (#FF7300)
COLOR_ARC  = (1.00, 0.65, 0.08)     # Golden Sunfire
COLOR_DEEP = (0.02, 0.01, 0.00)     # Matte Obsidian Black

# ── Dynamic Cinema Hologram State Palettes (MCU J.A.R.V.I.S. Gold & Amber) ──
STATE_PALETTES = {
    "idle": {
        "core": (1.00, 0.84, 0.15),   # Incandescent Gold (#FFD700)
        "glow": (1.00, 0.45, 0.02),   # Radiant Amber Orange (#FF7300)
        "arc":  (1.00, 0.65, 0.08),   # Golden Sunfire
    },
    "listening": {
        "core": (1.00, 0.92, 0.35),   # Luminous White-Gold
        "glow": (1.00, 0.55, 0.05),   # Vibrant Amber Halo
        "arc":  (1.00, 0.75, 0.12),   # High-Energy Gold
    },
    "speaking": {
        "core": (1.00, 0.96, 0.55),   # Incandescent Blazing Gold
        "glow": (1.00, 0.38, 0.00),   # Deep Molten Flame
        "arc":  (1.00, 0.70, 0.10),   # Harmonic Gold Waves
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
