"""
entities/enemy.py
=================
Hostile enemy entity for Verlassen.

Extends NPC with two additional alert states:
  - ``"chasing"``   — actively pursuing Ren's last known position
  - ``"searching"`` — wandering around the last known position after losing sight

If the enemy closes within 24 px of Ren it triggers player.get_caught().
Placeholder sprite: 32×32 red rect (scaled).
"""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

import pygame

from config import (
    SPRITE_SCALE,
    NPC_VISION_RANGE,
    NPC_FOV_DEGREES,
    NPC_SUSPICION_RATE,
    NPC_SUSPICION_DECAY,
    NPC_ALERT_THRESHOLD,
    NPC_CONFIRM_THRESHOLD,
    NPC_SEARCH_DURATION,
)
from core.event_bus import EventBus
from entities.npc import NPC

if TYPE_CHECKING:
    from core.camera import Camera
    from entities.player import Player

_SPRITE_PX = SPRITE_SCALE * 32

# Distance in pixels at which the enemy "catches" the player.
_CATCH_DISTANCE: float = 24.0

# Default chase speed (pixels/sec); can be overridden per-instance.
_DEFAULT_CHASE_SPEED: float = 160.0

# How far the enemy wanders from last_known_player_pos while searching.
_SEARCH_WANDER_RADIUS: float = 80.0


