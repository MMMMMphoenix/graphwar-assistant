"""Coordinate transforms: screen pixels <-> Graphwar world units.

The plot area is a pixel rectangle (:class:`PlotRect`).  Its left edge maps to
``WORLD_X_MIN``, right edge to ``WORLD_X_MAX``, top to ``WORLD_Y_MAX`` and
bottom to ``WORLD_Y_MIN`` (screen y grows downwards, world y grows upwards).
"""

from __future__ import annotations

from dataclasses import dataclass

from . import config


@dataclass
class PlotRect:
    """Plot-area rectangle in pixels, relative to the captured frame."""

    x0: int  # left
    y0: int  # top
    x1: int  # right
    y1: int  # bottom

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        return self.y1 - self.y0


def pixel_to_world(px: float, py: float, rect: PlotRect) -> tuple[float, float]:
    """Frame pixel -> world coordinates."""
    fx = (px - rect.x0) / max(rect.width, 1)
    fy = (py - rect.y0) / max(rect.height, 1)
    wx = config.WORLD_X_MIN + fx * (config.WORLD_X_MAX - config.WORLD_X_MIN)
    wy = config.WORLD_Y_MAX - fy * (config.WORLD_Y_MAX - config.WORLD_Y_MIN)
    return wx, wy


def world_to_pixel(wx: float, wy: float, rect: PlotRect) -> tuple[float, float]:
    """World coordinates -> frame pixel."""
    fx = (wx - config.WORLD_X_MIN) / (config.WORLD_X_MAX - config.WORLD_X_MIN)
    fy = (config.WORLD_Y_MAX - wy) / (config.WORLD_Y_MAX - config.WORLD_Y_MIN)
    return rect.x0 + fx * rect.width, rect.y0 + fy * rect.height


def world_scale_per_pixel(rect: PlotRect) -> tuple[float, float]:
    """World units per pixel along x and y."""
    sx = (config.WORLD_X_MAX - config.WORLD_X_MIN) / max(rect.width, 1)
    sy = (config.WORLD_Y_MAX - config.WORLD_Y_MIN) / max(rect.height, 1)
    return sx, sy


def pixel_radius_to_world(r_px: float, rect: PlotRect) -> float:
    """Radius in pixels -> world units (averaged over both axes)."""
    sx, sy = world_scale_per_pixel(rect)
    return r_px * (sx + sy) / 2.0
