"""
core/save_manager.py — JSON-based save / load system for Verlassen.

Save files are stored as pretty-printed JSON in ``saves/save_{slot}.json``
relative to the Verlassen project root.  Slot 0 is the default / auto-save
slot; additional slots (1–9) are used for manual saves.

Usage
-----
    from core.save_manager import SaveManager

    sm = SaveManager(root=".")
    sm.save(slot=0, data=sm.default_save())
    data = sm.load(slot=0)
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional

import config

log = logging.getLogger(__name__)


class SaveManager:
    """
    Handles reading and writing player save data.

    Save format (JSON schema)
    -------------------------
    {
        "current_level": str,       # e.g. "level_01"
        "savings":        float,    # Ren's in-game money
        "flags":          dict,     # arbitrary key/bool progression flags
        "timestamp":      float     # Unix epoch seconds of last save
    }
    """

    def __init__(self, root: str = ".") -> None:
        """
        Parameters
        ----------
        root:
            Filesystem root that the save directory is resolved against.
            Defaults to the current working directory (which should be
            the Verlassen project root when the game is launched via main.py).
        """
        self._save_dir: str = os.path.join(os.path.abspath(root), config.SAVE_DIR)
        # Create the saves directory if it doesn't exist yet
        os.makedirs(self._save_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, slot: int = 0, data: Optional[dict] = None) -> None:
        """
        Serialise *data* to ``saves/save_{slot}.json``.

        The ``timestamp`` key is always overwritten with the current time so
        the most-recently-used slot can be detected on the main menu.

        Parameters
        ----------
        slot:
            Save slot index (0 = auto-save, 1–9 = manual slots).
        data:
            Dict conforming to the save schema.  If ``None``, a fresh
            ``default_save()`` dict is written instead.
        """
        if data is None:
            data = self.default_save()

        # Always stamp the write time
        data["timestamp"] = time.time()

        path = self._slot_path(slot)
        try:
            with open(path, "w", encoding=config.DATA_ENCODING) as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
            log.info("SaveManager: saved slot %d → %s", slot, path)
        except OSError as exc:
            log.error("SaveManager: failed to save slot %d: %s", slot, exc)

    def load(self, slot: int = 0) -> Optional[dict]:
        """
        Deserialise and return the save data for *slot*, or ``None`` if the
        file does not exist or is corrupt.

        Parameters
        ----------
        slot:
            Save slot index to read.

        Returns
        -------
        dict or None:
            The parsed save dict, or ``None`` on failure.
        """
        path = self._slot_path(slot)
        if not os.path.isfile(path):
            log.info("SaveManager: no save file at slot %d (%s)", slot, path)
            return None

        try:
            with open(path, "r", encoding=config.DATA_ENCODING) as fh:
                data: dict = json.load(fh)
            log.info("SaveManager: loaded slot %d from %s", slot, path)
            return data
        except (OSError, json.JSONDecodeError) as exc:
            log.error("SaveManager: failed to load slot %d: %s", slot, exc)
            return None

    def delete(self, slot: int) -> None:
        """
        Delete the save file for *slot* (no-op if the file does not exist).

        Parameters
        ----------
        slot:
            Save slot index to delete.
        """
        path = self._slot_path(slot)
        try:
            os.remove(path)
            log.info("SaveManager: deleted slot %d", slot)
        except FileNotFoundError:
            pass
        except OSError as exc:
            log.error("SaveManager: failed to delete slot %d: %s", slot, exc)

    def exists(self, slot: int) -> bool:
        """Return True if a save file exists for *slot*."""
        return os.path.isfile(self._slot_path(slot))

    @staticmethod
    def default_save() -> dict:
        """
        Return a fresh save-data dict representing a new game.

        Returns
        -------
        dict:
            Default save conforming to the save schema.
        """
        return {
            "current_level": "level_01",
            "savings": float(config.STARTING_SAVINGS),
            "flags": {},
            "timestamp": time.time(),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def set_flag(self, flag: str, value: bool = True, slot: int = 0) -> None:
        """Convenience method to update and persist a single story flag."""
        data = self.load(slot=slot) or self.default_save()
        if "flags" not in data:
            data["flags"] = {}
        data["flags"][flag] = value
        self.save(slot=slot, data=data)

    def _slot_path(self, slot: int) -> str:
        """Return the filesystem path for save *slot*."""
        return os.path.join(self._save_dir, f"save_{slot}.json")


# Global singleton
_save_manager_instance: SaveManager = SaveManager()
SaveManager.get = staticmethod(lambda: _save_manager_instance)

