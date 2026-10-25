"""Trimmed configuration for the vendored graphwar-aim perception modules.

Original: graphwar-aim by RE22GDV, MIT License.
This file keeps only the world bounds and vision parameters used by
``vision.py`` and ``geometry.py``. Solver and application settings were
removed because our project uses its own solver and decision layer.
"""

from __future__ import annotations

from dataclasses import dataclass

# Graphwar field size in world units. The on-screen axes run from -25..25
# horizontally and -15..15 vertically.
WORLD_X_MIN = -25.0
WORLD_X_MAX = 25.0
WORLD_Y_MIN = -15.0
WORLD_Y_MAX = 15.0


@dataclass
class VisionParams:
    """Thresholds and filters for reading a Graphwar frame."""

    # Near-white background of the plot (0..255 grey).
    white_threshold: int = 235
    # "Black" threshold for obstacles (0..255 grey).
    black_threshold: int = 70
    # Max saturation for a "black" obstacle pixel (rejects coloured balls).
    obstacle_max_saturation: int = 60
    # Min saturation for a soldier pixel. Soldier balls are vivid; name plates
    # are pale, so a high threshold drops the plates and keeps the balls.
    soldier_min_saturation: int = 115
    soldier_min_value: int = 70

    # Morphological kernel (px) that erases thin axes/text before obstacle
    # search; must be smaller than the smallest obstacle radius.
    obstacle_open_kernel: int = 5

    # Obstacle splitting via distance-transform peak picking.
    obstacle_min_radius_px: float = 8.0
    obstacle_peak_suppress: float = 0.5
    obstacle_max_count: int = 60

    # Soldier blobs: small vivid balls (often two colour halves). Name plates
    # are large and wide, so size caps separate them.
    soldier_min_area: int = 18
    soldier_max_area: int = 600
    soldier_open_kernel: int = 5
    soldier_max_width: int = 42
    soldier_max_height: int = 42
    # Merge radius for the two halves of one ball (px). One ball is ~13 px, so
    # halves merge within ~16 px; two soldiers standing stacked are >20 px apart
    # and must NOT be merged.
    soldier_merge_dist: int = 16

    # Expected plot aspect ratio (50:30) used to pick the plot rectangle.
    plot_aspect: float = (WORLD_X_MAX - WORLD_X_MIN) / (WORLD_Y_MAX - WORLD_Y_MIN)
    plot_aspect_tol: float = 0.35
