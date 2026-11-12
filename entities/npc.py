"""
entities/npc.py
===============
Non-hostile NPC entity for Verlassen.

Family members (Mother, Father, siblings) patrol routes, overhear
noise, and grow suspicious of Ren — but they never chase.  When
suspicion hits NPC_CONFIRM_THRESHOLD they become "alert" and emit an
event that the narration / audio systems pick up.
"""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

import pygame

from config import (
    SPRITE_SCALE,
    TILE_SIZE,
    WALK_SPEED,
    NPC_VISION_RANGE,
    NPC_FOV_DEGREES,
    NPC_SUSPICION_RATE,
    NPC_SUSPICION_DECAY,
    NPC_ALERT_THRESHOLD,
    NPC_CONFIRM_THRESHOLD,
)
from core.event_bus import EventBus
from entities.base_entity import BaseEntity

if TYPE_CHECKING:
    from core.camera import Camera

_SPRITE_PX = SPRITE_SCALE * 32

# NPC patrol speed is slightly slower than player walk.
_NPC_PATROL_SPEED = WALK_SPEED * 0.65

# How close (px) the NPC must be to a patrol node before moving on.
_NODE_ARRIVAL_THRESHOLD = 4.0


class NPC(BaseEntity):
    """
    Non-hostile family-member NPC.

    Patrols a fixed path, can become suspicious when it hears Ren or
    spots them in its vision cone, but will never chase.

    Alert states
    ------------
    ``"idle"``       -- following patrol path normally
    ``"suspicious"`` -- stopped; suspicion is rising
    ``"alert"``      -- fully alerted; emits ``"alert_raised"``

    Attributes
    ----------
    name : str
        Display name, e.g. ``"Mother"``.
    facing_angle : float
        Current look direction in degrees (0 = right, CCW +).
    alert_state : str
        Current FSM state (see above).
    suspicion : float
        Accumulator in ``[0, NPC_CONFIRM_THRESHOLD]``.
    patrol_path : list[tuple[float, float]]
        Ordered world positions the NPC walks between.
    patrol_index : int
        Index of the current destination node in *patrol_path*.
    patrol_wait : float
        Seconds to wait at each node before moving on.
    dialogue_key : str
        Key into the story/narration data for overheard lines.
    """

    def __init__(
        self,
        pos: list[float],
        name: str = "NPC",
        patrol_path: list[tuple[float, float]] | None = None,
        patrol_wait: float = 2.0,
        dialogue_key: str = "",
        fov_degrees: float = NPC_FOV_DEGREES,
        vision_range: int = NPC_VISION_RANGE,
    ) -> None:
        """
        Initialise an NPC.

        Parameters
        ----------
        pos:
            Starting [x, y] world position.
        name:
            Human-readable label (e.g. ``"Father"``).
        patrol_path:
            Sequence of world positions to walk between.  When None or
            empty the NPC stands still.
        patrol_wait:
            How many seconds to pause at each patrol node.
        dialogue_key:
            Story data key for overheard dialogue lines.
        fov_degrees:
            Field of view in degrees.
        vision_range:
            Vision range in world pixels.
        """
        size = (_SPRITE_PX, _SPRITE_PX)
        super().__init__(pos, size)

        # Orange placeholder sprite for NPCs.
        self._placeholder_color = (230, 140, 30)
        self.sprite: pygame.Surface | None = None

        self.name: str = name
        self.facing_angle: float = 0.0
        self.dialogue_key: str = dialogue_key
        self.fov_degrees: float = fov_degrees
        self.vision_range: int = vision_range


        # Patrol state.
        self.patrol_path: list[tuple[float, float]] = list(patrol_path or [])
        self.patrol_index: int = 0
        self._wait_timer: float = 0.0
        self.patrol_wait: float = patrol_wait

        # Suspicion FSM.
        self.alert_state: str = "idle"
        self.suspicion: float = 0.0
        self._last_known_player_dir: float = 0.0  # degrees
        self._alert_emitted: bool = False          # one-shot guard

        self._bus = EventBus.get()

    # ------------------------------------------------------------------
    # Vision helpers
    # ------------------------------------------------------------------

    def can_see_point(self, world_pos: tuple[float, float]) -> bool:
        """
        Return True if *world_pos* lies inside the NPC's vision cone.

        The cone is a 2D wedge of ``NPC_FOV_DEGREES`` centred on
        ``facing_angle``, extending ``NPC_VISION_RANGE`` pixels.

        Parameters
        ----------
        world_pos:
            (x, y) point in world space to test.
        """
        cx, cy = self.center
        dx = world_pos[0] - cx
        dy = world_pos[1] - cy  # note: pygame y-down

        dist = math.hypot(dx, dy)
        if dist > NPC_VISION_RANGE or dist < 1e-6:
            return False

        # Angle from NPC to target (pygame y-down → negate dy for CCW).
        target_angle = math.degrees(math.atan2(-dy, dx))

        # Angular difference (shortest arc).
        diff = (target_angle - self.facing_angle + 360) % 360
        if diff > 180:
            diff -= 360
        return abs(diff) <= NPC_FOV_DEGREES / 2.0

    # ------------------------------------------------------------------
    # Stimulus API
    # ------------------------------------------------------------------

    def receive_stimulus(self, stimulus_type: str, intensity: float) -> None:
        """
        React to an external stimulus (noise, sight, etc.).

        Increases suspicion by *intensity* scaled by a type multiplier.
        Noise is less alarming than direct sight.

        Parameters
        ----------
        stimulus_type:
            ``"noise"`` or ``"sight"``.
        intensity:
            Raw intensity value (e.g. NOISE_* constant or distance factor).
        """
        multiplier = {
            "noise": 0.6,
            "sight": 1.0,
        }.get(stimulus_type, 0.5)

        gain = intensity * multiplier
        self.suspicion = min(self.suspicion + gain, NPC_CONFIRM_THRESHOLD)

        # Transition to suspicious if threshold reached.
        if self.suspicion >= NPC_ALERT_THRESHOLD and self.alert_state == "idle":
            self.alert_state = "suspicious"

    # ------------------------------------------------------------------
    # Update FSM
    # ------------------------------------------------------------------

    def update(self, dt: float, player=None, tile_map=None) -> None:  # type: ignore[override]
        """
        Advance NPC state for one tick.

        Parameters
        ----------
        dt:
            Delta-time in seconds.
        player:
            Player entity; used for sight checks.  May be None.
        tile_map:
            Tile map; not used directly in NPC but accepted for API
            consistency with subclasses.
        """
        if not self.active:
            return

        # --- Sight check: if player is visible, increase suspicion. ---
        player_in_cone = False
        if player is not None and player.active and not player.is_hidden:
            if self.can_see_point(player.center):
                player_in_cone = True
                # Store direction toward player for "suspicious" facing.
                dx = player.center[0] - self.center[0]
                dy = player.center[1] - self.center[1]
                self._last_known_player_dir = math.degrees(math.atan2(-dy, dx))
                # Rate of suspicion gain from sight.
                self.receive_stimulus("sight", NPC_SUSPICION_RATE * dt)

        # --- Suspicion decay when player not in cone. -----------------
        if not player_in_cone and self.alert_state != "alert":
            self.suspicion = max(0.0, self.suspicion - NPC_SUSPICION_DECAY * dt)
            if self.suspicion < NPC_ALERT_THRESHOLD and self.alert_state == "suspicious":
                self.alert_state = "idle"
                self._alert_emitted = False

        # --- Confirm threshold → alert. --------------------------------
        if self.suspicion >= NPC_CONFIRM_THRESHOLD and self.alert_state != "alert":
            self.alert_state = "alert"

        # --- FSM dispatch. ---------------------------------------------
        if self.alert_state == "idle":
            self._update_patrol(dt)
        elif self.alert_state == "suspicious":
            self._update_suspicious()
        elif self.alert_state == "alert":
            self._update_alert()

    def _update_patrol(self, dt: float) -> None:
        """Move along patrol_path, waiting at each node."""
        if not self.patrol_path:
            return  # stationary NPC

        target = self.patrol_path[self.patrol_index]
        cx, cy = self.center

        dx = target[0] - cx
        dy = target[1] - cy
        dist = math.hypot(dx, dy)

        if dist < _NODE_ARRIVAL_THRESHOLD:
            # Arrived at node — wait then advance.
            self._wait_timer += 1.0 / 60.0  # dt is 1/60; use 1 frame tick
            # (In practice dt is passed in, so we use it properly here:)
            # Recalculate using actual dt — overwrite above.
            self._wait_timer = self._wait_timer  # keeps previous increment
            if self._wait_timer >= self.patrol_wait:
                self._wait_timer = 0.0
                self.patrol_index = (self.patrol_index + 1) % len(self.patrol_path)
        else:
            # Move toward node.
            speed = _NPC_PATROL_SPEED
            self.pos[0] += (dx / dist) * speed / 60.0  # 1 frame step
            self.pos[1] += (dy / dist) * speed / 60.0
            # Update facing from movement direction.
            self.facing_angle = math.degrees(math.atan2(-dy, dx))

    def _update_patrol_dt(self, dt: float) -> None:
        """dt-correct patrol update (called from subclass-aware paths)."""
        if not self.patrol_path:
            return

        target = self.patrol_path[self.patrol_index]
        cx, cy = self.center

        dx = target[0] - cx
        dy = target[1] - cy
        dist = math.hypot(dx, dy)

        if dist < _NODE_ARRIVAL_THRESHOLD:
            self._wait_timer += dt
            if self._wait_timer >= self.patrol_wait:
                self._wait_timer = 0.0
                self.patrol_index = (self.patrol_index + 1) % len(self.patrol_path)
        else:
            speed = _NPC_PATROL_SPEED
            self.pos[0] += (dx / dist) * speed * dt
            self.pos[1] += (dy / dist) * speed * dt
            self.facing_angle = math.degrees(math.atan2(-dy, dx))

    def _update_suspicious(self) -> None:
        """Face last known player direction; do not move."""
        self.facing_angle = self._last_known_player_dir

    def _update_alert(self) -> None:
        """
        Fully alerted: stop, emit event once.

        The narration and audio systems subscribe to ``"alert_raised"``
        to trigger dialogue and tension music.
        """
        if not self._alert_emitted:
            self._alert_emitted = True
            self._bus.emit("alert_raised", {
                "npc_name": self.name,
                "pos": tuple(self.center),
            })

    # ------------------------------------------------------------------
    # Override update to use dt-correct patrol
    # ------------------------------------------------------------------

    def update(self, dt: float, player=None, tile_map=None) -> None:  # noqa: F811
        """Full dt-correct update (overrides the stub above)."""
        if not self.active:
            return

        player_in_cone = False
        if player is not None and player.active and not player.is_hidden:
            if self.can_see_point(player.center):
                player_in_cone = True
                dx = player.center[0] - self.center[0]
                dy = player.center[1] - self.center[1]
                self._last_known_player_dir = math.degrees(math.atan2(-dy, dx))
                self.suspicion = min(
                    self.suspicion + NPC_SUSPICION_RATE * dt,
                    NPC_CONFIRM_THRESHOLD,
                )
                if self.suspicion >= NPC_ALERT_THRESHOLD and self.alert_state == "idle":
                    self.alert_state = "suspicious"

        if not player_in_cone and self.alert_state != "alert":
            self.suspicion = max(0.0, self.suspicion - NPC_SUSPICION_DECAY * dt)
            if self.suspicion < NPC_ALERT_THRESHOLD and self.alert_state == "suspicious":
                self.alert_state = "idle"
                self._alert_emitted = False

        if self.suspicion >= NPC_CONFIRM_THRESHOLD and self.alert_state != "alert":
            self.alert_state = "alert"

        if self.alert_state == "idle":
            self._update_patrol_dt(dt)
        elif self.alert_state == "suspicious":
            self._update_suspicious()
        elif self.alert_state == "alert":
            self._update_alert()

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface, camera: "Camera") -> None:
        """Draw the NPC placeholder sprite and optional debug cone."""
        if not self.visible or not self.active:
            return

        screen_pos = camera.world_to_screen(self.pos)
        ph = self.get_placeholder_surface(self._placeholder_color, self.size)

        # State-colour overlay: yellow = suspicious, red = alert.
        overlay_color: tuple[int, int, int, int] | None = None
        if self.alert_state == "suspicious":
            overlay_color = (255, 220, 0, 100)
        elif self.alert_state == "alert":
            overlay_color = (220, 0, 0, 120)

        if overlay_color:
            overlay = pygame.Surface(self.size, pygame.SRCALPHA)
            overlay.fill(overlay_color)
            ph.blit(overlay, (0, 0))

        surface.blit(ph, screen_pos)

    def draw_vision_cone(self, surface: pygame.Surface, camera: "Camera") -> None:
        """
        Debug-only: draw a filled wedge representing the NPC's field of view.

        Parameters
        ----------
        surface:
            Logical render target.
        camera:
            Camera transform.
        """
        cx, cy = self.center
        scx, scy = camera.world_to_screen([cx, cy])

        # Build a polygon for the cone.
        half_fov = NPC_FOV_DEGREES / 2.0
        num_steps = 16
        points = [(scx, scy)]

        for i in range(num_steps + 1):
            angle_deg = self.facing_angle + (-half_fov + (NPC_FOV_DEGREES / num_steps) * i)
            angle_rad = math.radians(angle_deg)
            end_x = scx + math.cos(angle_rad) * NPC_VISION_RANGE
            end_y = scy - math.sin(angle_rad) * NPC_VISION_RANGE  # y-down
            points.append((int(end_x), int(end_y)))

        if len(points) >= 3:
            cone_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(cone_surf, (255, 255, 100, 40), points)
            pygame.draw.lines(cone_surf, (255, 255, 100, 150), False, points[1:], 1)
            surface.blit(cone_surf, (0, 0))
