"""
core/renderer.py
================
Layered draw queue for Verlassen.
Supports layered rendering: BACKGROUND -> ENVIRONMENT -> ENTITIES -> FOREGROUND -> LIGHTING -> UI
"""

from __future__ import annotations

from enum import IntEnum
from typing import Callable

import pygame


class Layer(IntEnum):
    BACKGROUND = 0
    ENVIRONMENT = 1
    ENTITIES = 2
    FOREGROUND = 3
    LIGHTING = 4
    UI = 5


class Renderer:
    """
    Deferred rendering queue sorted by layer depth.
    """

    def __init__(self) -> None:
        self._queue: list[tuple[int, Callable[[pygame.Surface], None]]] = []

    def add(self, surface: pygame.Surface, pos: tuple[int, int], layer: Layer = Layer.ENTITIES) -> None:
        """Enqueue a surface blit."""
        self._queue.append((int(layer), lambda target: target.blit(surface, pos)))

    def add_custom(self, render_fn: Callable[[pygame.Surface], None], layer: Layer = Layer.ENTITIES) -> None:
        """Enqueue a custom drawing function."""
        self._queue.append((int(layer), render_fn))

    def flush(self, target_surface: pygame.Surface) -> None:
        """Execute all queued draw operations in layer order and clear queue."""
        self._queue.sort(key=lambda item: item[0])
        for _, draw_fn in self._queue:
            draw_fn(target_surface)
        self._queue.clear()

