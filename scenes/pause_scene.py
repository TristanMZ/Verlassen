"""
scenes/pause_scene.py
=====================
Pause overlay scene for Verlassen.
Pushed on top of the LevelScene without destroying its state.
"""

from __future__ import annotations

import pygame

from config import INTERNAL_W, INTERNAL_H
from core.input_handler import InputHandler, Action
from scenes.base_scene import BaseScene


class PauseScene(BaseScene):
    """
    Pause overlay showing Resume, Restart, and Main Menu options.
    """

    OPTIONS = ["Resume", "Restart Level", "Main Menu"]

    def __init__(self, scene_manager) -> None:
        super().__init__(scene_manager)
        self.selected: int = 0
        self.font: pygame.font.Font | None = None
        self.title_font: pygame.font.Font | None = None

    def on_enter(self) -> None:
        self.font = pygame.font.SysFont("consolas", 28)
        self.title_font = pygame.font.SysFont("consolas", 48, bold=True)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_ESCAPE,):
            self._scene_manager.pop()
        elif event.key in (pygame.K_UP, pygame.K_w):
            self.selected = (self.selected - 1) % len(self.OPTIONS)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected = (self.selected + 1) % len(self.OPTIONS)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._confirm()

    def update(self, dt: float) -> None:
        ih = InputHandler.get()
        if ih.is_just_pressed(Action.PAUSE) or ih.is_just_pressed(Action.CANCEL):
            self._scene_manager.pop()
        elif ih.is_just_pressed(Action.MOVE_UP):
            self.selected = (self.selected - 1) % len(self.OPTIONS)
        elif ih.is_just_pressed(Action.MOVE_DOWN):
            self.selected = (self.selected + 1) % len(self.OPTIONS)
        elif ih.is_just_pressed(Action.CONFIRM):
            self._confirm()

    def _confirm(self) -> None:
        choice = self.OPTIONS[self.selected]
        if choice == "Resume":
            self._scene_manager.pop()
        elif choice == "Restart Level":
            self._scene_manager.pop()
            current = self._scene_manager.current
            if hasattr(current, "level_id"):
                from scenes.level_scene import LevelScene
                self._scene_manager.switch(LevelScene(self._scene_manager, current.level_id))
        elif choice == "Main Menu":
            from scenes.main_menu import MainMenuScene
            self._scene_manager.switch(MainMenuScene(self._scene_manager))

    def draw(self, surface: pygame.Surface) -> None:
        # Dark translucent overlay
        overlay = pygame.Surface((INTERNAL_W, INTERNAL_H), pygame.SRCALPHA)
        overlay.fill((8, 6, 12, 200))
        surface.blit(overlay, (0, 0))

        if self.title_font and self.font:
            title_surf = self.title_font.render("PAUSED", True, (240, 240, 250))
            title_rect = title_surf.get_rect(center=(INTERNAL_W // 2, 220))
            surface.blit(title_surf, title_rect)

            for idx, text in enumerate(self.OPTIONS):
                is_sel = idx == self.selected
                color = (255, 255, 255) if is_sel else (140, 140, 150)
                opt_surf = self.font.render(text, True, color)
                opt_rect = opt_surf.get_rect(center=(INTERNAL_W // 2, 330 + idx * 50))
                surface.blit(opt_surf, opt_rect)

                if is_sel:
                    pygame.draw.circle(surface, (255, 255, 255), (opt_rect.left - 20, opt_rect.centery), 4)

