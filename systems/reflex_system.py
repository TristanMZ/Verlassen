"""
systems/reflex_system.py
========================
Reflex / Quick-Time-Event (QTE) system for Verlassen.

.. note::
   **STUB — full implementation planned for Level 2.**

   This module provides the public class scaffold and complete docstrings so
   the rest of the codebase can import and reference ``ReflexSystem`` without
   errors.  Every method body raises ``NotImplementedError`` until the Level 2
   sprint implements them.

Architecture (planned)
----------------------
A QTE sequence is a list of action-name strings (e.g. ``["CONFIRM", "CANCEL",
"MOVE_UP"]``) that the player must input in order within a time window.

``start_sequence()`` begins the sequence; ``update()`` checks the input
handler each frame and returns a status string; ``draw()`` renders the
prompt icons to guide the player.
"""

from __future__ import annotations

from typing import Any

import pygame


class ReflexSystem:
    """
    Quick-Time-Event manager.

    Presents a timed input sequence to the player and reports success or
    failure.

    Example (future) usage::

        reflex = ReflexSystem()
        reflex.start_sequence(["CONFIRM", "CANCEL", "MOVE_UP"])

        # Each frame while active:
        status = reflex.update(dt, input_handler)
        reflex.draw(screen)

        if status == "success":
            level.trigger_escape()
        elif status == "fail":
            level.trigger_caught()

    Parameters
    ----------
    time_per_prompt:
        Seconds the player has to press each action in the sequence (planned).
    """

    def __init__(self, time_per_prompt: float = 2.0) -> None:
        """
        Initialise the reflex system.

        Parameters
        ----------
        time_per_prompt:
            Time budget (in seconds) for each individual prompt in a sequence.
            Stored now; honoured in the Level 2 implementation.
        """
        # Configuration (unused until Level 2 implementation).
        self._time_per_prompt: float = time_per_prompt

        # Active sequence state (all None / empty until a sequence starts).
        self._sequence: list[str] = []
        self._current_index: int = 0
        self._prompt_timer: float = 0.0
        self._status: str = "idle"  # "idle" | "ongoing" | "success" | "fail"

    # ------------------------------------------------------------------
    # Public API (STUB)
    # ------------------------------------------------------------------

    def start_sequence(self, sequence: list[str]) -> None:
        """
        Begin a QTE sequence.

        Parameters
        ----------
        sequence:
            Ordered list of action-name strings the player must input.
            Each string corresponds to an action defined in ``InputHandler``
            (e.g. ``"CONFIRM"``, ``"MOVE_UP"``, ``"CANCEL"``).

        Raises
        ------
        NotImplementedError
            Always — pending Level 2 implementation.
        """
        raise NotImplementedError(
            "ReflexSystem.start_sequence() is not yet implemented. "
            "Full QTE logic is scheduled for the Level 2 sprint."
        )

    def update(self, dt: float, input_handler: Any) -> str:
        """
        Process one frame of QTE input checking.

        Parameters
        ----------
        dt:
            Delta time in seconds.
        input_handler:
            The game's ``InputHandler`` instance; exposes
            ``is_just_pressed(action: str) -> bool``.

        Returns
        -------
        str
            One of:

            ``"ongoing"``
                The sequence is active and awaiting further input.
            ``"success"``
                The player completed the full sequence in time.
            ``"fail"``
                The player pressed the wrong key or ran out of time.

        Raises
        ------
        NotImplementedError
            Always — pending Level 2 implementation.
        """
        raise NotImplementedError(
            "ReflexSystem.update() is not yet implemented. "
            "Full QTE logic is scheduled for the Level 2 sprint."
        )

    def draw(self, surface: pygame.Surface) -> None:
        """
        Render the current QTE prompt icons to ``surface``.

        Shows the upcoming action prompts, a per-prompt countdown bar, and
        success/failure feedback animations.

        Parameters
        ----------
        surface:
            The logical (1280×720) render target.

        Raises
        ------
        NotImplementedError
            Always — pending Level 2 implementation.
        """
        raise NotImplementedError(
            "ReflexSystem.draw() is not yet implemented. "
            "Full QTE rendering is scheduled for the Level 2 sprint."
        )

    # ------------------------------------------------------------------
    # Read-only state accessors (safe to call even before Level 2)
    # ------------------------------------------------------------------

    @property
    def status(self) -> str:
        """
        Current sequence status.

        Returns ``"idle"`` when no sequence is running.  Once Level 2 is
        implemented this will also return ``"ongoing"``, ``"success"``, or
        ``"fail"`` during and after a sequence.
        """
        return self._status

    @property
    def is_active(self) -> bool:
        """``True`` while a QTE sequence is in progress."""
        return self._status == "ongoing"
