"""
core/__init__.py
================
Public interface for core engine modules of Verlassen.
"""

from core.event_bus import (
    EventBus,
    bus,
    EVT_ALERT_RAISED,
    EVT_ALERT_CLEARED,
    EVT_NOISE_EMITTED,
    EVT_PLAYER_HIDDEN,
    EVT_PLAYER_EXPOSED,
    EVT_PUZZLE_SOLVED,
    EVT_PICKUP_COLLECTED,
    EVT_PLAYER_CAUGHT,
    EVT_LEVEL_COMPLETE,
    EVT_SCENE_TRANSITION,
    EVT_NARRATION_TRIGGER,
    EVT_TIMER_STARTED,
    EVT_TIMER_EXPIRED,
)
from core.camera import Camera
from core.input_handler import InputHandler, Action
from core.asset_loader import AssetLoader
from core.audio_manager import AudioManager
from core.save_manager import SaveManager

__all__ = [
    "EventBus",
    "bus",
    "Camera",
    "InputHandler",
    "Action",
    "AssetLoader",
    "AudioManager",
    "SaveManager",
    "EVT_ALERT_RAISED",
    "EVT_ALERT_CLEARED",
    "EVT_NOISE_EMITTED",
    "EVT_PLAYER_HIDDEN",
    "EVT_PLAYER_EXPOSED",
    "EVT_PUZZLE_SOLVED",
    "EVT_PICKUP_COLLECTED",
    "EVT_PLAYER_CAUGHT",
    "EVT_LEVEL_COMPLETE",
    "EVT_SCENE_TRANSITION",
    "EVT_NARRATION_TRIGGER",
    "EVT_TIMER_STARTED",
    "EVT_TIMER_EXPIRED",
]

