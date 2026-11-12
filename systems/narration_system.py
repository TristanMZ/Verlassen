"""
systems/narration_system.py
===========================
Renders Ren Calloway's inner voice and dialogue subtitles.
"""

from __future__ import annotations

from typing import Any

import pygame

from config import INTERNAL_W, INTERNAL_H
from core.event_bus import bus, EVT_NARRATION_TRIGGER


class NarrationItem:
    def __init__(self, text: str, duration: float = 4.0, style: str = "thought") -> None:
        self.text = text
        self.duration = duration
        self.elapsed: float = 0.0
        self.style = style  # "thought" or "spoken"


class NarrationSystem:
    """
    Queue and display inner-monologue narration text.
    """

    def __init__(self) -> None:
        self.queue: list[NarrationItem] = []
        self.current: NarrationItem | None = None
        self.triggered_keys: set[str] = set()
        self.font: pygame.font.Font | None = None

    def _ensure_font(self) -> pygame.font.Font:
        if self.font is None:
            self.font = pygame.font.SysFont("georgia", 20, italic=True)
        return self.font

    def queue_text(self, text: str, duration: float = 4.0, style: str = "thought") -> None:
        """Add a narration item to the queue."""
        item = NarrationItem(text, duration, style)
        if self.current is None:
            self.current = item
        else:
            self.queue.append(item)

    def trigger(self, key: str, narration_data: dict[str, Any]) -> bool:
        """
        Trigger narration by key if not already triggered.
        Returns True if triggered.
        """
        if key in self.triggered_keys:
            return False

        if key in narration_data:
            entry = narration_data[key]
            text = entry.get("text", "")
            duration = float(entry.get("duration", 4.0))
            self.queue_text(text, duration)
            self.triggered_keys.add(key)
            bus.emit(EVT_NARRATION_TRIGGER, {"key": key, "text": text})
            return True

        return False

    def update(self, dt: float) -> None:
        """Advance time for active narration."""
        if self.current is None:
            if self.queue:
                self.current = self.queue.pop(0)
            return

        self.current.elapsed += dt
        if self.current.elapsed >= self.current.duration:
            self.current = self.queue.pop(0) if self.queue else None

    def draw(self, surface: pygame.Surface) -> None:
        """Draw current narration text with smooth fade at bottom of the screen."""
        if self.current is None:
            return

        font = self._ensure_font()
        t = self.current.elapsed
        dur = self.current.duration

        # Compute alpha for fade-in (0.4s) and fade-out (0.4s)
        fade_time = 0.4
        alpha = 255
        if t < fade_time:
            alpha = int(255 * (t / fade_time))
        elif t > dur - fade_time:
            alpha = max(0, int(255 * ((dur - t) / fade_time)))

        if alpha <= 0:
            return

        text_surf = font.render(self.current.text, True, (240, 240, 250))
        text_surf.set_alpha(alpha)

        # Subtle dark translucent bar behind text
        rect = text_surf.get_rect(center=(INTERNAL_W // 2, INTERNAL_H - 45))
        bg_surf = pygame.Surface((rect.width + 24, rect.height + 10), pygame.SRCALPHA)
        bg_surf.fill((10, 8, 14, min(180, alpha)))

        surface.blit(bg_surf, (rect.x - 12, rect.y - 5))
        surface.blit(text_surf, rect)

