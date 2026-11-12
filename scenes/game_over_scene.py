"""
scenes/game_over_scene.py
=========================
Game Over scene for Verlassen when Ren is caught.
"""

from __future__ import annotations

import pygame

from config import INTERNAL_W, INTERNAL_H
from core.input_handler import InputHandler, Action
from scenes.base_scene import BaseScene


class GameOverScene(BaseScene):
    """
    Game Over screen shown upon detection/capture.
    """

    OPTIONS = ["Try Again", "Main Menu"]

    def __init__(self, scene_manager, level_id: str = "level_01_the_house") -> None:
        super().__init__(scene_manager)
        self.level_id = level_id
        self.selected: int = 0
        self.font: pygame.font.Font | None = None
        self.title_font: pygame.font.Font | None = None
        self.quote_font: pygame.font.Font | None = None

    def on_enter(self) -> None:
        self.font = pygame.font.SysFont("consolas", 28)
        self.title_font = pygame.font.SysFont("consolas", 64, bold=True)
        self.quote_font = pygame.font.SysFont("georgia", 22, italic=True)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_UP, pygame.K_w):
            self.selected = (self.selected - 1) % len(self.OPTIONS)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected = (self.selected + 1) % len(self.OPTIONS)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._confirm()

    def update(self, dt: float) -> None:
        ih = InputHandler.get()
        if ih.is_just_pressed(Action.MOVE_UP):
            self.selected = (self.selected - 1) % len(self.OPTIONS)
        elif ih.is_just_pressed(Action.MOVE_DOWN):
            self.selected = (self.selected + 1) % len(self.OPTIONS)
        elif ih.is_just_pressed(Action.CONFIRM):
            self._confirm()

    def _confirm(self) -> None:
        choice = self.OPTIONS[self.selected]
        if choice == "Try Again":
            from scenes.level_scene import LevelScene
            self._scene_manager.switch(LevelScene(self._scene_manager, self.level_id))
        elif choice == "Main Menu":
            from scenes.main_menu import MainMenuScene
            self._scene_manager.switch(MainMenuScene(self._scene_manager))

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((16, 6, 8))

        # Vignette / subtle red edge accent
        vignette = pygame.Surface((INTERNAL_W, INTERNAL_H), pygame.SRCALPHA)
        pygame.draw.rect(vignette, (180, 20, 20, 45), (0, 0, INTERNAL_W, INTERNAL_H), width=18)
        surface.blit(vignette, (0, 0))

        if self.title_font and self.font and self.quote_font:
            title_surf = self.title_font.render("CAUGHT", True, (240, 220, 220))
            title_rect = title_surf.get_rect(center=(INTERNAL_W // 2, 200))
            surface.blit(title_surf, title_rect)

            quote_surf = self.quote_font.render('"Not like this."', True, (190, 160, 160))
            quote_rect = quote_surf.get_rect(center=(INTERNAL_W // 2, 265))
            surface.blit(quote_surf, quote_rect)

            for idx, text in enumerate(self.OPTIONS):
                is_sel = idx == self.selected
                color = (255, 255, 255) if is_sel else (140, 120, 120)
                opt_surf = self.font.render(text, True, color)
                opt_rect = opt_surf.get_rect(center=(INTERNAL_W // 2, 370 + idx * 50))
                surface.blit(opt_surf, opt_rect)

                if is_sel:
                    pygame.draw.circle(surface, (240, 80, 80), (opt_rect.left - 20, opt_rect.centery), 4)

