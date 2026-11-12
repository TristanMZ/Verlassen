"""
scenes/level_scene.py
=====================
Generic data-driven level scene for Verlassen.
Hosts gameplay: TileMap, Player, NPCs, Interactables, StealthSystem, LightingSystem, NarrationSystem, and TimerSystem.
"""

from __future__ import annotations

import json
import os
from typing import Any

import pygame

from config import (
    INTERNAL_W,
    INTERNAL_H,
    TILE_SIZE,
    SPRITE_SCALE,
    NOISE_CREAK,
    DATA_ENCODING,
)
from core.event_bus import (
    bus,
    EVT_PLAYER_CAUGHT,
    EVT_LEVEL_COMPLETE,
    EVT_PUZZLE_SOLVED,
    EVT_TIMER_EXPIRED,
)
from core.camera import Camera
from core.input_handler import InputHandler, Action
from core.save_manager import SaveManager
from core.audio_manager import AudioManager

from systems.stealth_system import StealthSystem
from systems.lighting_system import LightingSystem
from systems.narration_system import NarrationSystem
from systems.timer_system import TimerSystem
from systems.puzzle_system import KeypadPuzzle

from entities.player import Player
from entities.npc import NPC
from entities.enemy import Enemy
from entities.interactable import Interactable
from scenes.base_scene import BaseScene


class TileMap:
    """
    Manages multi-layer tile grid and collisions.
    """

    def __init__(self, map_data: dict[str, Any]) -> None:
        self.meta = map_data.get("meta", {})
        self.width: int = self.meta.get("width", 40)
        self.height: int = self.meta.get("height", 25)
        self.tile_size: int = self.meta.get("tile_size", TILE_SIZE)

        self.collision_layer_name = map_data.get("collision_layer", "walls")
        self.creak_tiles: set[int] = set(map_data.get("creak_tiles", [3]))

        self.layers: dict[str, list[list[int]]] = {}
        for layer in map_data.get("layers", []):
            name = layer.get("name")
            self.layers[name] = layer.get("tiles", [])

        # Color palette for placeholder tile rendering
        self.tile_colors = {
            1: (42, 40, 48),    # Walkable floor
            2: (22, 20, 28),    # Solid wall
            3: (64, 48, 36),    # Creaky floor board
            4: (84, 52, 32),    # Doorway
        }

    def is_solid(self, tile_x: int, tile_y: int) -> bool:
        """Check if tile at coordinate is solid wall or out of bounds."""
        if tile_x < 0 or tile_x >= self.width or tile_y < 0 or tile_y >= self.height:
            return True
        walls = self.layers.get(self.collision_layer_name)
        if walls and 0 <= tile_y < len(walls) and 0 <= tile_x < len(walls[tile_y]):
            return walls[tile_y][tile_x] != 0
        return False

    def is_creak(self, tile_x: int, tile_y: int) -> bool:
        """Check if stepping here makes floor creak noise."""
        floor = self.layers.get("floor")
        if floor and 0 <= tile_y < len(floor) and 0 <= tile_x < len(floor[tile_y]):
            return floor[tile_y][tile_x] in self.creak_tiles
        return False

    def draw(self, surface: pygame.Surface, camera: Camera, layer_name: str) -> None:
        """Draw visible tiles for specified layer."""
        tiles = self.layers.get(layer_name)
        if not tiles:
            return

        for y, row in enumerate(tiles):
            for x, tile_id in enumerate(row):
                if tile_id == 0:
                    continue
                wx = x * self.tile_size
                wy = y * self.tile_size
                sx, sy = camera.world_to_screen((wx, wy))

                # Viewport culling
                if -self.tile_size <= sx <= INTERNAL_W and -self.tile_size <= sy <= INTERNAL_H:
                    color = self.tile_colors.get(tile_id, (50, 50, 50))
                    rect = pygame.Rect(sx, sy, self.tile_size, self.tile_size)
                    pygame.draw.rect(surface, color, rect)
                    # Subtle tile border for clarity
                    if tile_id in (2, 3):
                        pygame.draw.rect(surface, (color[0] + 15, color[1] + 15, color[2] + 15), rect, width=1)


