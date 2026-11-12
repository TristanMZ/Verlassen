"""
scenes/__init__.py
==================
Exports all scene classes for Verlassen.
"""

from scenes.base_scene import BaseScene
from scenes.main_menu import MainMenuScene
from scenes.level_scene import LevelScene
from scenes.cutscene_scene import CutsceneScene
from scenes.pause_scene import PauseScene
from scenes.game_over_scene import GameOverScene

__all__ = [
    "BaseScene",
    "MainMenuScene",
    "LevelScene",
    "CutsceneScene",
    "PauseScene",
    "GameOverScene",
]
