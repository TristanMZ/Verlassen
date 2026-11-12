"""
entities/player.py
==================
Player entity for Verlassen — Ren Calloway.

Handles:
  - Four-directional movement with sneak / walk / run speeds
  - Noise level tracking
  - Tile-map collision resolution
  - Hiding / exposure
  - Catch handling with event-bus integration
  - Debug visualisation (noise radius, facing arrow)
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from config import (
    SPRITE_SCALE,
    TILE_SIZE,
    SNEAK_SPEED,
    WALK_SPEED,
    RUN_SPEED,
    NOISE_STILL,
    NOISE_SNEAK,
    NOISE_WALK,
    NOISE_RUN,
    STARTING_SAVINGS,
)
from core.event_bus import EventBus
from core.input_handler import InputHandler, Action
from entities.base_entity import BaseEntity

# Optional config flag — guard with getattr so it's safely absent.
try:
    from config import DEBUG_NOISE  # type: ignore[attr-defined]
except ImportError:
    DEBUG_NOISE = False

if TYPE_CHECKING:
    from core.camera import Camera


# Scaled sprite size: SPRITE_SCALE × 32 px
_SPRITE_PX = SPRITE_SCALE * 32


class Player(BaseEntity):
    """
    Ren Calloway — the player-controlled character.

    Movement is driven by InputHandler each frame.  Collision against
    solid tiles is resolved axis-by-axis (horizontal then vertical) to
    avoid corner trapping.

    Attributes
    ----------
    movement_state : str
        One of ``"still"``, ``"sneaking"``, ``"walking"``, ``"running"``,
        ``"hiding"``.
    facing_angle : float
        Direction the player last moved, in degrees (0 = right, CCW +).
    noise_level : int
        Current NOISE_* constant; consumed by NPC stimulus system.
    is_hidden : bool
        True while inside a hiding spot.
    savings : float
        Ren's on-hand money; may be docked when caught.
    caught : bool
        Set to True by get_caught(); game-over condition.
    health : int
        Hit-points; no regeneration by design.
    """

    def __init__(self, pos: list[float]) -> None:
        """
        Initialise the player at world position *pos*.

        Parameters
        ----------
        pos:
            Starting [x, y] world position (top-left of sprite).
        """
        size = (_SPRITE_PX, _SPRITE_PX)
        super().__init__(pos, size)

        # Blue placeholder sprite for Ren.
        self._placeholder_color = (30, 100, 220)
        self.sprite: pygame.Surface | None = None  # no asset yet

        # -- Movement state ------------------------------------------
        self.movement_state: str = "still"
        self.facing_angle: float = 0.0        # degrees; 0 = right
        self._velocity: list[float] = [0.0, 0.0]  # px/sec this frame

        # -- Stealth stats -------------------------------------------
        self.noise_level: int = NOISE_STILL
        self.is_hidden: bool = False
        self._hiding_spot = None               # reference to Interactable

        # -- Character stats -----------------------------------------
        self.savings: float = float(STARTING_SAVINGS)
        self.health: int = 3
        self.caught: bool = False

        # Grab singletons once; they don't change.
        self._input = InputHandler.get()
        self._bus = EventBus.get()

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float, tile_map=None) -> None:  # type: ignore[override]
        """
        Advance player state by one fixed tick.

        Parameters
        ----------
        dt:
            Delta-time in seconds.
        tile_map:
            Level tile-map object exposing ``is_solid(tx, ty) -> bool``
            and ``width`` / ``height`` attributes (in tiles).  When None,
            no collision or bounds-clamping is performed (useful in tests).
        """
        if not self.active or self.caught:
            return

        # While hidden, player cannot move.
        if self.is_hidden:
            self.movement_state = "hiding"
            self.noise_level = NOISE_STILL
            self._velocity = [0.0, 0.0]
            return

        # ---- Build velocity from input -----------------------------
        dx, dy = 0.0, 0.0
        inp = self._input

        if inp.is_held(Action.MOVE_LEFT):
            dx -= 1.0
        if inp.is_held(Action.MOVE_RIGHT):
            dx += 1.0
        if inp.is_held(Action.MOVE_UP):
            dy -= 1.0
        if inp.is_held(Action.MOVE_DOWN):
            dy += 1.0

        moving = (dx != 0.0 or dy != 0.0)

        # Normalise diagonal movement so it doesn't exceed 1.0 magnitude.
        if moving:
            length = math.hypot(dx, dy)
            dx /= length
            dy /= length

        # Determine speed and noise level.
        if not moving:
            speed = 0.0
            self.noise_level = NOISE_STILL
            self.movement_state = "still"
        elif inp.is_held(Action.SNEAK):
            speed = SNEAK_SPEED
            self.noise_level = NOISE_SNEAK
            self.movement_state = "sneaking"
        elif inp.is_held(Action.RUN):
            speed = RUN_SPEED
            self.noise_level = NOISE_RUN
            self.movement_state = "running"
        else:
            speed = WALK_SPEED
            self.noise_level = NOISE_WALK
            self.movement_state = "walking"

        self._velocity = [dx * speed, dy * speed]

        # Update facing angle from last non-zero velocity.
        if moving:
            self.facing_angle = math.degrees(math.atan2(-dy, dx))  # pygame y-down

        # ---- Integrate position ------------------------------------
        new_x = self.pos[0] + self._velocity[0] * dt
        new_y = self.pos[1] + self._velocity[1] * dt

        # ---- Tile collision (axis-separated) -----------------------
        if tile_map is not None:
            new_x, new_y = self._resolve_tile_collision(new_x, new_y, tile_map)

        self.pos[0] = new_x
        self.pos[1] = new_y

        # ---- Level bounds clamp ------------------------------------
        if tile_map is not None:
            level_w = tile_map.width * TILE_SIZE
            level_h = tile_map.height * TILE_SIZE
            self.pos[0] = max(0.0, min(self.pos[0], level_w - self.size[0]))
            self.pos[1] = max(0.0, min(self.pos[1], level_h - self.size[1]))

        # Emit noise so NPCs can react (every frame; NPC rate-limits itself).
        if self.noise_level > NOISE_STILL:
            self._bus.emit("noise_emitted", {
                "pos": tuple(self.center),
                "level": self.noise_level,
                "source": "player",
            })

    # ------------------------------------------------------------------
    # Tile collision helper
    # ------------------------------------------------------------------

    def _resolve_tile_collision(
        self, new_x: float, new_y: float, tile_map
    ) -> tuple[float, float]:
        """
        Axis-separated tile collision resolution.

        First moves horizontally and resolves, then vertically.  This
        prevents the player from getting stuck on corners.

        Parameters
        ----------
        new_x, new_y:
            Proposed new position before collision.
        tile_map:
            Exposes ``is_solid(tx: int, ty: int) -> bool``.

        Returns
        -------
        tuple[float, float]
            Collision-resolved (x, y) position.
        """
        w, h = self.size

        # -- Horizontal pass -----------------------------------------
        test_rect_h = pygame.Rect(int(new_x), int(self.pos[1]), w, h)
        if self._rect_hits_solid(test_rect_h, tile_map):
            # Push back to original x.
            new_x = self.pos[0]

        # -- Vertical pass -------------------------------------------
        test_rect_v = pygame.Rect(int(new_x), int(new_y), w, h)
        if self._rect_hits_solid(test_rect_v, tile_map):
            new_y = self.pos[1]

        return new_x, new_y

    @staticmethod
    def _rect_hits_solid(rect: pygame.Rect, tile_map) -> bool:
        """
        Return True if *rect* overlaps any solid tile.

        Checks all four corners (and potentially mid-edges for large
        sprites) against the tile map.
        """
        # Sample the four corners of the rect.
        corners = [
            (rect.left, rect.top),
            (rect.right - 1, rect.top),
            (rect.left, rect.bottom - 1),
            (rect.right - 1, rect.bottom - 1),
        ]
        for px, py in corners:
            tx = px // TILE_SIZE
            ty = py // TILE_SIZE
            if tile_map.is_solid(tx, ty):
                return True
        return False

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def try_hide(self, spot) -> bool:
        """
        Attempt to hide inside *spot* (an Interactable hiding_spot).

        Only succeeds when the player is physically near the spot.
        Emits ``"player_hidden"`` on success.

        Parameters
        ----------
        spot:
            An ``Interactable`` with ``interactable_type == "hiding_spot"``.

        Returns
        -------
        bool
            True if the player successfully entered hiding.
        """
        if self.is_hidden:
            return False  # already hidden

        # Proximity check (spot handles range, but double-check here).
        cx, cy = self.center
        if not spot.is_in_range((cx, cy)):
            return False

        self.is_hidden = True
        self._hiding_spot = spot
        self.movement_state = "hiding"
        self.noise_level = NOISE_STILL

        # Snap player pos to the hiding spot centre so overlap looks right.
        self.pos[0] = spot.pos[0] + (spot.size[0] - self.size[0]) / 2
        self.pos[1] = spot.pos[1] + (spot.size[1] - self.size[1]) / 2

        self._bus.emit("player_hidden", {"spot_pos": tuple(spot.center)})
        return True

    def expose(self) -> None:
        """
        Leave the current hiding spot.

        Emits ``"player_exposed"``.
        """
        if not self.is_hidden:
            return
        self.is_hidden = False
        self._hiding_spot = None
        self.movement_state = "still"
        self._bus.emit("player_exposed", {"pos": tuple(self.center)})

    def get_caught(self) -> None:
        """
        Handle the player being caught by an enemy.

        Docks savings, sets ``caught = True``, and emits
        ``"player_caught"`` for the scene manager to show game-over.
        """
        if self.caught:
            return  # idempotent

        # Penalty: lose 20 % of current savings (story consequence).
        penalty = self.savings * 0.20
        self.savings = max(0.0, self.savings - penalty)

        self.caught = True
        self.movement_state = "still"
        self._bus.emit("player_caught", {
            "pos": tuple(self.center),
            "savings_lost": penalty,
            "savings_remaining": self.savings,
        })

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface, camera: "Camera") -> None:
        """
        Draw the player sprite (or placeholder) and optional debug rings.

        Parameters
        ----------
        surface:
            Logical render target.
        camera:
            Provides world_to_screen().
        """
        if not self.visible or not self.active:
            return

        screen_pos = camera.world_to_screen(self.pos)

        if self.sprite is not None:
            surface.blit(self.sprite, screen_pos)
        else:
            # Build placeholder: blue rect with a small white direction pip.
            ph = self.get_placeholder_surface(self._placeholder_color, self.size)

            # Direction indicator pip — small white square near the edge.
            pip_size = max(4, self.size[0] // 8)
            cx = self.size[0] // 2
            cy = self.size[1] // 2
            angle_rad = math.radians(self.facing_angle)
            pip_x = int(cx + math.cos(angle_rad) * (cx - pip_size)) - pip_size // 2
            pip_y = int(cy - math.sin(angle_rad) * (cy - pip_size)) - pip_size // 2  # y-down
            pygame.draw.rect(ph, (255, 255, 255), (pip_x, pip_y, pip_size, pip_size))

            surface.blit(ph, screen_pos)

        # -- Debug: noise radius circle ------------------------------
        if DEBUG_NOISE and self.noise_level > NOISE_STILL:
            # Radius in pixels grows with noise level.
            noise_px = {
                NOISE_SNEAK: 40,
                NOISE_WALK: 90,
                NOISE_RUN: 160,
            }.get(self.noise_level, 40)

            # Draw onto a temporary alpha surface and blit.
            screen_cx = screen_pos[0] + self.size[0] // 2
            screen_cy = screen_pos[1] + self.size[1] // 2
            ring_surf = pygame.Surface(
                (noise_px * 2 + 2, noise_px * 2 + 2), pygame.SRCALPHA
            )
            ring_surf.fill((0, 0, 0, 0))
            pygame.draw.circle(
                ring_surf, (0, 220, 80, 60),
                (noise_px + 1, noise_px + 1), noise_px
            )
            pygame.draw.circle(
                ring_surf, (0, 220, 80, 160),
                (noise_px + 1, noise_px + 1), noise_px, 1
            )
            surface.blit(ring_surf, (screen_cx - noise_px - 1, screen_cy - noise_px - 1))
