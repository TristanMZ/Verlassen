"""
core/asset_loader.py — Cache-based asset loader for Verlassen.

Loads and caches images, sounds, and fonts.  All paths are relative to the
Verlassen project root (the directory that contains main.py).

Usage
-----
    from core.asset_loader import AssetLoader

    loader = AssetLoader()
    surf   = loader.load_image("assets/sprites/player.png", use_nearest=True)
    sound  = loader.load_sound("assets/sfx/footstep.wav")
    font   = loader.load_font("assets/fonts/main.ttf", 16)
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import pygame

log = logging.getLogger(__name__)


class AssetLoader:
    """
    Cache-backed asset loader.

    All assets are keyed by a normalised, absolute path string so that the
    same file is never loaded from disk more than once per session.
    """

    def __init__(self, root: str = ".") -> None:
        """
        Parameters
        ----------
        root:
            Filesystem root that path arguments are resolved against.
            Defaults to the current working directory.
        """
        self._root: str = os.path.abspath(root)
        self._image_cache: dict[str, pygame.Surface] = {}
        self._sound_cache: dict[str, pygame.mixer.Sound] = {}
        self._font_cache:  dict[tuple[str, int], pygame.font.Font] = {}

    # ------------------------------------------------------------------
    # Images
    # ------------------------------------------------------------------

    def load_image(
        self,
        path: str,
        scale: Optional[tuple[int, int]] = None,
        use_nearest: bool = False,
    ) -> pygame.Surface:
        """
        Load and return a ``pygame.Surface`` from *path*.

        Results are cached by (path, scale, use_nearest) so that loading the
        same image with different parameters returns distinct surfaces without
        re-reading disk.

        Parameters
        ----------
        path:
            Path relative to the Verlassen root (e.g. ``"assets/bg.png"``).
        scale:
            Optional ``(width, height)`` to resize the loaded surface.  When
            *use_nearest* is True, ``pygame.transform.scale`` is used (integer
            nearest-neighbour) instead of ``smoothscale``.  Pixel-art sprites
            **must** pass ``use_nearest=True``.
        use_nearest:
            If True, any scaling uses ``pygame.transform.scale`` (nearest-
            neighbour).  Never use ``smoothscale`` for pixel art.
        """
        abs_path = self._resolve(path)
        cache_key = f"{abs_path}|{scale}|{use_nearest}"

        if cache_key not in self._image_cache:
            surface = pygame.image.load(abs_path).convert_alpha()

            if scale is not None:
                if use_nearest:
                    # Nearest-neighbour — mandatory for pixel-art sprites
                    surface = pygame.transform.scale(surface, scale)
                else:
                    # Smooth scaling for vector / painted backgrounds only
                    surface = pygame.transform.smoothscale(surface, scale)

            self._image_cache[cache_key] = surface
            log.debug("AssetLoader: loaded image %s", abs_path)

        return self._image_cache[cache_key]

    # ------------------------------------------------------------------
    # Sounds
    # ------------------------------------------------------------------

    def load_sound(self, path: str) -> pygame.mixer.Sound:
        """
        Load and return a ``pygame.mixer.Sound`` from *path*.

        Parameters
        ----------
        path:
            Path relative to the Verlassen root (e.g. ``"assets/sfx/step.wav"``).
        """
        abs_path = self._resolve(path)

        if abs_path not in self._sound_cache:
            sound = pygame.mixer.Sound(abs_path)
            self._sound_cache[abs_path] = sound
            log.debug("AssetLoader: loaded sound %s", abs_path)

        return self._sound_cache[abs_path]

    # ------------------------------------------------------------------
    # Fonts
    # ------------------------------------------------------------------

    def load_font(self, path: str, size: int) -> pygame.font.Font:
        """
        Load and return a ``pygame.font.Font`` from *path* at *size* pt.

        Pass an empty string or ``"default"`` for *path* to use Pygame's
        built-in fallback font.

        Parameters
        ----------
        path:
            Path relative to the Verlassen root (e.g. ``"assets/fonts/main.ttf"``),
            or ``""`` / ``"default"`` for the system default font.
        size:
            Point size of the font.
        """
        # Resolve path: empty / "default" → use pygame's built-in font
        if path and path != "default":
            abs_path: Optional[str] = self._resolve(path)
        else:
            abs_path = None  # pygame.font.Font(None, size) → default font

        cache_key: tuple[str, int] = (abs_path or "default", size)

        if cache_key not in self._font_cache:
            font = pygame.font.Font(abs_path, size)
            self._font_cache[cache_key] = font
            log.debug("AssetLoader: loaded font %s @ %dpx", abs_path or "default", size)

        return self._font_cache[cache_key]

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Evict all cached assets (call between levels to free VRAM/RAM)."""
        self._image_cache.clear()
        self._sound_cache.clear()
        self._font_cache.clear()
        log.debug("AssetLoader: cache cleared")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve(self, path: str) -> str:
        """Return the absolute filesystem path for a root-relative *path*."""
        return os.path.normpath(os.path.join(self._root, path))
