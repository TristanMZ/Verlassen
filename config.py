"""
config.py — Global constants and tunable parameters for Verlassen.

All game-wide settings live here so other modules import a single source of
truth rather than hard-coding magic numbers.
"""

# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------
PLAYER_NAME: str = "Ren Calloway"

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
INTERNAL_W: int = 1280   # Logical render width  (px)
INTERNAL_H: int = 720    # Logical render height (px)
WINDOW_W:   int = 2560   # Physical window width  (px) — 1440p
WINDOW_H:   int = 1440   # Physical window height (px)
SCALE:      int = 2      # Integer upscale factor (INTERNAL → WINDOW)

# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------
FPS: int = 60  # Target / fixed-step tick rate

# ---------------------------------------------------------------------------
# Tiles & Sprites
# ---------------------------------------------------------------------------
TILE_SIZE:    int = 32  # World tile size (logical px)
SPRITE_SCALE: int = 3   # Raw 32-px sprites are drawn at 32*3 = 96 px

# ---------------------------------------------------------------------------
# Player speeds (logical pixels per second)
# ---------------------------------------------------------------------------
SNEAK_SPEED: int = 60    # Crouched movement
WALK_SPEED:  int = 120   # Normal walk
RUN_SPEED:   int = 200   # Sprint

# ---------------------------------------------------------------------------
# Noise levels (ordinal scale, compared by NPC hearing)
# ---------------------------------------------------------------------------
NOISE_STILL:  int = 0   # Standing still / holding breath
NOISE_SNEAK:  int = 1   # Sneaking
NOISE_WALK:   int = 2   # Walking normally
NOISE_RUN:    int = 3   # Running
NOISE_CREAK:  int = 4   # Stepping on a creaky surface

# ---------------------------------------------------------------------------
# NPC Vision & Alertness
# ---------------------------------------------------------------------------
NPC_VISION_RANGE:    int   = 200   # How far an NPC can see (logical px)
NPC_FOV_DEGREES:     int   = 90    # Half-angle of vision cone (degrees)
NPC_SUSPICION_RATE:  float = 1.5   # Suspicion gained per second inside cone
NPC_SUSPICION_DECAY: float = 0.5   # Suspicion lost per second outside cone
NPC_ALERT_THRESHOLD: float = 3.0   # Suspicion level → "Alert" state
NPC_CONFIRM_THRESHOLD: float = 5.0 # Suspicion level → "Caught" state
NPC_SEARCH_DURATION: float = 8.0   # Seconds an NPC searches after losing player

# ---------------------------------------------------------------------------
# Lighting
# ---------------------------------------------------------------------------
AMBIENT_DARKNESS: int = 180  # Alpha of the dark overlay (0 = transparent, 255 = black)

# ---------------------------------------------------------------------------
# Puzzle
# ---------------------------------------------------------------------------
KEYPAD_CODE_LENGTH: int = 4  # Digits in a keypad code

# ---------------------------------------------------------------------------
# Economy
# ---------------------------------------------------------------------------
STARTING_SAVINGS: int = 340  # USD Ren managed to save before the story begins

# ---------------------------------------------------------------------------
# Asset paths (all relative to the Verlassen/ project root)
# ---------------------------------------------------------------------------
ASSETS_DIR:    str = "assets"
SAVE_DIR:      str = "saves"
LEVELS_DIR:    str = "levels"
STORY_DIR:     str = "story"

# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------
DATA_ENCODING: str = "utf-8"  # Encoding for JSON / text files
