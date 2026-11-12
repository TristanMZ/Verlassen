"""
systems/timer_system.py
=======================
Timer system for Verlassen.

Manages named countdown timers used for:
  - Stealth alert durations.
  - Puzzle time limits.
  - Level-scripted events (e.g. "door unlocks in 10 seconds").

Each timer is registered by name so level scripts can query or cancel it at
any point.  When a timer expires it optionally calls a callback and always
emits a ``"timer_expired"`` event on the global ``EventBus``.

HUD rendering is provided via :meth:`draw_hud` for timers that the player
should be aware of.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pygame

from core.event_bus import EventBus

# ---------------------------------------------------------------------------
# HUD constants
# ---------------------------------------------------------------------------

_BAR_W: int = 160    # width of the countdown bar in pixels
_BAR_H: int = 12     # height of the countdown bar
_BAR_BG: tuple[int, int, int] = (30, 30, 40)
_BAR_BORDER: tuple[int, int, int] = (80, 80, 100)
_TEXT_COLOR: tuple[int, int, int] = (230, 230, 230)


@dataclass
class _Timer:
    """Internal record for a single countdown timer."""

    name: str
    duration: float               # original duration (seconds)
    remaining: float              # time left (seconds)
    on_expire: Callable[[], None] | None = field(default=None)
    expired: bool = False


class TimerSystem:
    """
    Named countdown-timer manager.

    Example usage::

        timers = TimerSystem()

        # Register a 10-second countdown with a callback.
        timers.add_timer("alarm", 10.0, on_expire=level.trigger_guards)

        # Every frame:
        timers.update(dt)

        # In the HUD draw:
        timers.draw_hud(screen, "alarm", pos=(20, 60))

        # Query / cancel.
        secs_left = timers.get_remaining("alarm")
        timers.cancel("alarm")
    """

    def __init__(self) -> None:
        """Initialise the timer system with no active timers."""
        self._timers: dict[str, _Timer] = {}
        self._font: pygame.font.Font | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_timer(
        self,
        name: str,
        duration: float,
        on_expire: Callable[[], None] | None = None,
    ) -> None:
        """
        Register a new named countdown timer.

        If a timer with ``name`` already exists it is replaced.

        Parameters
        ----------
        name:
            Unique identifier for the timer (e.g. ``"alarm"``, ``"keypad_grace"``).
        duration:
            Countdown length in seconds.
        on_expire:
            Optional zero-argument callable invoked exactly once when the
            timer reaches zero.
        """
        self._timers[name] = _Timer(
            name=name,
            duration=max(0.0, duration),
            remaining=max(0.0, duration),
            on_expire=on_expire,
        )
        # Notify subscribers that a timer has started.
        EventBus.get().emit("timer_started", {"name": name, "duration": duration})

    def update(self, dt: float) -> None:
        """
        Tick all active timers by ``dt`` seconds.

        Timers that reach zero trigger their callback (if any) and emit a
        ``"timer_expired"`` event.  Expired timers remain in the registry so
        callers can still query their state; use :meth:`cancel` to remove them.

        Parameters
        ----------
        dt:
            Delta time in seconds.
        """
        for timer in list(self._timers.values()):
            if timer.expired:
                continue

            timer.remaining -= dt

            if timer.remaining <= 0.0:
                timer.remaining = 0.0
                timer.expired = True

                # Fire the optional callback.
                if timer.on_expire is not None:
                    try:
                        timer.on_expire()
                    except Exception as exc:  # pragma: no cover
                        # Don't let a bad callback crash the game loop.
                        print(f"[TimerSystem] on_expire raised for '{timer.name}': {exc}")

                # Broadcast the expiry event.
                EventBus.get().emit("timer_expired", {"name": timer.name})

    def get_remaining(self, name: str) -> float:
        """
        Return the seconds remaining on a named timer.

        Parameters
        ----------
        name:
            Timer identifier.

        Returns
        -------
        float
            Remaining seconds.  Returns ``0.0`` if the timer is not found,
            has never been registered, or has already expired.
        """
        timer = self._timers.get(name)
        if timer is None:
            return 0.0
        return timer.remaining

    def cancel(self, name: str) -> None:
        """
        Remove a timer without firing its callback or expiry event.

        Safe to call even if ``name`` does not exist.

        Parameters
        ----------
        name:
            Timer identifier to remove.
        """
        self._timers.pop(name, None)

    def is_active(self, name: str) -> bool:
        """
        Return ``True`` if the named timer exists and has not yet expired.

        Parameters
        ----------
        name:
            Timer identifier.
        """
        timer = self._timers.get(name)
        return timer is not None and not timer.expired

    def draw_hud(
        self,
        surface: pygame.Surface,
        name: str,
        pos: tuple[int, int],
        color: tuple[int, int, int] = (255, 100, 100),
    ) -> None:
        """
        Draw a countdown bar and remaining-seconds label at ``pos``.

        The bar shrinks from full-width to zero as the timer counts down.
        Does nothing if the named timer does not exist.

        Parameters
        ----------
        surface:
            The logical render target.
        name:
            Timer to display.
        pos:
            Top-left corner ``(x, y)`` of the HUD element in screen space.
        color:
            RGB fill colour for the countdown bar (default red).
        """
        timer = self._timers.get(name)
        if timer is None or timer.duration <= 0:
            return

        font = self._get_font()
        x, y = pos

        # --- Background track. ---------------------------------------------
        bg_rect = pygame.Rect(x, y, _BAR_W, _BAR_H)
        pygame.draw.rect(surface, _BAR_BG, bg_rect, border_radius=4)
        pygame.draw.rect(surface, _BAR_BORDER, bg_rect, width=1, border_radius=4)

        # --- Fill bar proportional to remaining time. ----------------------
        fraction = timer.remaining / timer.duration
        fill_w = int(_BAR_W * fraction)
        if fill_w > 0:
            fill_rect = pygame.Rect(x, y, fill_w, _BAR_H)
            pygame.draw.rect(surface, color, fill_rect, border_radius=4)

        # --- Remaining-seconds label to the right of the bar. --------------
        label = f"{timer.remaining:.1f}s"
        label_surf = font.render(label, True, _TEXT_COLOR)
        lx = x + _BAR_W + 6
        ly = y + (_BAR_H - label_surf.get_height()) // 2
        surface.blit(label_surf, (lx, ly))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_font(self) -> pygame.font.Font:
        """Return (and cache) the HUD label font."""
        if self._font is None:
            self._font = pygame.font.Font(None, 20)
        return self._font
