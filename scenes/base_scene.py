"""
scenes/base_scene.py
~~~~~~~~~~~~~~~~~~~~
Abstract base class that every scene in Verlassen must inherit from.

The SceneManager calls these methods; concrete scenes implement them.
"""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    # Avoid circular imports at runtime; SceneManager is only needed for type hints.
    from core.scene_manager import SceneManager


class BaseScene(abc.ABC):
    """Abstract base scene.

    All game scenes (main menu, level, cutscene, pause, game-over) derive from
    this class.  The SceneManager drives the lifecycle via ``on_enter`` /
    ``on_exit`` and the three per-frame hooks.

    Args:
        scene_manager: The owning SceneManager instance, stored so scenes can
            request transitions without coupling to a global singleton.
    """

    def __init__(self, scene_manager: "SceneManager") -> None:
        self._scene_manager: "SceneManager" = scene_manager

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def on_enter(self) -> None:
        """Called once when this scene becomes the active scene.

        Override to load resources, subscribe to events, start music, etc.
        The default implementation is a no-op so subclasses only override
        what they need.
        """

    def on_exit(self) -> None:
        """Called once when this scene is about to be removed.

        Override to release resources, unsubscribe from events, etc.
        """

    def on_resume(self) -> None:
        """Called when an overlay on top of this scene is popped."""


    # ------------------------------------------------------------------
    # Per-frame hooks
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def handle_event(self, event: pygame.event.Event) -> None:
        """Process a single Pygame event.

        Called by SceneManager for every event in the queue *before*
        ``update``.  Scenes that sit below a push-overlay (e.g. the
        level scene below the pause overlay) will NOT receive events
        while the overlay is active — the manager only forwards events
        to the top-most scene.

        Args:
            event: A pygame.event.Event object polled from the event queue.
        """

    @abc.abstractmethod
    def update(self, dt: float) -> None:
        """Advance game logic by *dt* seconds.

        Args:
            dt: Elapsed seconds since the last frame (fixed at 1/60 by the
                game loop).
        """

    @abc.abstractmethod
    def draw(self, surface: pygame.Surface) -> None:
        """Render this scene onto *surface*.

        ``surface`` is always the internal 1280×720 logical surface; the
        game loop handles upscaling to the window resolution afterwards.

        Args:
            surface: The render target.
        """
