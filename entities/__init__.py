"""
entities/__init__.py
====================
Public surface of the entities package for Verlassen.

Importing from this module gives callers access to all entity classes
without needing to know their internal file locations.
"""

from entities.base_entity import BaseEntity
from entities.player import Player
from entities.npc import NPC
from entities.enemy import Enemy
from entities.interactable import Interactable, KeypadPuzzle

__all__ = [
    "BaseEntity",
    "Player",
    "NPC",
    "Enemy",
    "Interactable",
    "KeypadPuzzle",
]
