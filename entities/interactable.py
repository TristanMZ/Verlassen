"""
entities/interactable.py
========================
Interactable entities in Verlassen:
- Doors (locked / unlocked, can require puzzle or key)
- Notes (letters, bills, calendar clues)
- Keypads (triggers KeypadPuzzle)
- Hiding spots (wardrobe, under bed, bathroom)
- Items (savings bag, keys)
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

import pygame

from config import SPRITE_SCALE, TILE_SIZE
from core.event_bus import bus, EVT_PICKUP_COLLECTED, EVT_PLAYER_HIDDEN
from entities.base_entity import BaseEntity
from systems.puzzle_system import KeypadPuzzle

if TYPE_CHECKING:
    from core.camera import Camera
    from entities.player import Player


class Interactable(BaseEntity):
    """
    World object that the player can interact with when within range.
    """

    def __init__(
        self,
        pos: list[float],
        size: tuple[int, int] = (TILE_SIZE, TILE_SIZE),
        interactable_type: str = "note",
        label: str = "Interact",
        data: dict[str, Any] | None = None,
        interaction_radius: float = 48.0,
        sprite: pygame.Surface | None = None,
    ) -> None:
        super().__init__(pos=pos, size=size, sprite=sprite)
        self.interactable_type: str = interactable_type
        self.label: str = label
        self.data: dict[str, Any] = data if data is not None else {}
        self.interaction_radius: float = interaction_radius
        self.is_active: bool = True
        self._interacted: bool = False

        # Color mapping for placeholder representation
        colors = {
            "hiding_spot": (60, 100, 140),
            "note": (220, 220, 180),
            "keypad": (80, 180, 220),
            "door": (140, 80, 40),
            "item": (240, 200, 60),
        }
        self.placeholder_color: tuple[int, int, int] = colors.get(
            interactable_type, (180, 180, 180)
        )

    def is_in_range(self, player_center: tuple[float, float]) -> bool:
        """Check if player center is within interaction radius."""
        if not self.active or not self.is_active:
            return False
        cx, cy = self.center
        px, py = player_center
        return math.hypot(cx - px, cy - py) <= self.interaction_radius

    def interact(self, player: Player) -> dict[str, Any]:
        """
        Execute interaction and return a result dictionary describing what occurred.
        """
        if not self.is_active:
            return {"type": "none"}

        res: dict[str, Any] = {
            "type": self.interactable_type,
            "id": self.data.get("id", ""),
            "data": self.data,
        }

        if self.interactable_type == "hiding_spot":
            if not player.is_hidden:
                player.try_hide(self)
                res["action"] = "entered_hide"
            else:
                player.expose()
                res["action"] = "exited_hide"

        elif self.interactable_type == "note":
            res["text"] = self.data.get("text", "")
            res["narration_trigger"] = self.data.get("narration_trigger")
            res["flag_set"] = self.data.get("flag_set")
            self._interacted = True

        elif self.interactable_type == "keypad":
            code = self.data.get("code", "0000")
            res["puzzle"] = KeypadPuzzle(code=code)

        elif self.interactable_type == "item":
            savings_add = self.data.get("savings_add", 0)
            if savings_add > 0:
                player.savings += savings_add
                res["savings_added"] = savings_add

            bus.emit(EVT_PICKUP_COLLECTED, {"item": self.data, "label": self.label})

            if self.data.get("one_shot", True):
                self.is_active = False
                self.visible = False
            self._interacted = True

        elif self.interactable_type == "door":
            res["is_locked"] = self.data.get("locked", False)

        return res

    def draw_prompt(self, surface: pygame.Surface, camera: Camera, font: pygame.font.Font) -> None:
        """Draw interaction prompt floating above the interactable."""
        if not self.is_active:
            return

        sx, sy = camera.world_to_screen(self.pos)
        prompt_surf = font.render(f"[E] {self.label}", True, (255, 255, 255))

        bg_rect = prompt_surf.get_rect(midbottom=(sx + self.size[0] // 2, sy - 6))
        bg_surface = pygame.Surface((bg_rect.width + 8, bg_rect.height + 4), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 180))

        surface.blit(bg_surface, (bg_rect.x - 4, bg_rect.y - 2))
        surface.blit(prompt_surf, bg_rect)

    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        """Draw placeholder or assigned sprite."""
        if not self.visible:
            return

        sx, sy = camera.world_to_screen(self.pos)
        if self.sprite is not None:
            surface.blit(self.sprite, (sx, sy))
        else:
            # Draw placeholder colored box
            rect = pygame.Rect(sx, sy, self.size[0], self.size[1])
            pygame.draw.rect(surface, self.placeholder_color, rect)
            pygame.draw.rect(surface, (255, 255, 255), rect, width=1)

