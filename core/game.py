"""
core/game.py
============
Main game loop, window initialization, fixed-timestep execution, and resolution scaling.
"""

from __future__ import annotations

import sys
import pygame

from config import (
    INTERNAL_W,
    INTERNAL_H,
    WINDOW_W,
    WINDOW_H,
    FPS,
)
from core.scene_manager import SceneManager
from core.input_handler import InputHandler
from scenes.main_menu import MainMenuScene


class Game:
    """
    Core game container.
    Manages the window, frame clock, fixed timestep, and root scene manager.
    """

    def __init__(self) -> None:
        pygame.init()
        pygame.font.init()

        # Target window resolution
        self.window = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("Verlassen")

        # Internal logical canvas
        self.canvas = pygame.Surface((INTERNAL_W, INTERNAL_H))

        self.clock = pygame.time.Clock()
        self.is_running = True
        self.scene_manager = SceneManager()
        self.input_handler = InputHandler.get()

        # Start on Main Menu
        self.scene_manager.switch(MainMenuScene(self.scene_manager))

    def run(self) -> None:
        """Main game loop with fixed-timestep physics/logic."""
        dt = 1.0 / FPS

        while self.is_running:
            # 1. Event pumping
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.is_running = False
                else:
                    self.scene_manager.handle_event(event)

            # 2. Input update
            self.input_handler.update()

            # 3. Logic update
            self.scene_manager.update(dt)

            # 4. Render to internal logical canvas
            self.canvas.fill((0, 0, 0))
            self.scene_manager.draw(self.canvas)

            # 5. Upscale canvas to window (nearest-neighbor preserves crisp pixel art)
            scaled = pygame.transform.scale(self.canvas, (WINDOW_W, WINDOW_H))
            self.window.blit(scaled, (0, 0))

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit(0)

