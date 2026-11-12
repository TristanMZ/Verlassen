"""
core/scene_manager.py
=====================
Stack-based scene manager for Verlassen.
Supports switching active scene, pushing overlay scenes (e.g. pause), and popping back.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pygame

if TYPE_CHECKING:
    from scenes.base_scene import BaseScene


class SceneManager:
    """
    Manages scene stack and transitions.
    """

    def __init__(self) -> None:
        self.stack: list[BaseScene] = []

    @property
    def current(self) -> BaseScene | None:
        return self.stack[-1] if self.stack else None

    def push(self, scene: BaseScene) -> None:
        """Push a scene on top of the current one (overlay, like Pause)."""
        self.stack.append(scene)
        scene.on_enter()

    def pop(self) -> BaseScene | None:
        """Pop the top scene off the stack and restore the previous scene."""
        if not self.stack:
            return None
        popped = self.stack.pop()
        popped.on_exit()
        if self.stack:
            self.stack[-1].on_resume()
        return popped

    def switch(self, scene: BaseScene) -> None:
        """Clear the current scene(s) and replace with a new one."""
        while self.stack:
            old = self.stack.pop()
            old.on_exit()
        self.push(scene)

    def handle_event(self, event: pygame.Event) -> None:
        if self.current:
            self.current.handle_event(event)

    def update(self, dt: float) -> None:
        if self.current:
            self.current.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """
        Draw all active stacked scenes bottom-to-top.
        If scenes below are covered, they still render behind semi-transparent overlays.
        """
        for scene in self.stack:
            scene.draw(surface)

