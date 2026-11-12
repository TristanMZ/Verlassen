"""
systems/stealth_system.py
=========================
Line-of-sight raycasting and acoustic noise detection system for Verlassen.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

import pygame

from config import (
    TILE_SIZE,
    NOISE_STILL,
    NOISE_SNEAK,
    NOISE_WALK,
    NOISE_RUN,
    NOISE_CREAK,
)
from core.event_bus import bus, EVT_NOISE_EMITTED

if TYPE_CHECKING:
    from core.camera import Camera
    from entities.player import Player
    from entities.npc import NPC


class StealthSystem:
    """
    Computes NPC detection:
    1. Vision cone raycasts through solid tiles.
    2. Sound radius overlaps based on player movement noise.
    """

    NOISE_RADII = {
        NOISE_STILL: 0.0,
        NOISE_SNEAK: 40.0,
        NOISE_WALK: 110.0,
        NOISE_RUN: 200.0,
        NOISE_CREAK: 280.0,
    }

    def __init__(self) -> None:
        self.debug_vision: bool = True

    def update(
        self,
        dt: float,
        enemies: list[NPC],
        player: Player,
        tile_map: Any,
    ) -> None:
        """
        Process perception checks for all NPCs against player.
        """
        player_center = player.center
        player_hidden = getattr(player, "is_hidden", False)
        noise_level = getattr(player, "noise_level", NOISE_STILL)
        noise_radius = self.NOISE_RADII.get(noise_level, 0.0)

        for npc in enemies:
            if not npc.active:
                continue

            npc_center = npc.center
            dx = player_center[0] - npc_center[0]
            dy = player_center[1] - npc_center[1]
            dist = math.hypot(dx, dy)

            # 1. Vision Check
            if not player_hidden and dist <= npc.vision_range:
                # Calculate angle to player in degrees (0 = right, 90 = down)
                angle_to_player = math.degrees(math.atan2(dy, dx))
                facing = getattr(npc, "facing_angle", 0.0)

                # Smallest angle difference [-180, 180]
                diff = (angle_to_player - facing + 180) % 360 - 180
                half_fov = npc.fov_degrees / 2.0

                if abs(diff) <= half_fov:
                    # Raycast from NPC center to player center
                    if self._has_los(npc_center, player_center, tile_map):
                        # Intensity scales inversely with distance
                        intensity = max(0.2, 1.0 - (dist / npc.vision_range) * 0.6)
                        npc.receive_stimulus("vision", intensity=intensity * dt)

            # 2. Noise Check (works even if hidden, but at reduced range)
            effective_radius = noise_radius * (0.3 if player_hidden else 1.0)
            if effective_radius > 0 and dist <= effective_radius:
                noise_intensity = (noise_level / 4.0) * (1.0 - dist / effective_radius)
                npc.receive_stimulus("noise", intensity=noise_intensity * dt)
                bus.emit(EVT_NOISE_EMITTED, {
                    "source": "player",
                    "pos": player_center,
                    "level": noise_level,
                })

    def _has_los(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        tile_map: Any,
    ) -> bool:
        """Step along the ray to ensure no solid wall blocks line of sight."""
        sx, sy = start
        ex, ey = end
        dist = math.hypot(ex - sx, ey - sy)
        if dist < 1.0:
            return True

        step_size = TILE_SIZE / 4.0
        steps = int(dist / step_size)
        if steps == 0:
            return True

        dx = (ex - sx) / steps
        dy = (ey - sy) / steps

        cur_x, cur_y = sx, sy
        for _ in range(steps):
            cur_x += dx
            cur_y += dy
            tile_x = int(cur_x // TILE_SIZE)
            tile_y = int(cur_y // TILE_SIZE)
            if hasattr(tile_map, "is_solid") and tile_map.is_solid(tile_x, tile_y):
                return False

        return True

    def draw_debug(self, surface: pygame.Surface, camera: Camera, enemies: list[NPC]) -> None:
        """Render semi-transparent vision cone wedges and alert indicators."""
        if not self.debug_vision:
            return

        for npc in enemies:
            if not npc.active:
                continue

            sx, sy = camera.world_to_screen(npc.center)
            facing = getattr(npc, "facing_angle", 0.0)
            half_fov = npc.fov_degrees / 2.0
            r = npc.vision_range

            # Determine vision cone color based on alert state
            state = getattr(npc, "alert_state", "idle")
            if state == "chasing":
                cone_color = (255, 40, 40, 60)
            elif state in ("alert", "searching"):
                cone_color = (255, 180, 40, 50)
            elif state == "suspicious":
                cone_color = (240, 240, 80, 40)
            else:
                cone_color = (100, 200, 255, 25)

            # Build polygon points for wedge
            points = [(sx, sy)]
            num_segments = 14
            for i in range(num_segments + 1):
                ang = math.radians(facing - half_fov + (npc.fov_degrees * i / num_segments))
                px = sx + math.cos(ang) * r
                py = sy + math.sin(ang) * r
                points.append((px, py))

            # Draw semi-transparent wedge
            cone_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(cone_surf, cone_color, points)
            pygame.draw.lines(cone_surf, (cone_color[0], cone_color[1], cone_color[2], 90), False, points)
            surface.blit(cone_surf, (0, 0))

