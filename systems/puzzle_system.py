"""
systems/puzzle_system.py
========================
Puzzle system for Verlassen.

Provides a base class for all in-game puzzles and a concrete ``KeypadPuzzle``
implementation — a 4-digit PIN entry panel used to unlock doors and safes.

Architecture
------------
``BasePuzzle`` defines the solved-state contract and emits a ``"puzzle_solved"``
event on the global ``EventBus`` when :meth:`solve` is called.

``KeypadPuzzle`` extends it with:
  - Digit-by-digit input handling.
  - A simple but readable on-screen keypad UI drawn via pygame primitives.
  - Brief red-flash feedback on wrong entry.
"""

from __future__ import annotations

from typing import Any

import pygame

from config import KEYPAD_CODE_LENGTH
from core.event_bus import EventBus

# ---------------------------------------------------------------------------
# UI constants
# ---------------------------------------------------------------------------

_PANEL_W: int = 160
_PANEL_H: int = 220
_PANEL_COLOR: tuple[int, int, int] = (28, 28, 36)
_PANEL_BORDER: tuple[int, int, int] = (80, 80, 100)
_DISPLAY_H: int = 36
_DISPLAY_COLOR: tuple[int, int, int] = (12, 12, 20)
_DISPLAY_BORDER: tuple[int, int, int] = (60, 60, 80)
_KEY_SIZE: int = 36
_KEY_GAP: int = 6
_KEY_COLOR: tuple[int, int, int] = (50, 50, 70)
_KEY_HOVER: tuple[int, int, int] = (70, 70, 100)
_KEY_TEXT: tuple[int, int, int] = (220, 220, 230)
_CORRECT_COLOR: tuple[int, int, int, int] = (60, 200, 100, 180)
_WRONG_COLOR: tuple[int, int, int, int] = (200, 50, 50, 180)
_WRONG_FLASH_DURATION: float = 0.5  # seconds the red flash persists


class BasePuzzle:
    """
    Abstract base for all Verlassen puzzles.

    Subclasses must override :meth:`handle_input` and :meth:`draw`.

    Attributes
    ----------
    is_solved:
        ``True`` once :meth:`solve` has been called.
    puzzle_id:
        Optional string identifier used in ``"puzzle_solved"`` event data.
    """

    def __init__(self, puzzle_id: str = "") -> None:
        """
        Parameters
        ----------
        puzzle_id:
            Human-readable identifier emitted with the ``"puzzle_solved"``
            event so level scripts can react to specific puzzles.
        """
        self.is_solved: bool = False
        self.puzzle_id: str = puzzle_id

    def solve(self) -> None:
        """
        Mark this puzzle as solved and emit a ``"puzzle_solved"`` event.

        Safe to call multiple times; only the first call has any effect.
        """
        if self.is_solved:
            return
        self.is_solved = True
        EventBus.get().emit(
            "puzzle_solved",
            {"puzzle_id": self.puzzle_id},
        )

    def handle_input(self, key_char: str) -> bool:
        """
        Process a single character of player input.

        Parameters
        ----------
        key_char:
            A single character (digit, letter, etc.) from the player's keypress.

        Returns
        -------
        bool
            ``True`` if this input caused the puzzle to be solved.
        """
        raise NotImplementedError("Subclasses must implement handle_input().")

    def draw(self, surface: pygame.Surface, pos: tuple[int, int]) -> None:
        """
        Render the puzzle UI at screen position ``pos``.

        Parameters
        ----------
        surface:
            The logical render target.
        pos:
            Top-left corner of the puzzle panel in screen space.
        """
        raise NotImplementedError("Subclasses must implement draw().")


