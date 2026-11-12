"""
core/event_bus.py — Global publish/subscribe event bus for Verlassen.

Usage
-----
    from core.event_bus import bus

    bus.subscribe("player_caught", my_handler)
    bus.emit("player_caught", {"catcher": "Guard A"})
    bus.unsubscribe("player_caught", my_handler)

All event-name string constants are defined here as module-level names so the
rest of the codebase can import them and avoid typo-prone bare strings.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Callable

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Event-name constants
# Every system that emits or listens to these events should import the
# constant rather than hard-coding the string literal.
# ---------------------------------------------------------------------------

# Stealth / detection
EVT_ALERT_RAISED:   str = "alert_raised"
EVT_ALERT_CLEARED:  str = "alert_cleared"
EVT_NOISE_EMITTED:  str = "noise_emitted"
EVT_PLAYER_HIDDEN:  str = "player_hidden"
EVT_PLAYER_EXPOSED: str = "player_exposed"

# Gameplay milestones
EVT_PUZZLE_SOLVED:    str = "puzzle_solved"
EVT_PICKUP_COLLECTED: str = "pickup_collected"
EVT_PLAYER_CAUGHT:    str = "player_caught"
EVT_LEVEL_COMPLETE:   str = "level_complete"

# Narrative / UI
EVT_SCENE_TRANSITION: str = "scene_transition"
EVT_NARRATION_TRIGGER: str = "narration_trigger"

# Timers
EVT_TIMER_STARTED: str = "timer_started"
EVT_TIMER_EXPIRED: str = "timer_expired"

# ---------------------------------------------------------------------------
# EventBus
# ---------------------------------------------------------------------------

# Type alias for subscriber callbacks
_Handler = Callable[[dict[str, Any]], None]


class EventBus:
    """
    Lightweight global publish/subscribe event bus.

    Subscribers register callbacks keyed to an event name string.  When an
    event is emitted, every registered callback for that name is invoked with
    the accompanying data dictionary.

    Callbacks are called synchronously in the order they were registered.
    Re-entrant emission (emitting inside a handler) is safe — the inner emit
    drains completely before the outer emit continues.
    """

    def __init__(self) -> None:
        # Map: event_name → ordered list of handlers
        self._listeners: defaultdict[str, list[_Handler]] = defaultdict(list)
        # Pending events queued during recursive emit to avoid mutation issues
        self._emitting: bool = False
        self._deferred: list[tuple[str, dict[str, Any]]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def subscribe(self, event: str, callback: _Handler) -> None:
        """
        Register *callback* to be called whenever *event* is emitted.

        Registering the same callback twice for the same event is a no-op
        (the callback will only fire once per emission).
        """
        listeners = self._listeners[event]
        if callback not in listeners:
            listeners.append(callback)

    def unsubscribe(self, event: str, callback: _Handler) -> None:
        """
        Remove *callback* from the listener list for *event*.

        Silently ignores requests to remove a callback that was never
        registered.
        """
        try:
            self._listeners[event].remove(callback)
        except ValueError:
            pass  # callback was never registered — not an error

    def emit(self, event: str, data: dict[str, Any] | None = None) -> None:
        """
        Broadcast *event* to all registered listeners with *data*.

        If emitted from within a handler (re-entrant), the event is queued
        and dispatched after the current dispatch loop completes.

        Parameters
        ----------
        event:
            The event name string (use the EVT_* constants defined above).
        data:
            Arbitrary key/value payload passed verbatim to each handler.
            Defaults to an empty dict when omitted.
        """
        payload: dict[str, Any] = data if data is not None else {}

        if self._emitting:
            # Re-entrant call — defer to avoid mutating the list mid-iteration
            self._deferred.append((event, payload))
            return

        self._emitting = True
        try:
            self._dispatch(event, payload)
            # Drain any events queued by handlers
            while self._deferred:
                deferred_event, deferred_data = self._deferred.pop(0)
                self._dispatch(deferred_event, deferred_data)
        finally:
            self._emitting = False

    def clear(self) -> None:
        """Remove all subscribers (useful for scene teardown / tests)."""
        self._listeners.clear()
        self._deferred.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _dispatch(self, event: str, data: dict[str, Any]) -> None:
        """Invoke all handlers registered for *event*."""
        # Iterate over a snapshot so handlers can safely unsubscribe.
        for handler in list(self._listeners.get(event, [])):
            try:
                handler(data)
            except Exception:
                log.exception(
                    "EventBus: unhandled exception in handler %r for event %r",
                    handler,
                    event,
                )


# ---------------------------------------------------------------------------
# Module-level singleton — the one bus everyone imports
# ---------------------------------------------------------------------------
bus: EventBus = EventBus()
EventBus.get = staticmethod(lambda: bus)