class LevelScene(BaseScene):
    """
    Core gameplay scene for any level.
    """

    def __init__(self, scene_manager, level_id: str = "level_01_the_house") -> None:
        super().__init__(scene_manager)
        self.level_id = level_id

        # Systems
        self.camera = Camera(INTERNAL_W, INTERNAL_H)
        self.stealth_system = StealthSystem()
        self.lighting_system = LightingSystem()
        self.narration_system = NarrationSystem()
        self.timer_system = TimerSystem()

        # Entities
        self.player: Player | None = None
        self.npcs: list[NPC] = []
        self.interactables: list[Interactable] = []
        self.tile_map: TileMap | None = None

        # Level data
        self.map_data: dict[str, Any] = {}
        self.entities_data: dict[str, Any] = {}
        self.events_data: dict[str, Any] = {}
        self.narration_data: dict[str, Any] = {}

        # State
        self.story_flags: dict[str, Any] = {}
        self.active_puzzle: KeypadPuzzle | None = None
        self.active_note_text: str | None = None
        self.font = pygame.font.SysFont("consolas", 18)
        self.hud_font = pygame.font.SysFont("consolas", 22, bold=True)

    def on_enter(self) -> None:
        """Load data and initialize world."""
        level_dir = os.path.join("levels", self.level_id)

        # 1. Load JSON data files
        with open(os.path.join(level_dir, "map.json"), "r", encoding=DATA_ENCODING) as f:
            self.map_data = json.load(f)
        with open(os.path.join(level_dir, "entities.json"), "r", encoding=DATA_ENCODING) as f:
            self.entities_data = json.load(f)
        with open(os.path.join(level_dir, "events.json"), "r", encoding=DATA_ENCODING) as f:
            self.events_data = json.load(f)
        with open(os.path.join(level_dir, "narration.json"), "r", encoding=DATA_ENCODING) as f:
            self.narration_data = json.load(f)

        # 2. Setup map
        self.tile_map = TileMap(self.map_data)

        # 3. Setup player
        spawn = self.entities_data.get("player_spawn", {"x": 64, "y": 576})
        self.player = Player(pos=[float(spawn["x"]), float(spawn["y"])])

        # 4. Setup NPCs
        self.npcs.clear()
        for npc_def in self.entities_data.get("npcs", []):
            pos = [float(npc_def["pos"][0]), float(npc_def["pos"][1])]
            npc = NPC(
                pos=pos,
                name=npc_def.get("name", "NPC"),
                patrol_path=[(float(p[0]), float(p[1])) for p in npc_def.get("patrol_path", [])],
                patrol_wait=float(npc_def.get("patrol_wait", 2.0)),
                fov_degrees=float(npc_def.get("fov_degrees", 90)),
                vision_range=int(npc_def.get("vision_range", 180)),
                dialogue_key=npc_def.get("dialogue_key", ""),
            )
            npc.facing_angle = float(npc_def.get("facing_angle", 0))
            self.npcs.append(npc)

        # 5. Setup Interactables
        self.interactables.clear()
        for obj in self.entities_data.get("interactables", []):
            item = Interactable(
                pos=[float(obj["pos"][0]), float(obj["pos"][1])],
                interactable_type=obj.get("type", "note"),
                label=obj.get("label", "Interact"),
                data=obj.get("data", {}),
            )
            self.interactables.append(item)

        # 6. Event subscriptions
        bus.subscribe(EVT_PLAYER_CAUGHT, self._on_player_caught)
        bus.subscribe(EVT_LEVEL_COMPLETE, self._on_level_complete)
        bus.subscribe(EVT_PUZZLE_SOLVED, self._on_puzzle_solved)
        bus.subscribe(EVT_TIMER_EXPIRED, self._on_timer_expired)

        # 7. Start intro narration
        self.narration_system.trigger("intro", self.narration_data)

    def on_exit(self) -> None:
        """Unsubscribe from events to prevent dangling references."""
        bus.unsubscribe(EVT_PLAYER_CAUGHT, self._on_player_caught)
        bus.unsubscribe(EVT_LEVEL_COMPLETE, self._on_level_complete)
        bus.unsubscribe(EVT_PUZZLE_SOLVED, self._on_puzzle_solved)
        bus.unsubscribe(EVT_TIMER_EXPIRED, self._on_timer_expired)

    def _on_player_caught(self, data: dict[str, Any]) -> None:
        from scenes.game_over_scene import GameOverScene
        self._scene_manager.switch(GameOverScene(self._scene_manager, self.level_id))

    def _on_level_complete(self, data: dict[str, Any]) -> None:
        SaveManager.get().set_flag(f"{self.level_id}_complete", True)
        from scenes.cutscene_scene import CutsceneScene
        self._scene_manager.switch(CutsceneScene(self._scene_manager, "cutscene_01"))

    def _on_puzzle_solved(self, data: dict[str, Any]) -> None:
        self.story_flags["keypad_front_solved"] = True
        SaveManager.get().set_flag("keypad_front_solved", True)
        self.active_puzzle = None
        self.narration_system.queue_text("Keypad unlocked. The door clicked open.", 3.5)

    def _on_timer_expired(self, data: dict[str, Any]) -> None:
        if data.get("name") == "escape_clock":
            # If player didn't exit in time
            bus.emit(EVT_PLAYER_CAUGHT, {"reason": "time_expired"})

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        # Handle modal popups first
        if self.active_puzzle is not None:
            if event.key == pygame.K_ESCAPE:
                self.active_puzzle = None
            elif event.unicode and (event.unicode.isdigit() or event.key == pygame.K_BACKSPACE):
                key_char = "\b" if event.key == pygame.K_BACKSPACE else event.unicode
                self.active_puzzle.handle_input(key_char)
            return

        if self.active_note_text is not None:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_e):
                self.active_note_text = None
            return

        # Game pause
        if event.key == pygame.K_ESCAPE:
            from scenes.pause_scene import PauseScene
            self._scene_manager.push(PauseScene(self._scene_manager))

    def update(self, dt: float) -> None:
        if self.active_puzzle is not None or self.active_note_text is not None:
            return

        ih = InputHandler.get()

        # 1. Update player
        if self.player:
            self.player.update(dt, self.tile_map)

            # Check if stepping on creaky floor tile
            tx = int(self.player.center[0] // TILE_SIZE)
            ty = int(self.player.center[1] // TILE_SIZE)
            if self.tile_map.is_creak(tx, ty) and self.player.movement_state in ("walking", "running"):
                self.player.noise_level = NOISE_CREAK

        # 2. Update NPCs
        for npc in self.npcs:
            npc.update(dt, player=self.player, tile_map=self.tile_map)


        # 3. Update Stealth System
        if self.player:
            self.stealth_system.update(dt, self.npcs, self.player, self.tile_map)

        # 4. Check Trigger Zones
        self._check_triggers()

        # 5. Check Interactables
        if self.player and ih.is_just_pressed(Action.INTERACT):
            self._handle_interaction()

        # 6. Update narration & timers
        self.narration_system.update(dt)
        self.timer_system.update(dt)

        # 7. Update camera
        if self.player:
            self.camera.follow(self.player.center, dt)


        # 8. Rebuild dynamic lights for this frame
        self._update_lighting()

    def _check_triggers(self) -> None:
        if not self.player:
            return
        px, py = self.player.center
        for zone in self.events_data.get("trigger_zones", []):
            if zone.get("_triggered", False) and zone.get("one_shot", True):
                continue

            rx, ry, rw, rh = zone["rect"]
            if rx <= px <= rx + rw and ry <= py <= ry + rh:
                req_flag = zone.get("requires_flag")
                if req_flag and not self.story_flags.get(req_flag, False):
                    continue

                zone["_triggered"] = True
                for action in zone.get("actions", []):
                    act_type = action.get("type")
                    if act_type == "narration":
                        self.narration_system.trigger(action["key"], self.narration_data)
                    elif act_type == "audio_tension":
                        AudioManager.get().set_tension(float(action.get("value", 0.5)))
                    elif act_type == "timer_start":
                        self.timer_system.add_timer(action["name"], float(action["duration"]))
                    elif act_type == "level_complete":
                        bus.emit(EVT_LEVEL_COMPLETE, {"level": self.level_id})

    def _handle_interaction(self) -> None:
        if not self.player:
            return
        p_center = self.player.center
        for obj in self.interactables:
            if obj.is_in_range(p_center):
                res = obj.interact(self.player)
                obj_type = res.get("type")

                if obj_type == "note":
                    self.active_note_text = res.get("text", "")
                    if res.get("flag_set"):
                        self.story_flags[res["flag_set"]] = True
                        SaveManager.get().set_flag(res["flag_set"], True)
                    if res.get("narration_trigger"):
                        self.narration_system.trigger(res["narration_trigger"], self.narration_data)

                elif obj_type == "keypad":
                    self.active_puzzle = res.get("puzzle")

                elif obj_type == "item":
                    if obj.data.get("narration_trigger"):
                        self.narration_system.trigger(obj.data["narration_trigger"], self.narration_data)
                break

    def _update_lighting(self) -> None:
        self.lighting_system.clear_lights()

        # Add level light sources
        for light in self.entities_data.get("light_sources", []):
            self.lighting_system.add_light(
                pos=(float(light["pos"][0]), float(light["pos"][1])),
                radius=float(light.get("radius", 60)),
                color=tuple(light.get("color", [255, 220, 150])),
                intensity=float(light.get("intensity", 0.8)),
                flicker=light.get("flicker", False),
            )

        # Player's personal visibility radius
        if self.player:
            self.lighting_system.add_light(
                pos=self.player.center,
                radius=45.0,
                color=(220, 230, 255),
                intensity=0.5,
                flicker=False,
            )

    def draw(self, surface: pygame.Surface) -> None:
        if not self.tile_map or not self.player:
            return

        # 1. Floor & Walls
        self.tile_map.draw(surface, self.camera, "floor")
        self.tile_map.draw(surface, self.camera, "walls")

        # 2. Interactables
        for obj in self.interactables:
            obj.draw(surface, self.camera)
            if obj.is_in_range(self.player.center):
                obj.draw_prompt(surface, self.camera, self.font)

        # 3. NPCs
        for npc in self.npcs:
            npc.draw(surface, self.camera)

        # 4. Player
        self.player.draw(surface, self.camera)

        # 5. Vision cones (debug overlay)
        self.stealth_system.draw_debug(surface, self.camera, self.npcs)

        # 6. Lighting Compositor
        self.lighting_system.render(surface, self.camera)

        # 7. Narration subtitles
        self.narration_system.draw(surface)

        # 8. Escape Clock HUD
        rem = self.timer_system.get_remaining("escape_clock")
        if rem > 0:
            time_text = f"ESCAPE BUS: {rem:04.1f}s"
            t_surf = self.hud_font.render(time_text, True, (255, 100, 100))
            surface.blit(t_surf, (INTERNAL_W // 2 - t_surf.get_width() // 2, 20))

        # 9. Savings HUD
        sav_text = f"SAVINGS: ${self.player.savings:.0f}"
        s_surf = self.hud_font.render(sav_text, True, (240, 220, 140))
        surface.blit(s_surf, (INTERNAL_W - s_surf.get_width() - 20, 20))

        # 10. Modals (Notes & Keypad)
        if self.active_note_text:
            self._draw_note_modal(surface)
        elif self.active_puzzle:
            self.active_puzzle.draw(surface, (INTERNAL_W // 2 - 120, INTERNAL_H // 2 - 140))

    def _draw_note_modal(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((INTERNAL_W, INTERNAL_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        box_w, box_h = 560, 200
        bx = (INTERNAL_W - box_w) // 2
        by = (INTERNAL_H - box_h) // 2
        pygame.draw.rect(surface, (230, 220, 190), (bx, by, box_w, box_h))
        pygame.draw.rect(surface, (60, 40, 20), (bx, by, box_w, box_h), width=2)

        note_font = pygame.font.SysFont("georgia", 20)
        # Word wrap text simply
        words = self.active_note_text.split(" ")
        lines = []
        cur_line = ""
        for word in words:
            test = cur_line + (" " if cur_line else "") + word
            if note_font.size(test)[0] < box_w - 40:
                cur_line = test
            else:
                lines.append(cur_line)
                cur_line = word
        if cur_line:
            lines.append(cur_line)

        for i, l in enumerate(lines):
            line_surf = note_font.render(l, True, (20, 15, 10))
            surface.blit(line_surf, (bx + 20, by + 25 + i * 28))

        close_font = pygame.font.SysFont("consolas", 14)
        close_surf = close_font.render("[SPACE] Close", True, (100, 80, 60))
        surface.blit(close_surf, (bx + box_w - close_surf.get_width() - 15, by + box_h - 25))