class KeypadPuzzle(BasePuzzle):
    """
    A four-digit PIN keypad puzzle.

    The player enters digits one at a time via :meth:`handle_input`.  If the
    full ``code`` is entered correctly the puzzle is solved; a wrong entry
    clears the input and shows a brief red flash.

    Attributes
    ----------
    code:
        The correct PIN (exactly ``KEYPAD_CODE_LENGTH`` digit characters).
    entered:
        Digits entered by the player so far (grows until length == code length).
    """

    def __init__(self, code: str, puzzle_id: str = "") -> None:
        """
        Parameters
        ----------
        code:
            The correct PIN.  Must be a string of ``KEYPAD_CODE_LENGTH`` digit
            characters (e.g. ``"4729"``).
        puzzle_id:
            Forwarded to :class:`BasePuzzle`.
        """
        super().__init__(puzzle_id=puzzle_id)

        if len(code) != KEYPAD_CODE_LENGTH or not code.isdigit():
            raise ValueError(
                f"KeypadPuzzle code must be exactly {KEYPAD_CODE_LENGTH} digits, "
                f"got {code!r}."
            )

        self.code: str = code
        self.entered: str = ""

        # Flash state.
        self._flash_wrong: bool = False
        self._flash_timer: float = 0.0

        # Lazily created font reference.
        self._font: pygame.font.Font | None = None
        self._small_font: pygame.font.Font | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def handle_input(self, key_char: str) -> bool:
        """
        Append a digit character to the current entry.

        If the entry reaches ``KEYPAD_CODE_LENGTH``:
          - Match → :meth:`solve` is called, returns ``True``.
          - Mismatch → entry is cleared, red flash is triggered.

        Non-digit characters are silently ignored.

        Parameters
        ----------
        key_char:
            A single character.  Only ``'0'``–``'9'`` are accepted.

        Returns
        -------
        bool
            ``True`` if the puzzle was just solved by this input.
        """
        if self.is_solved:
            return True

        if not (key_char.isdigit() and len(key_char) == 1):
            return False  # Ignore non-digit input.

        self.entered += key_char

        if len(self.entered) == KEYPAD_CODE_LENGTH:
            if self.entered == self.code:
                self.solve()
                return True
            else:
                # Wrong code — flash and reset.
                self.entered = ""
                self._flash_wrong = True
                self._flash_timer = _WRONG_FLASH_DURATION

        return False

    def update(self, dt: float) -> None:
        """
        Tick the wrong-entry flash timer.

        Call this every frame while the keypad is displayed.

        Parameters
        ----------
        dt:
            Delta time in seconds.
        """
        if self._flash_wrong:
            self._flash_timer -= dt
            if self._flash_timer <= 0.0:
                self._flash_wrong = False
                self._flash_timer = 0.0

    def draw(self, surface: pygame.Surface, pos: tuple[int, int]) -> None:
        """
        Draw the keypad panel at screen position ``pos``.

        Layout (top-to-bottom inside the panel):
          - Dark panel background + border.
          - Digit display strip (shows ``*`` per entered digit).
          - 3×3 digit grid (1–9) + a bottom row with 0.

        A red tint overlays the display briefly after a wrong entry.

        Parameters
        ----------
        surface:
            The logical render target.
        pos:
            Top-left corner ``(x, y)`` of the panel in screen space.
        """
        font = self._get_font()
        small_font = self._get_small_font()
        x, y = pos

        # --- Panel background. ---------------------------------------------
        panel_rect = pygame.Rect(x, y, _PANEL_W, _PANEL_H)
        pygame.draw.rect(surface, _PANEL_COLOR, panel_rect, border_radius=6)
        pygame.draw.rect(surface, _PANEL_BORDER, panel_rect, width=2, border_radius=6)

        # --- Digit display strip. ------------------------------------------
        display_rect = pygame.Rect(x + 10, y + 10, _PANEL_W - 20, _DISPLAY_H)
        pygame.draw.rect(surface, _DISPLAY_COLOR, display_rect, border_radius=4)
        pygame.draw.rect(surface, _DISPLAY_BORDER, display_rect, width=1, border_radius=4)

        # Show entered digits as asterisks (masked).
        display_text = "*" * len(self.entered) + "_" * (KEYPAD_CODE_LENGTH - len(self.entered))
        text_surf = font.render(display_text, True, (200, 220, 200))
        tx = display_rect.centerx - text_surf.get_width() // 2
        ty = display_rect.centery - text_surf.get_height() // 2
        surface.blit(text_surf, (tx, ty))

        # Red flash overlay on wrong entry.
        if self._flash_wrong:
            # Fade the flash as the timer counts down.
            alpha = int((_WRONG_FLASH_DURATION > 0) and
                        (self._flash_timer / _WRONG_FLASH_DURATION) * 180)
            flash_surf = pygame.Surface(display_rect.size, pygame.SRCALPHA)
            flash_surf.fill((*_WRONG_COLOR[:3], alpha))
            surface.blit(flash_surf, display_rect.topleft)

        # --- Digit key grid. -----------------------------------------------
        # Layout: rows of [1,2,3], [4,5,6], [7,8,9], then [0] centred.
        grid_top = y + 10 + _DISPLAY_H + 10
        grid_left = x + (_PANEL_W - (3 * _KEY_SIZE + 2 * _KEY_GAP)) // 2

        digits_grid = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
        ]

        for row_idx, row in enumerate(digits_grid):
            for col_idx, digit in enumerate(row):
                kx = grid_left + col_idx * (_KEY_SIZE + _KEY_GAP)
                ky = grid_top + row_idx * (_KEY_SIZE + _KEY_GAP)
                key_rect = pygame.Rect(kx, ky, _KEY_SIZE, _KEY_SIZE)
                pygame.draw.rect(surface, _KEY_COLOR, key_rect, border_radius=4)
                pygame.draw.rect(surface, _PANEL_BORDER, key_rect, width=1, border_radius=4)

                d_surf = small_font.render(digit, True, _KEY_TEXT)
                dx = key_rect.centerx - d_surf.get_width() // 2
                dy = key_rect.centery - d_surf.get_height() // 2
                surface.blit(d_surf, (dx, dy))

        # Zero key centred below the grid.
        zero_x = grid_left + _KEY_SIZE + _KEY_GAP  # centre column
        zero_y = grid_top + 3 * (_KEY_SIZE + _KEY_GAP)
        zero_rect = pygame.Rect(zero_x, zero_y, _KEY_SIZE, _KEY_SIZE)
        pygame.draw.rect(surface, _KEY_COLOR, zero_rect, border_radius=4)
        pygame.draw.rect(surface, _PANEL_BORDER, zero_rect, width=1, border_radius=4)

        z_surf = small_font.render("0", True, _KEY_TEXT)
        zx = zero_rect.centerx - z_surf.get_width() // 2
        zy = zero_rect.centery - z_surf.get_height() // 2
        surface.blit(z_surf, (zx, zy))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_font(self) -> pygame.font.Font:
        """Return (and cache) the display font."""
        if self._font is None:
            self._font = pygame.font.Font(None, 28)
        return self._font

    def _get_small_font(self) -> pygame.font.Font:
        """Return (and cache) the key-label font."""
        if self._small_font is None:
            self._small_font = pygame.font.Font(None, 22)
        return self._small_font
