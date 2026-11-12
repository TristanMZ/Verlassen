"""
core/input_handler.py — Unified keyboard input handler for Verlassen.

All game actions are defined as string constants (Action.*).  Keys are
rebindable at runtime by modifying the ``bindings`` dict.  The handler is
updated once per frame and exposes three query methods that scenes/entities
call to read input state without touching pygame directly.

Usage
-----
    from core.input_handler import InputHandler, Action

    ih = InputHandler()

    # In the game loop:
    ih.update()

    # In entity/scene update code:
    if ih.is_held(Action.SNEAK):
        player.sneak()
    if ih.is_just_pressed(Action.INTERACT):
        player.try_interact()
"""

from __future__ import annotations

import pygame


# ---------------------------------------------------------------------------
# Action constants
# ---------------------------------------------------------------------------

class Action:
    """Namespace of string constants for every bindable game action."""

    MOVE_UP:    str = "move_up"
    MOVE_DOWN:  str = "move_down"
    MOVE_LEFT:  str = "move_left"
    MOVE_RIGHT: str = "move_right"

    SNEAK:    str = "sneak"     # hold Left Shift
    RUN:      str = "run"       # hold Left Ctrl
    INTERACT: str = "interact"  # E
    HIDE:     str = "hide"      # H or F

    PAUSE:    str = "pause"    # Escape
    CONFIRM:  str = "confirm"  # Enter / Space
    CANCEL:   str = "cancel"   # Escape / Backspace


# ---------------------------------------------------------------------------
# Default key bindings
# Each action maps to a *list* of pygame key constants so multiple keys can
# trigger the same action without special-casing.
# ---------------------------------------------------------------------------

DEFAULT_BINDINGS: dict[str, list[int]] = {
    Action.MOVE_UP:    [pygame.K_UP,   pygame.K_w],
    Action.MOVE_DOWN:  [pygame.K_DOWN, pygame.K_s],
    Action.MOVE_LEFT:  [pygame.K_LEFT, pygame.K_a],
    Action.MOVE_RIGHT: [pygame.K_RIGHT, pygame.K_d],

    Action.SNEAK:    [pygame.K_LSHIFT],
    Action.RUN:      [pygame.K_LCTRL],
    Action.INTERACT: [pygame.K_e],
    Action.HIDE:     [pygame.K_h, pygame.K_f],

    Action.PAUSE:   [pygame.K_ESCAPE],
    Action.CONFIRM: [pygame.K_RETURN, pygame.K_SPACE],
    Action.CANCEL:  [pygame.K_ESCAPE, pygame.K_BACKSPACE],
}


# ---------------------------------------------------------------------------
# InputHandler
# ---------------------------------------------------------------------------

class InputHandler:
    """
    Frame-accurate keyboard input tracker.

    Call ``update()`` once at the start of each game-loop iteration, **after**
    pumping the pygame event queue but **before** running any scene or entity
    logic.

    Key-state snapshots are taken at ``update()`` time so that
    ``is_just_pressed`` / ``is_just_released`` remain stable for the entire
    frame.
    """

    def __init__(self) -> None:
        # Active bindings (action → list of pygame key codes).  Copy defaults
        # so callers can mutate without affecting the class-level dict.
        self.bindings: dict[str, list[int]] = {
            action: list(keys) for action, keys in DEFAULT_BINDINGS.items()
        }

        # Snapshots of pygame key state for current and previous frame
        self._prev_keys: pygame.key.ScancodeWrapper | None = None
        self._curr_keys: pygame.key.ScancodeWrapper | None = None

    # ------------------------------------------------------------------
    # Frame update
    # ------------------------------------------------------------------

    def update(self) -> None:
        """
        Capture the current keyboard state.

        Must be called once per frame, before querying any action state.
        The previous frame's snapshot is preserved to compute just-pressed and
        just-released transitions.
        """
        self._prev_keys = self._curr_keys
        # pygame.key.get_pressed() returns a ScancodeWrapper (sequence indexed
        # by pygame.K_* constants) reflecting every key's held state.
        self._curr_keys = pygame.key.get_pressed()

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def is_held(self, action: str) -> bool:
        """
        Return True if *any* key bound to *action* is currently held.

        Parameters
        ----------
        action:
            One of the ``Action.*`` string constants.
        """
        if self._curr_keys is None:
            return False
        return any(self._curr_keys[key] for key in self.bindings.get(action, []))

    def is_just_pressed(self, action: str) -> bool:
        """
        Return True if *action* transitioned from released to held this frame.

        Parameters
        ----------
        action:
            One of the ``Action.*`` string constants.
        """
        if self._curr_keys is None or self._prev_keys is None:
            return False
        keys = self.bindings.get(action, [])
        # Pressed this frame AND not pressed last frame
        return any(self._curr_keys[k] and not self._prev_keys[k] for k in keys)

    def is_just_released(self, action: str) -> bool:
        """
        Return True if *action* transitioned from held to released this frame.

        Parameters
        ----------
        action:
            One of the ``Action.*`` string constants.
        """
        if self._curr_keys is None or self._prev_keys is None:
            return False
        keys = self.bindings.get(action, [])
        # Was pressed last frame AND not pressed this frame
        return any(not self._curr_keys[k] and self._prev_keys[k] for k in keys)

    # ------------------------------------------------------------------
    # Rebinding helpers
    # ------------------------------------------------------------------

    def bind(self, action: str, key: int, exclusive: bool = False) -> None:
        """
        Bind *key* to *action*.

        Parameters
        ----------
        action:
            One of the ``Action.*`` string constants.
        key:
            A ``pygame.K_*`` integer constant.
        exclusive:
            If True, replace the existing binding list entirely; otherwise
            append to it.
        """
        if exclusive:
            self.bindings[action] = [key]
        else:
            if key not in self.bindings.get(action, []):
                self.bindings.setdefault(action, []).append(key)

    def unbind(self, action: str, key: int) -> None:
        """Remove *key* from the binding list for *action* (no-op if absent)."""
        try:
            self.bindings[action].remove(key)
        except (KeyError, ValueError):
            pass

    def reset_bindings(self) -> None:
        """Restore all bindings to the defaults defined in DEFAULT_BINDINGS."""
        self.bindings = {
            action: list(keys) for action, keys in DEFAULT_BINDINGS.items()
        }


# Global singleton instance
input_handler: InputHandler = InputHandler()
InputHandler.get = staticmethod(lambda: input_handler)

