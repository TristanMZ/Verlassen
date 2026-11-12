# Verlassen

A 2D, story-driven stealth game built in Python using Pygame-CE.

> *"Tonight. It has to be tonight. I've been waiting too long already."*

---

## Story Overview

Ren Calloway grew up in a cramped home under the crushing weight of family debt. For two years, he has quietly hidden away \$340 to escape and start fresh. On the night of his escape, he uncovers fragments of a devastating betrayal: his own family signed debts in his name, sold him out to creditors, and skimmed his savings. 

No supernatural elements. Pure tension, stealth, and moral reckoning.

---

## Architecture & Systems

- **Display**: Logical internal resolution of 1280×720 upscaled 2× to crisp 1440p (2560×1440).
- **Game Loop**: Fixed-timestep 60 FPS update cycle (`core/game.py`).
- **Scene Manager**: Stack-based scene manager supporting modals, pause overlay (`push`/`pop`), and level switching (`switch`).
- **Event Bus**: Decoupled pub/sub bus (`core/event_bus.py`) coordinating stealth alerts, pickups, timers, and level transitions.
- **Stealth System**: Continuous line-of-sight raycasting against solid tiles + acoustic noise rings (sneaking, walking, running, floor creaks).
- **Lighting Compositor**: Dynamic darkness overlay (`SRCALPHA` + `BLEND_RGBA_SUB`) with radial light sources, flickering lamps, and subtle visibility radii.
- **Narration System**: Timed inner-monologue subtitles in Ren's voice with fade in/out effects.
- **Data-Driven Levels**: Levels are loaded dynamically from JSON definitions (`map.json`, `entities.json`, `events.json`, `narration.json`).

---

## Installation & Running

### Requirements
- Python 3.11+
- `pygame-ce` >= 2.5.0

```bash
pip install -r requirements.txt
python main.py
```

### Controls

| Action | Key(s) |
|---|---|
| Move | `W`, `A`, `S`, `D` or `Arrow Keys` |
| Sneak (low noise) | Hold `Left Shift` |
| Sprint (fast, loud) | Hold `Left Ctrl` |
| Interact / Read / Enter | `E` |
| Hide in Hiding Spot | `H` or `F` (or `E` when nearby) |
| Pause Game | `Escape` |
| Confirm / Dismiss Note | `Space` / `Enter` |

---

## Level 1 ("The House") Walkthrough

1. **Ren's Bedroom**: Pick up your savings bag (`$340`) from under the desk.
2. **The Hallway**: Watch out for creaky floorboards that alert nearby family members.
3. **Living Room**: Father is sleeping on the couch near the flickering lamp; keep your distance. Check the table for a debt notice addressed to `R. Calloway`.
4. **Kitchen**: Mother paces a short patrol route with an active vision cone. Use furniture to break line of sight, or duck into the bathroom hiding spot if she turns toward you.
5. **Keypad Lock**: Inspect the wall calendar clue (`1947`), then enter the 4-digit code on the front door keypad.
6. **The Escape**: Clearing the front door triggers the timed escape window before the night bus departs.

---

## How to Extend the Game

### Adding a New Level
1. Create a new folder under `levels/level_0X_<name>/`.
2. Provide four JSON files:
   - `map.json`: Tile dimensions, collision layer, and 2D tile arrays.
   - `entities.json`: Player spawn point, NPC patrol paths, interactable objects, and light sources.
   - `events.json`: Trigger zones, event actions, and win/loss transitions.
   - `narration.json`: Story beats and Ren's inner voice keyed to level triggers.
3. Hook the level into `scenes/level_scene.py` or trigger it via `EVT_LEVEL_COMPLETE`.

### Adding a New Puzzle
1. Subclass `BasePuzzle` in `systems/puzzle_system.py`.
2. Implement `handle_input()` and `draw()`.
3. Register your puzzle type with `entities/interactable.py`.

