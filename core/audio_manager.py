"""
core/audio_manager.py — Layered music and SFX manager for Verlassen.

Wraps ``pygame.mixer`` with higher-level concepts:

* Named music tracks played with configurable loop / fade behaviour.
* A *tension level* (0.0–1.0) that other systems set to react to gameplay
  state; the manager uses it to mix ambient and tense music layers.
* Named SFX played on demand.

No real audio assets are needed at this stage — all public methods are fully
functional stubs that log their calls so the rest of the codebase can be
wired up without audio files.

Usage
-----
    from core.audio_manager import AudioManager

    audio = AudioManager()
    audio.play_music("ambient_house", loop=True, fade_ms=2000)
    audio.set_tension(0.8)
    audio.play_sfx("footstep_wood")
    audio.stop_music(fade_ms=500)
"""

from __future__ import annotations

import logging
from typing import Optional

import pygame

log = logging.getLogger(__name__)

# Mixer initialisation constants
_FREQUENCY: int   = 44100
_SIZE:       int   = -16    # signed 16-bit
_CHANNELS:   int   = 2      # stereo
_BUFFER:     int   = 512    # samples per buffer (low latency)


class AudioManager:
    """
    High-level audio controller for music and SFX.

    Handles mixer initialisation internally so callers never touch
    ``pygame.mixer`` directly.  All methods are safe to call even if the
    mixer failed to initialise (errors are logged, not raised).
    """

    def __init__(self) -> None:
        self._ready: bool = self._init_mixer()

        self._current_track: Optional[str] = None
        self._tension: float = 0.0  # 0.0 = calm, 1.0 = maximum tension

        # SFX cache: name → Sound object
        self._sfx_cache: dict[str, pygame.mixer.Sound] = {}

    # ------------------------------------------------------------------
    # Mixer lifecycle
    # ------------------------------------------------------------------

    @staticmethod
    def _init_mixer() -> bool:
        """
        Initialise ``pygame.mixer`` if not already initialised.

        Returns True on success, False if the mixer is unavailable (e.g.
        no audio hardware).
        """
        if pygame.mixer.get_init():
            return True
        try:
            pygame.mixer.init(_FREQUENCY, _SIZE, _CHANNELS, _BUFFER)
            log.info("AudioManager: mixer initialised (%d Hz, %dch)", _FREQUENCY, _CHANNELS)
            return True
        except pygame.error as exc:
            log.warning("AudioManager: mixer init failed — running silent (%s)", exc)
            return False

    # ------------------------------------------------------------------
    # Music
    # ------------------------------------------------------------------

    def play_music(
        self,
        track: str,
        loop: bool = True,
        fade_ms: int = 1000,
        path: Optional[str] = None,
    ) -> None:
        """
        Start playing a music *track*, fading in over *fade_ms* milliseconds.

        If *track* is already playing it is left untouched.

        Parameters
        ----------
        track:
            Logical track name (e.g. ``"ambient_house"``).  Used as the key
            into asset lookup; callers may also supply an explicit *path*.
        loop:
            Whether the track loops indefinitely.
        fade_ms:
            Fade-in duration in milliseconds.
        path:
            Explicit filesystem path to the audio file.  If omitted the asset
            loader (not yet wired here) would resolve it via the track name.
            Currently logged as a stub.
        """
        if track == self._current_track:
            return  # already playing — nothing to do

        if not self._ready:
            log.debug("AudioManager.play_music: silent — no mixer (%s)", track)
            self._current_track = track
            return

        log.info("AudioManager: play_music '%s' (loop=%s, fade=%dms)", track, loop, fade_ms)

        if path:
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.play(-1 if loop else 0, fade_ms=fade_ms)
            except pygame.error as exc:
                log.warning("AudioManager: could not play '%s': %s", track, exc)

        self._current_track = track

    def stop_music(self, fade_ms: int = 500) -> None:
        """
        Stop the currently playing music, fading out over *fade_ms* ms.

        Parameters
        ----------
        fade_ms:
            Fade-out duration in milliseconds.
        """
        log.info("AudioManager: stop_music (fade=%dms)", fade_ms)
        self._current_track = None

        if not self._ready:
            return
        try:
            pygame.mixer.music.fadeout(fade_ms)
        except pygame.error as exc:
            log.warning("AudioManager: stop_music error: %s", exc)

    # ------------------------------------------------------------------
    # SFX
    # ------------------------------------------------------------------

    def play_sfx(self, name: str, path: Optional[str] = None) -> None:
        """
        Play a one-shot sound effect by *name*.

        Parameters
        ----------
        name:
            Logical SFX name (e.g. ``"footstep_wood"``).
        path:
            Explicit filesystem path.  If the sound is already cached by
            *name*, *path* is ignored.
        """
        log.debug("AudioManager: play_sfx '%s'", name)

        if not self._ready:
            return

        if name not in self._sfx_cache and path:
            try:
                self._sfx_cache[name] = pygame.mixer.Sound(path)
            except pygame.error as exc:
                log.warning("AudioManager: could not load sfx '%s': %s", name, exc)
                return

        sound = self._sfx_cache.get(name)
        if sound:
            sound.play()

    def preload_sfx(self, name: str, path: str) -> None:
        """
        Load an SFX file into the cache without playing it.

        Parameters
        ----------
        name:
            Logical name used by later ``play_sfx`` calls.
        path:
            Filesystem path to the audio file.
        """
        if not self._ready or name in self._sfx_cache:
            return
        try:
            self._sfx_cache[name] = pygame.mixer.Sound(path)
            log.debug("AudioManager: preloaded sfx '%s'", name)
        except pygame.error as exc:
            log.warning("AudioManager: preload_sfx '%s' failed: %s", name, exc)

    # ------------------------------------------------------------------
    # Tension / dynamic mixing
    # ------------------------------------------------------------------

    def set_tension(self, level: float) -> None:
        """
        Set the tension level, which drives dynamic music / ambient mixing.

        At level 0.0 the ambient underscore plays at full volume; at 1.0 the
        tense / alert layer is prominent.  Intermediate values crossfade both
        layers.

        Parameters
        ----------
        level:
            Tension value in ``[0.0, 1.0]``.
        """
        self._tension = max(0.0, min(1.0, level))
        log.debug("AudioManager: tension → %.2f", self._tension)

        if not self._ready:
            return

        # Drive music volume: calm layer fades out as tension rises
        calm_vol  = 1.0 - self._tension
        tense_vol = self._tension

        # pygame.mixer.music controls the foreground track only; a full
        # layered implementation would use separate channels.  For now we
        # adjust the master music volume as a proxy.
        try:
            pygame.mixer.music.set_volume(max(calm_vol, 0.1))
        except pygame.error:
            pass

    @property
    def tension(self) -> float:
        """Current tension level (0.0–1.0, read-only)."""
        return self._tension

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def quit(self) -> None:
        """Stop all audio and release mixer resources."""
        log.info("AudioManager: shutting down")
        if self._ready:
            pygame.mixer.stop()
            pygame.mixer.quit()
        self._ready = False
        self._sfx_cache.clear()


# Global singleton instance
_audio_manager_instance: AudioManager = AudioManager()
AudioManager.get = staticmethod(lambda: _audio_manager_instance)

