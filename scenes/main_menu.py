"""
scenes/main_menu.py
~~~~~~~~~~~~~~~~~~~
Main menu scene for Verlassen.

Presents the game title, subtitle and three navigation options.
Keyboard navigation: UP/DOWN to move selection, ENTER/SPACE to confirm.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pygame

from config import (
    INTERNAL_W,
    INTERNAL_H,
    PLAYER_NAME,
)
from core.input_handler import InputHandler, Action
from core.save_manager import SaveManager
from core.audio_manager import AudioManager
from scenes.base_scene import BaseScene

if TYPE_CHECKING:
    from core.scene_manager import SceneManager

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
_BG_COLOR = (10, 8, 18)          # #0A0812 – near-black with a purple tint
_TITLE_COLOR = (255, 255, 255)   # Bright white for the game title
_SUBTITLE_COLOR = (140, 130, 155)  # Muted lavender for the subtitle
_OPTION_COLOR = (120, 115, 130)  # Dim gray for unselected options
_SELECTED_COLOR = (220, 215, 230)  # Slightly brighter for selected option
_FOOTER_COLOR = (60, 55, 70)     # Very dim text for the footer hint


class MainMenuScene(BaseScene):
    """The main menu: title, subtitle and New Game / Continue / Quit options.

    Args:
        scene_manager: Owning SceneManager.
    """

    _OPTIONS = ["New Game", "Continue", "Quit"]

    def __init__(self, scene_manager: "SceneManager") -> None:
        super().__init__(scene_manager)
        self._selected: int = 0          # Index into _OPTIONS
        self._has_save: bool = False     # Whether slot 0 has a valid save
        self._alpha: int = 0             # Fade-in alpha (0-255)
        self._fading_in: bool = True

        # Font references (populated in on_enter once pygame is running)
        self._font_title: pygame.font.Font | None = None
        self._font_subtitle: pygame.font.Font | None = None
        self._font_option: pygame.font.Font | None = None
        self._font_footer: pygame.font.Font | None = None

        # Pre-rendered surfaces (populated in on_enter)
        self._title_surf: pygame.Surface | None = None
        self._subtitle_surf: pygame.Surface | None = None
        self._footer_surf: pygame.Surface | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_enter(self) -> None:
        """Load fonts, check for existing save, start menu music."""
        # -- Check save --
        save_data = SaveManager.get().load(slot=0)
        self._has_save = save_data is not None

        # If "Continue" was selected but save no longer exists, reset selection
        if not self._has_save and self._selected == 1:
            self._selected = 0

        # -- Fonts (SysFont fallback; AssetLoader may supply a custom TTF) --
        try:
            from core.asset_loader import AssetLoader
            loader = AssetLoader.get()
            self._font_title = loader.load_font("assets/fonts/main.ttf", 72)
            self._font_subtitle = loader.load_font("assets/fonts/main.ttf", 24)
            self._font_option = loader.load_font("assets/fonts/main.ttf", 36)
            self._font_footer = loader.load_font("assets/fonts/main.ttf", 18)
        except Exception:
            # Graceful fallback to system fonts if custom fonts aren't present
            self._font_title = pygame.font.SysFont("consolas", 72, bold=True)
            self._font_subtitle = pygame.font.SysFont("consolas", 24)
            self._font_option = pygame.font.SysFont("consolas", 36)
            self._font_footer = pygame.font.SysFont("consolas", 18)

        # -- Pre-render static text surfaces --
        self._title_surf = self._font_title.render("VERLASSEN", True, _TITLE_COLOR)
        self._subtitle_surf = self._font_subtitle.render(
            "A story of leaving", True, _SUBTITLE_COLOR
        )
        self._footer_surf = self._font_footer.render(
            "↑↓ Navigate   ENTER Confirm", True, _FOOTER_COLOR
        )

        # -- Fade in --
        self._alpha = 0
        self._fading_in = True

        # -- Music --
        try:
            AudioManager.get().play_music("menu_theme", loop=True, fade_ms=1500)
        except Exception:
            pass  # No audio assets yet — silent is fine

    def on_exit(self) -> None:
        """Stop menu music when leaving this scene."""
        try:
            AudioManager.get().stop_music(fade_ms=500)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Per-frame
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        """Navigate the menu on KEYDOWN events."""
        if event.type != pygame.KEYDOWN:
            return

        input_handler = InputHandler.get()

        if event.key in (pygame.K_UP,):
            self._move_selection(-1)
        elif event.key in (pygame.K_DOWN,):
            self._move_selection(1)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._confirm_selection()

    def update(self, dt: float) -> None:
        """Drive the fade-in animation."""
        if self._fading_in:
            # Fade in over ~0.5 s (alpha increases by 510 per second)
            self._alpha = min(255, self._alpha + int(510 * dt))
            if self._alpha >= 255:
                self._fading_in = False

        # Also support Action-based navigation (rebindable keys)
        input_handler = InputHandler.get()
        if input_handler.is_just_pressed(Action.MOVE_UP):
            self._move_selection(-1)
        elif input_handler.is_just_pressed(Action.MOVE_DOWN):
            self._move_selection(1)
        if input_handler.is_just_pressed(Action.CONFIRM):
            self._confirm_selection()

    def draw(self, surface: pygame.Surface) -> None:
        """Render the main menu."""
        surface.fill(_BG_COLOR)

        # Apply fade-in by drawing a black overlay that decreases in opacity
        if self._fading_in:
            overlay = pygame.Surface((INTERNAL_W, INTERNAL_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 255 - self._alpha))
            surface.blit(overlay, (0, 0))

        cx = INTERNAL_W // 2  # horizontal center

        # -- Title --
        if self._title_surf:
            title_rect = self._title_surf.get_rect(centerx=cx, centery=200)
            surface.blit(self._title_surf, title_rect)

        # -- Subtitle --
        if self._subtitle_surf:
            sub_rect = self._subtitle_surf.get_rect(centerx=cx, centery=258)
            surface.blit(self._subtitle_surf, sub_rect)

        # -- Decorative separator --
        sep_y = 290
        pygame.draw.line(
            surface, (40, 36, 52), (cx - 120, sep_y), (cx + 120, sep_y), 1
        )

        # -- Options --
        option_start_y = 340
        option_gap = 56

        for idx, label in enumerate(self._OPTIONS):
            # Gray out "Continue" when no save exists
            unavailable = (idx == 1 and not self._has_save)
            is_selected = (idx == self._selected)

            if unavailable:
                color = (55, 50, 65)  # Very dim — not interactive
            elif is_selected:
                color = _SELECTED_COLOR
            else:
                color = _OPTION_COLOR

            opt_surf = self._font_option.render(label, True, color)  # type: ignore[union-attr]
            opt_rect = opt_surf.get_rect(
                centerx=cx, centery=option_start_y + idx * option_gap
            )
            surface.blit(opt_surf, opt_rect)

            # Selection indicator: a small dot to the left of selected option
            if is_selected and not unavailable:
                dot_x = opt_rect.left - 16
                dot_y = opt_rect.centery
                pygame.draw.circle(surface, _SELECTED_COLOR, (dot_x, dot_y), 3)

        # -- Footer hint --
        if self._footer_surf:
            foot_rect = self._footer_surf.get_rect(
                centerx=cx, bottom=INTERNAL_H - 24
            )
            surface.blit(self._footer_surf, foot_rect)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _move_selection(self, direction: int) -> None:
        """Move the selection cursor by *direction* (+1 down, -1 up).

        Skips the "Continue" option when no save exists.
        """
        num_options = len(self._OPTIONS)
        for _ in range(num_options):
            self._selected = (self._selected + direction) % num_options
            # Skip "Continue" (index 1) if there is no save
            if self._selected == 1 and not self._has_save:
                continue
            break

    def _confirm_selection(self) -> None:
        """Execute the action for the currently highlighted option."""
        option = self._OPTIONS[self._selected]

        if option == "New Game":
            self._start_new_game()
        elif option == "Continue" and self._has_save:
            self._continue_game()
        elif option == "Quit":
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def _start_new_game(self) -> None:
        """Begin a fresh playthrough from level_01."""
        # Write a fresh save so progress is tracked from the start
        save = SaveManager.get().default_save()
        SaveManager.get().save(slot=0, data=save)

        from scenes.level_scene import LevelScene
        self._scene_manager.switch(LevelScene(self._scene_manager, "level_01_the_house"))

    def _continue_game(self) -> None:
        """Resume from the saved current level."""
        save_data = SaveManager.get().load(slot=0)
        if save_data is None:
            # Edge case: save vanished between on_enter and confirm
            self._has_save = False
            self._selected = 0
            return

        level_id: str = save_data.get("current_level", "level_01_the_house")
        from scenes.level_scene import LevelScene
        self._scene_manager.switch(LevelScene(self._scene_manager, level_id))
