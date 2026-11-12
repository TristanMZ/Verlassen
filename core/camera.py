"""
core/camera.py — Smooth-follow camera with shake and zoom for Verlassen.

The camera tracks a target position in world space and translates world
coordinates to screen coordinates (and back) for rendering.

Usage
-----
    from core.camera import Camera

    cam = Camera(INTERNAL_W, INTERNAL_H)
    cam.follow(player.rect.center)   # call each frame before drawing
    cam.shake(intensity=8, duration=0.4)
    cam.zoom(factor=1.5, duration=0.3)

    screen_pos = cam.world_to_screen((wx, wy))
    world_pos  = cam.screen_to_world((sx, sy))
"""

from __future__ import annotations

import math
import random
from typing import Optional

import pygame

import config


class Camera:
    """
    Smooth-follow camera with optional screen-shake and zoom effects.

    The camera maintains a *logical* position (``pos``) expressed in world
    pixels and applies lerp smoothing to track a target.  Shake is added as a
    per-frame random offset; zoom scales the viewport around the camera centre.
    """

    # Lerp coefficient per second — higher = snappier follow
    LERP_SPEED: float = 6.0

    def __init__(self, view_w: int = config.INTERNAL_W, view_h: int = config.INTERNAL_H) -> None:
        """
        Parameters
        ----------
        view_w, view_h:
            Dimensions of the viewport (logical resolution).
        """
        self._view_w: int = view_w
        self._view_h: int = view_h

        # Current camera centre in world space (float for sub-pixel accuracy)
        self.pos: pygame.Vector2 = pygame.Vector2(view_w / 2, view_h / 2)
        # Desired target the camera is lerping toward
        self._target: pygame.Vector2 = pygame.Vector2(self.pos)

        # --- Shake state ---
        self._shake_intensity: float = 0.0   # max pixel offset per axis
        self._shake_duration:  float = 0.0   # remaining shake time (seconds)
        self._shake_offset:    pygame.Vector2 = pygame.Vector2(0, 0)

        # --- Zoom state ---
        self._zoom_current:  float = 1.0
        self._zoom_target:   float = 1.0
        self._zoom_duration: float = 0.0
        self._zoom_elapsed:  float = 0.0
        self._zoom_start:    float = 1.0

        # Optional world bounds to clamp the camera inside
        self._bounds: Optional[pygame.Rect] = None

    # ------------------------------------------------------------------
    # Per-frame update
    # ------------------------------------------------------------------

    def follow(self, target: tuple[float, float] | pygame.Vector2, dt: float) -> None:
        """
        Smoothly move the camera toward *target* (a world-space point).

        Call once per frame before any ``world_to_screen`` queries.

        Parameters
        ----------
        target:
            World-space (x, y) the camera should centre on.
        dt:
            Elapsed time in seconds since the last frame (fixed step = 1/60).
        """
        self._target.update(target)

        # Exponential lerp: remainder = (1 - lerp_speed * dt)^n approaches 0
        alpha = min(1.0, self.LERP_SPEED * dt)
        self.pos.x += (self._target.x - self.pos.x) * alpha
        self.pos.y += (self._target.y - self.pos.y) * alpha

        # Clamp to world bounds if set
        if self._bounds is not None:
            half_w = (self._view_w / 2) / self._zoom_current
            half_h = (self._view_h / 2) / self._zoom_current
            self.pos.x = max(self._bounds.left + half_w, min(self._bounds.right  - half_w, self.pos.x))
            self.pos.y = max(self._bounds.top  + half_h, min(self._bounds.bottom - half_h, self.pos.y))

        # --- Advance shake ---
        if self._shake_duration > 0:
            self._shake_duration -= dt
            if self._shake_duration <= 0:
                self._shake_duration = 0.0
                self._shake_offset.update(0, 0)
            else:
                # Random pixel offset scaled by remaining intensity
                scale = self._shake_intensity * (self._shake_duration / max(self._shake_duration, 0.001))
                self._shake_offset.x = random.uniform(-scale, scale)
                self._shake_offset.y = random.uniform(-scale, scale)
        else:
            self._shake_offset.update(0, 0)

        # --- Advance zoom ---
        if self._zoom_duration > 0:
            self._zoom_elapsed += dt
            t = min(self._zoom_elapsed / self._zoom_duration, 1.0)
            # Smooth step (3t² − 2t³) for a pleasing ease-in-out
            t_smooth = t * t * (3 - 2 * t)
            self._zoom_current = self._zoom_start + (self._zoom_target - self._zoom_start) * t_smooth
            if t >= 1.0:
                self._zoom_current = self._zoom_target
                self._zoom_duration = 0.0

    # ------------------------------------------------------------------
    # Effects API
    # ------------------------------------------------------------------

    def shake(self, intensity: float, duration: float) -> None:
        """
        Trigger a screen-shake effect.

        Parameters
        ----------
        intensity:
            Maximum pixel displacement per axis (at logical resolution).
        duration:
            Duration in seconds.  Stacks with any in-progress shake by
            taking whichever is stronger / longer.
        """
        # Allow stacking: take the larger of current and new values
        self._shake_intensity = max(self._shake_intensity, intensity)
        self._shake_duration  = max(self._shake_duration, duration)

    def zoom(self, factor: float, duration: float) -> None:
        """
        Animate the camera zoom level to *factor* over *duration* seconds.

        Parameters
        ----------
        factor:
            Target zoom level (1.0 = normal, 2.0 = double magnification).
        duration:
            Time in seconds to reach the target zoom level.
        """
        self._zoom_start   = self._zoom_current
        self._zoom_target  = factor
        self._zoom_duration = duration
        self._zoom_elapsed  = 0.0

    def set_bounds(self, bounds: Optional[pygame.Rect]) -> None:
        """
        Constrain camera movement to *bounds* (world-space rect).

        Pass ``None`` to disable clamping.
        """
        self._bounds = bounds

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------

    def world_to_screen(self, pos: tuple[float, float]) -> tuple[int, int]:
        """
        Convert a world-space position to screen (viewport) pixel coordinates.

        Applies the current zoom level and shake offset.

        Parameters
        ----------
        pos:
            World-space ``(x, y)`` position.

        Returns
        -------
        tuple[int, int]:
            Integer screen-space pixel coordinates.
        """
        # Translate relative to camera centre, then scale by zoom, then
        # re-centre on the viewport centre.
        cx = (self._view_w / 2) + self._shake_offset.x
        cy = (self._view_h / 2) + self._shake_offset.y

        sx = (pos[0] - self.pos.x) * self._zoom_current + cx
        sy = (pos[1] - self.pos.y) * self._zoom_current + cy
        return (int(sx), int(sy))

    def screen_to_world(self, pos: tuple[float, float]) -> tuple[float, float]:
        """
        Convert screen-space pixel coordinates back to world space.

        Parameters
        ----------
        pos:
            Screen-space ``(x, y)`` coordinates.

        Returns
        -------
        tuple[float, float]:
            World-space position.
        """
        cx = self._view_w / 2
        cy = self._view_h / 2

        wx = (pos[0] - cx) / self._zoom_current + self.pos.x
        wy = (pos[1] - cy) / self._zoom_current + self.pos.y
        return (wx, wy)

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def zoom_level(self) -> float:
        """Current zoom factor (read-only)."""
        return self._zoom_current

    @property
    def offset(self) -> pygame.Vector2:
        """
        Top-left world-space offset for this frame (useful for rect-based
        draw systems).  Equivalent to ``self.pos - half_viewport``.
        """
        return pygame.Vector2(
            self.pos.x - self._view_w / 2 / self._zoom_current,
            self.pos.y - self._view_h / 2 / self._zoom_current,
        )
