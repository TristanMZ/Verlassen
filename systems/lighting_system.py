"""
systems/lighting_system.py
==========================
Dynamic 2D lighting compositor for Verlassen.
Draws ambient darkness overlay and punches soft light holes for lanterns, lamps, and flashlight cones.
"""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING, Any

import pygame

from config import INTERNAL_W, INTERNAL_H, AMBIENT_DARKNESS

if TYPE_CHECKING:
    from core.camera import Camera


class LightSource:
    def __init__(
        self,
        pos: tuple[float, float],
        radius: float,
        color: tuple[int, int, int] = (255, 230, 180),
        intensity: float = 1.0,
        flicker: bool = False,
    ) -> None:
        self.pos = pos
        self.radius = radius
        self.color = color
        self.intensity = intensity
        self.flicker = flicker
        self._flicker_phase = random.random() * 100.0


class LightingSystem:
    """
    Renders darkness overlay with radial lights blended subtractively.
    """

    def __init__(self) -> None:
        self.ambient_darkness: int = AMBIENT_DARKNESS
        self.lights: list[LightSource] = []
        self._dark_surface = pygame.Surface((INTERNAL_W, INTERNAL_H), pygame.SRCALPHA)
        self._light_cache: dict[tuple[int, tuple[int, int, int]], pygame.Surface] = {}

    def add_light(
        self,
        pos: tuple[float, float],
        radius: float,
        color: tuple[int, int, int] = (255, 220, 150),
        intensity: float = 1.0,
        flicker: bool = False,
    ) -> None:
        """Register a light source for the current frame."""
        self.lights.append(LightSource(pos, radius, color, intensity, flicker))

    def clear_lights(self) -> None:
        """Clear all registered lights."""
        self.lights.clear()

    def _get_radial_surface(self, radius: int, color: tuple[int, int, int]) -> pygame.Surface:
        """Create and cache soft circular radial light punch."""
        key = (radius, color)
        if key in self._light_cache:
            return self._light_cache[key]

        size = radius * 2
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        center = radius

        # Concentric rings fading outward to zero alpha
        num_rings = 16
        for i in range(num_rings, 0, -1):
            factor = i / num_rings
            current_r = int(radius * factor)
            # Alpha reaches 255 at center, 0 at edge
            alpha = int(255 * (1.0 - factor) ** 1.3)
            pygame.draw.circle(
                surf,
                (color[0], color[1], color[2], alpha),
                (center, center),
                current_r,
            )

        self._light_cache[key] = surf
        return surf

    def render(self, target: pygame.Surface, camera: Camera) -> None:
        """Compose lighting onto the target surface."""
        # 1. Fill dark surface with uniform ambient darkness
        self._dark_surface.fill((10, 8, 16, self.ambient_darkness))

        # 2. Subtract darkness for each light
        for light in self.lights:
            sx, sy = camera.world_to_screen(light.pos)
            radius = light.radius

            if light.flicker:
                flicker_offset = math.sin(pygame.time.get_ticks() * 0.008 + light._flicker_phase) * 0.08
                flicker_offset += (random.random() - 0.5) * 0.06
                radius = max(8.0, radius * (1.0 + flicker_offset))

            r_int = int(radius)
            if r_int <= 0:
                continue

            light_surf = self._get_radial_surface(r_int, light.color)
            blit_pos = (int(sx - r_int), int(sy - r_int))

            # Blend subtractively to erase darkness
            self._dark_surface.blit(light_surf, blit_pos, special_flags=pygame.BLEND_RGBA_SUB)

        # 3. Blit darkness overlay onto target surface
        target.blit(self._dark_surface, (0, 0))

    def get_tint_at(self, world_pos: tuple[float, float]) -> tuple[int, int, int]:
        """Compute the cumulative light tint at a given position."""
        base_r, base_g, base_b = 60, 60, 80
        total_r, total_g, total_b = float(base_r), float(base_g), float(base_b)

        for light in self.lights:
            dx = world_pos[0] - light.pos[0]
            dy = world_pos[1] - light.pos[1]
            dist = math.hypot(dx, dy)
            if dist < light.radius:
                attenuation = (1.0 - dist / light.radius) * light.intensity
                total_r += light.color[0] * attenuation
                total_g += light.color[1] * attenuation
                total_b += light.color[2] * attenuation

        return (
            min(255, int(total_r)),
            min(255, int(total_g)),
            min(255, int(total_b)),
        )