class Enemy(NPC):
    """
    Hostile pursuer that chases and catches Ren.

    Inherits NPC vision-cone and suspicion logic, then adds two extra
    FSM states: ``"chasing"`` and ``"searching"``.

    Alert-state progression
    -----------------------
    idle → suspicious → alert → chasing → searching → idle
                                       ↑ (re-spots player while searching)

    Additional Attributes
    ---------------------
    last_known_player_pos : tuple[float, float] | None
        World position where the player was last seen.
    chase_speed : float
        Movement speed in pixels/sec while chasing.
    search_timer : float
        Seconds remaining in the searching state.
    _chase_path : list
        Placeholder for a future A* path; currently a direct vector.
    """

    def __init__(
        self,
        pos: list[float],
        name: str = "Enemy",
        patrol_path: list[tuple[float, float]] | None = None,
        patrol_wait: float = 1.5,
        dialogue_key: str = "",
        chase_speed: float = _DEFAULT_CHASE_SPEED,
    ) -> None:
        """
        Initialise an Enemy.

        Parameters
        ----------
        pos:
            Starting [x, y] world position.
        name:
            Identifier string (e.g. ``"StrictFather"``).
        patrol_path:
            Waypoints to walk when idle.
        patrol_wait:
            Seconds to wait at each patrol node.
        dialogue_key:
            Story data key for enemy dialogue lines.
        chase_speed:
            Pixels per second the enemy moves while chasing.
        """
        super().__init__(pos, name, patrol_path, patrol_wait, dialogue_key)

        # Red placeholder sprite for enemies.
        self._placeholder_color = (200, 30, 30)
        self.sprite: pygame.Surface | None = None

        # Chase / search state.
        self.last_known_player_pos: tuple[float, float] | None = None
        self.chase_speed: float = chase_speed
        self.search_timer: float = 0.0

        # Placeholder for A* path list (direct vector for now).
        self._chase_path: list[tuple[float, float]] = []

        # Search wander target (recalculated when switching into search).
        self._search_target: tuple[float, float] | None = None

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(  # type: ignore[override]
        self,
        dt: float,
        player: "Player | None" = None,
        tile_map=None,
    ) -> None:
        """
        Advance enemy state for one tick.

        Parameters
        ----------
        dt:
            Delta-time in seconds.
        player:
            Player entity; needed for sight, distance, and catch checks.
        tile_map:
            Level tile map (reserved for future pathfinding).
        """
        if not self.active:
            return

        # --- Sight check (same cone as NPC) -------------------------
        player_visible = False
        if player is not None and player.active and not player.is_hidden:
            if self.can_see_point(player.center):
                player_visible = True
                self.last_known_player_pos = player.center
                # Accelerate suspicion when in direct sight.
                self.suspicion = min(
                    self.suspicion + NPC_SUSPICION_RATE * dt * 2.0,
                    NPC_CONFIRM_THRESHOLD,
                )

        # --- Suspicion decay (only when idle/suspicious) -------------
        if not player_visible and self.alert_state in ("idle", "suspicious"):
            self.suspicion = max(0.0, self.suspicion - NPC_SUSPICION_DECAY * dt)
            if self.suspicion < NPC_ALERT_THRESHOLD and self.alert_state == "suspicious":
                self.alert_state = "idle"
                self._alert_emitted = False

        # --- Threshold transitions ------------------------------------
        if self.suspicion >= NPC_CONFIRM_THRESHOLD:
            if self.alert_state not in ("chasing", "searching", "alert"):
                self.alert_state = "chasing"
        elif self.suspicion >= NPC_ALERT_THRESHOLD and self.alert_state == "idle":
            self.alert_state = "suspicious"

        # --- FSM dispatch --------------------------------------------
        if self.alert_state == "idle":
            self._update_patrol_dt(dt)

        elif self.alert_state == "suspicious":
            self._update_suspicious()

        elif self.alert_state == "alert":
            # Transition immediately to chasing.
            self.alert_state = "chasing"
            self._update_chasing(dt, player)

        elif self.alert_state == "chasing":
            self._update_chasing(dt, player)

        elif self.alert_state == "searching":
            self._update_searching(dt, player)

    # ------------------------------------------------------------------
    # Chase / search FSM methods
    # ------------------------------------------------------------------

    def _update_chasing(self, dt: float, player: "Player | None") -> None:
        """
        Chase the player (or last known position).

        If the player is currently visible, update last_known_player_pos
        each frame.  When we get within catch distance, trigger get_caught.
        If we reach the last known pos and the player is not visible,
        switch to searching.

        Parameters
        ----------
        dt:
            Delta-time in seconds.
        player:
            Player entity.
        """
        # Emit alert_raised once when entering chase state.
        if not self._alert_emitted:
            self._alert_emitted = True
            self._bus.emit("alert_raised", {
                "npc_name": self.name,
                "pos": tuple(self.center),
                "hostile": True,
            })

        if self.last_known_player_pos is None:
            # No target; fall back to idle.
            self.alert_state = "idle"
            return

        # --- Check if we caught the player --------------------------
        if player is not None and player.active:
            dist = math.hypot(
                self.center[0] - player.center[0],
                self.center[1] - player.center[1],
            )
            if dist < _CATCH_DISTANCE:
                player.get_caught()
                # Reset to idle after catching.
                self.alert_state = "idle"
                self.suspicion = 0.0
                self._alert_emitted = False
                return

        # --- Move toward target -------------------------------------
        tx, ty = self.last_known_player_pos
        cx, cy = self.center
        dx = tx - cx
        dy = ty - cy
        dist_to_target = math.hypot(dx, dy)

        if dist_to_target < 8.0:
            # Reached last known position but player not caught → search.
            if player is None or not self.can_see_point(player.center):
                self._enter_searching()
                return

        if dist_to_target > 1e-6:
            norm_x = dx / dist_to_target
            norm_y = dy / dist_to_target
            self.pos[0] += norm_x * self.chase_speed * dt
            self.pos[1] += norm_y * self.chase_speed * dt
            # Update facing.
            self.facing_angle = math.degrees(math.atan2(-dy, dx))

    def _enter_searching(self) -> None:
        """Transition into the searching state and pick an initial wander point."""
        self.alert_state = "searching"
        self.search_timer = NPC_SEARCH_DURATION
        self._pick_search_target()

    def _pick_search_target(self) -> None:
        """Choose a random point near last_known_player_pos to wander to."""
        if self.last_known_player_pos is None:
            self._search_target = tuple(self.center)  # type: ignore[assignment]
            return
        angle = random.uniform(0, math.pi * 2)
        radius = random.uniform(_SEARCH_WANDER_RADIUS * 0.4, _SEARCH_WANDER_RADIUS)
        self._search_target = (
            self.last_known_player_pos[0] + math.cos(angle) * radius,
            self.last_known_player_pos[1] + math.sin(angle) * radius,
        )

    def _update_searching(self, dt: float, player: "Player | None") -> None:
        """
        Wander near last known player position.

        Re-enters chasing if the player becomes visible again.
        Gives up and returns to idle once the timer expires.

        Parameters
        ----------
        dt:
            Delta-time in seconds.
        player:
            Player entity.
        """
        # If we spot the player, go back to chasing.
        if player is not None and player.active and not player.is_hidden:
            if self.can_see_point(player.center):
                self.last_known_player_pos = player.center
                self.alert_state = "chasing"
                return

        # Count down the search timer.
        self.search_timer -= dt
        if self.search_timer <= 0.0:
            # Give up; clear suspicion and go idle.
            self.alert_state = "idle"
            self.suspicion = 0.0
            self._alert_emitted = False
            self.last_known_player_pos = None
            self._search_target = None
            self._bus.emit("alert_cleared", {"npc_name": self.name})
            return

        # Walk toward current wander target.
        if self._search_target is None:
            self._pick_search_target()

        tx, ty = self._search_target  # type: ignore[misc]
        cx, cy = self.center
        dx = tx - cx
        dy = ty - cy
        dist = math.hypot(dx, dy)

        if dist < 8.0:
            # Reached wander target; pick a new one.
            self._pick_search_target()
        else:
            # Move at half chase speed while searching.
            search_speed = self.chase_speed * 0.5
            self.pos[0] += (dx / dist) * search_speed * dt
            self.pos[1] += (dy / dist) * search_speed * dt
            self.facing_angle = math.degrees(math.atan2(-dy, dx))

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface, camera: "Camera") -> None:
        """
        Draw the enemy placeholder sprite with chase/search overlay.

        Parameters
        ----------
        surface:
            Logical render target.
        camera:
            Camera transform.
        """
        if not self.visible or not self.active:
            return

        screen_pos = camera.world_to_screen(self.pos)
        ph = self.get_placeholder_surface(self._placeholder_color, self.size)

        # Bright overlay when chasing or searching.
        overlay_color: tuple[int, int, int, int] | None = None
        if self.alert_state == "chasing":
            overlay_color = (255, 60, 0, 130)
        elif self.alert_state == "searching":
            overlay_color = (200, 100, 0, 100)
        elif self.alert_state == "suspicious":
            overlay_color = (255, 200, 0, 90)

        if overlay_color:
            overlay = pygame.Surface(self.size, pygame.SRCALPHA)
            overlay.fill(overlay_color)
            ph.blit(overlay, (0, 0))

        surface.blit(ph, screen_pos)
