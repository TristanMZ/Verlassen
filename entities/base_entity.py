"""
entities/base_entity.py
=======================
Abstract base class for every game object in Verlassen.

All entities (player, NPCs, enemies, interactables) inherit from BaseEntity.
It owns the fundamental spatial data and the draw/update contract.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    # Avoid circular imports at runtime; camera is used only for type hints.
    from core.camera import Camera


class BaseEntity:
    """
    Base class for all Verlassen game entities.

    Provides position, collision rect, sprite management, and the
    update/draw interface that the game loop calls each frame.

    Attributes
    ----------
    pos : list[float]
        [x, y] world-space top-left corner of the entity in pixels.
    size : tuple[int, int]
        Width and height of the collision box in pixels.
    sprite : pygame.Surface | None
        The surface drawn each frame, or None if placeholder art is used.
    visible : bool
        When False the entity is completely skipped during draw.
    active : bool
        When False the entity is skipped during update (and draw).
    """

    def __init__(
        self,
        pos: list[float],
        size: tuple[int, int],
        sprite: pygame.Surface | None = None,
    ) -> None:
        """
        Initialise a BaseEntity.

        Parameters
        ----------
        pos:
            Starting [x, y] world position (top-left).
        size:
            (width, height) of the collision / bounding box in pixels.
        sprite:
            Optional pre-loaded surface.  Pass None to use placeholder art.
        """
        # Mutable list so callers can do entity.pos[0] += dx in-place.
        self.pos: list[float] = list(pos)
        self.size: tuple[int, int] = size
        self.sprite: pygame.Surface | None = sprite
        self.visible: bool = True
        self.active: bool = True

        # Placeholder colour used when no sprite is provided (subclasses
        # override _placeholder_color to get their own colour).
        self._placeholder_color: tuple[int, int, int] = (200, 200, 200)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def rect(self) -> pygame.Rect:
        """Return a pygame.Rect computed from current pos and size.

        Always up-to-date — no caching needed because pos may be mutated
        incrementally every frame.
        """
        return pygame.Rect(int(self.pos[0]), int(self.pos[1]), self.size[0], self.size[1])

    @property
    def center(self) -> tuple[float, float]:
        """Return the world-space centre of the entity's bounding box."""
        return (
            self.pos[0] + self.size[0] / 2.0,
            self.pos[1] + self.size[1] / 2.0,
        )

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """
        Update entity state for one game tick.

        Subclasses must override this.  The base implementation does
        nothing, so a subclass that forgets to call super().update(dt)
        doesn't break.

        Parameters
        ----------
        dt:
            Delta-time in seconds (fixed at 1/60 by the game loop).
        """

    def draw(self, surface: pygame.Surface, camera: "Camera") -> None:
        """
        Draw the entity onto *surface* using the camera transform.

        If a sprite surface is available it is blitted at the camera-
        transformed screen position.  Otherwise a solid-coloured
        placeholder rect is drawn.

        Parameters
        ----------
        surface:
            The render target (the logical 1280×720 internal surface).
        camera:
            Provides world_to_screen() for the coordinate transform.
        """
        if not self.visible or not self.active:
            return

        # Convert top-left world position → screen position.
        screen_pos: tuple[int, int] = camera.world_to_screen(self.pos)

        if self.sprite is not None:
            surface.blit(self.sprite, screen_pos)
        else:
            # Placeholder: draw a solid-coloured rectangle.
            placeholder = self.get_placeholder_surface(self._placeholder_color, self.size)
            surface.blit(placeholder, screen_pos)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_placeholder_surface(
        color: tuple[int, int, int],
        size: tuple[int, int],
    ) -> pygame.Surface:
        """
        Create a solid-coloured surface for placeholder art.

        Parameters
        ----------
        color:
            RGB tuple, e.g. (0, 120, 255).
        size:
            (width, height) of the surface in pixels.

        Returns
        -------
        pygame.Surface
            A new surface filled with *color*, suitable for blitting.
        """
        surf = pygame.Surface(size, flags=pygame.SRCALPHA)
        surf.fill(color)
        return surf

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} pos={self.pos} "
            f"size={self.size} active={self.active}>"
        )
