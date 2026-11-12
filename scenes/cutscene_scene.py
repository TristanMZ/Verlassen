"""
scenes/cutscene_scene.py
========================
Narrative cutscene cards with fade-in and text sequence.
"""

from __future__ import annotations

import pygame

from config import INTERNAL_W, INTERNAL_H
from core.input_handler import InputHandler, Action
from scenes.base_scene import BaseScene


class CutsceneScene(BaseScene):
    """
    Renders story narration beats between levels.
    """

    def __init__(
        self,
        scene_manager,
        cutscene_id: str,
        next_scene_type: str = "level",
        next_scene_param: str = "level_02_neighborhood",
    ) -> None:
        super().__init__(scene_manager)
        self.cutscene_id = cutscene_id
        self.next_scene_type = next_scene_type
        self.next_scene_param = next_scene_param

        self.cards: list[str] = [
            "The front door clicked shut.",
            "Cold night air. The city smelled like wet asphalt and burning coal.",
            "In my jacket pocket, three hundred and forty dollars.",
            "I didn't look back.",
        ]
        self.card_index: int = 0
        self.elapsed: float = 0.0
        self.card_duration: float = 4.5
        self.font: pygame.font.Font | None = None

    def on_enter(self) -> None:
        self.font = pygame.font.SysFont("georgia", 24, italic=True)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
            self._advance()

    def update(self, dt: float) -> None:
        ih = InputHandler.get()
        if ih.is_just_pressed(Action.CONFIRM):
            self._advance()
            return

        self.elapsed += dt
        if self.elapsed >= self.card_duration:
            self._advance()

    def _advance(self) -> None:
        self.elapsed = 0.0
        self.card_index += 1
        if self.card_index >= len(self.cards):
            self._finish()

    def _finish(self) -> None:
        from scenes.main_menu import MainMenuScene
        # When cutscene ends, go to next level or main menu
        self._scene_manager.switch(MainMenuScene(self._scene_manager))

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((8, 6, 12))

        if self.font and self.card_index < len(self.cards):
            text = self.cards[self.card_index]
            text_surf = self.font.render(text, True, (230, 230, 240))
            rect = text_surf.get_rect(center=(INTERNAL_W // 2, INTERNAL_H // 2))
            surface.blit(text_surf, rect)

            hint_font = pygame.font.SysFont("consolas", 14)
            hint_surf = hint_font.render("[SPACE] to continue", True, (90, 80, 100))
            hint_rect = hint_surf.get_rect(center=(INTERNAL_W // 2, INTERNAL_H - 40))
            surface.blit(hint_surf, hint_rect)

