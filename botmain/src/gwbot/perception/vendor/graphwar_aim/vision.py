"""Computer vision: parse a Graphwar frame.

Pipeline:

1. :func:`find_plot_rect`     — locate the white plot rectangle;
2. :func:`detect_obstacles`   — black filled circles (world units);
3. :func:`detect_soldiers`    — small vivid soldier balls (world units).

All detectors return results in **world units** so nothing downstream has to
think about pixels.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import cv2
import numpy as np

from . import config, geometry
from .geometry import PlotRect


@dataclass
class Obstacle:
    x: float  # world centre
    y: float
    r: float  # world radius


@dataclass
class Soldier:
    x: float  # world centre
    y: float
    px: float  # frame pixel (debugging / overlays)
    py: float


@dataclass
class Scene:
    rect: PlotRect
    obstacles: list[Obstacle]
    soldiers: list[Soldier]
    frame_shape: tuple[int, int]  # (h, w)


# --------------------------------------------------------------------------- #
# 1. Plot area
# --------------------------------------------------------------------------- #
def find_plot_rect(frame_bgr: np.ndarray, vp: config.VisionParams | None = None) -> PlotRect:
    """Locate the plot rectangle.

    The plot background is one big connected near-white region ("Swiss
    cheese" around the black obstacles) with by far the most white pixels.
    A light 3x3 closing keeps it connected without bridging the green gaps to
    the white log/input panels below the plot.
    """
    vp = vp or config.VisionParams()
    h, w = frame_bgr.shape[:2]
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    white = (gray >= vp.white_threshold).astype(np.uint8) * 255
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    white = cv2.morphologyEx(white, cv2.MORPH_CLOSE, k, iterations=1)

    num, _labels, stats, _cent = cv2.connectedComponentsWithStats(white, 8)
    cands = []  # (x, y, w, h, pixel_area, aspect)
    for i in range(1, num):
        x, y, ww, hh, pix = stats[i]
        if ww * hh < 0.10 * w * h:
            continue
        cands.append((x, y, ww, hh, int(pix), ww / max(hh, 1)))
    if not cands:
        return PlotRect(0, 0, w, h)

    # Prefer components with the field's 50:30 aspect; among them the one with
    # the most white pixels (the plot background, not a solid side panel).
    in_aspect = [c for c in cands if abs(c[5] - vp.plot_aspect) <= vp.plot_aspect_tol * vp.plot_aspect]
    pool = in_aspect if in_aspect else cands
    x, y, ww, hh, _, _ = max(pool, key=lambda c: c[4])
    return PlotRect(int(x), int(y), int(x + ww), int(y + hh))


def _roi_mask(rect: PlotRect, shape: tuple[int, int], pad: int) -> np.ndarray:
    h, w = shape
    m = np.zeros((h, w), dtype=np.uint8)
    x0, y0 = max(0, rect.x0 + pad), max(0, rect.y0 + pad)
    x1, y1 = min(w, rect.x1 - pad), min(h, rect.y1 - pad)
    m[y0:y1, x0:x1] = 255
    return m


# --------------------------------------------------------------------------- #
# 2. Obstacles (black circles)
# --------------------------------------------------------------------------- #
def detect_obstacles(
    frame_bgr: np.ndarray, rect: PlotRect, vp: config.VisionParams | None = None
) -> list[Obstacle]:
    vp = vp or config.VisionParams()
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    sat = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)[:, :, 1]

    # Obstacle = dark AND unsaturated (pure black has S~0). This excludes the
    # coloured soldier balls, which can also be dark in greyscale.
    black = ((gray <= vp.black_threshold) & (sat <= vp.obstacle_max_saturation)).astype(np.uint8) * 255
    black = cv2.bitwise_and(black, _roi_mask(rect, black.shape, pad=3))

    # Opening erases thin axes and label text but keeps the big discs.
    ksz = max(3, vp.obstacle_open_kernel)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksz, ksz))
    black = cv2.morphologyEx(black, cv2.MORPH_OPEN, k, iterations=1)

    # Split touching circles with the distance transform of the ORIGINAL mask:
    # every disc has a local maximum at its own centre whose value is its own
    # radius (the union boundary on the outer side is the disc's own arc), so
    # peak picking recovers true centres/radii even for overlapping discs.
    from scipy.ndimage import maximum_filter

    dist = cv2.distanceTransform(black, cv2.DIST_L2, 5)
    peaks = (dist >= maximum_filter(dist, size=7) - 1e-6) & (dist >= vp.obstacle_min_radius_px)
    ys_pk, xs_pk = np.nonzero(peaks)
    cands = sorted(zip(dist[ys_pk, xs_pk].tolist(), xs_pk.tolist(), ys_pk.tolist()), reverse=True)

    kept_px: list[tuple[float, float, float]] = []  # (cx, cy, r) in pixels
    for r, cx, cy in cands:
        # Plateau neighbours / shoulders of an already kept disc are suppressed;
        # a genuinely different disc has its centre farther than half a radius.
        if any((cx - kx) ** 2 + (cy - ky) ** 2 < (vp.obstacle_peak_suppress * kr) ** 2 for kx, ky, kr in kept_px):
            continue
        kept_px.append((float(cx), float(cy), float(r)))
        if len(kept_px) >= vp.obstacle_max_count:
            break

    obstacles: list[Obstacle] = []
    for cx, cy, r in kept_px:
        wx, wy = geometry.pixel_to_world(cx, cy, rect)
        obstacles.append(Obstacle(float(wx), float(wy), float(geometry.pixel_radius_to_world(r, rect))))
    # Safety net: a small circle mostly inside a bigger one adds nothing.
    kept: list[Obstacle] = []
    for o in sorted(obstacles, key=lambda o: -o.r):
        if not any(np.hypot(o.x - k.x, o.y - k.y) + 0.6 * o.r <= k.r for k in kept):
            kept.append(o)
    return kept


# --------------------------------------------------------------------------- #
# 3. Soldiers (vivid balls)
# --------------------------------------------------------------------------- #
def detect_soldiers(
    frame_bgr: np.ndarray, rect: PlotRect, vp: config.VisionParams | None = None
) -> list[Soldier]:
    vp = vp or config.VisionParams()
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    colored = ((hsv[:, :, 1] >= vp.soldier_min_saturation)
               & (hsv[:, :, 2] >= vp.soldier_min_value)).astype(np.uint8) * 255
    colored = cv2.bitwise_and(colored, _roi_mask(rect, colored.shape, pad=2))

    # Opening first: erases thin lines (the in-flight shot trail drawn by the
    # game) that would otherwise merge with a ball and inflate the blob.
    k_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (vp.soldier_open_kernel, vp.soldier_open_kernel))
    colored = cv2.morphologyEx(colored, cv2.MORPH_OPEN, k_open, iterations=1)
    # Light closing fills inner gaps without gluing a ball to its name plate.
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    colored = cv2.morphologyEx(colored, cv2.MORPH_CLOSE, k, iterations=1)

    cnts, _ = cv2.findContours(colored, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    raw: list[tuple[float, float]] = []
    for c in cnts:
        area = cv2.contourArea(c)
        if area < vp.soldier_min_area or area > vp.soldier_max_area:
            continue
        _x, _y, ww, hh = cv2.boundingRect(c)
        if ww > vp.soldier_max_width or hh > vp.soldier_max_height:
            continue  # a wide/tall name plate, not a ball
        M = cv2.moments(c)
        if M["m00"] == 0:
            continue
        raw.append((M["m10"] / M["m00"], M["m01"] / M["m00"]))

    merged = _merge_points(raw, vp.soldier_merge_dist)
    return [Soldier(*geometry.pixel_to_world(cx, cy, rect), cx, cy) for cx, cy in merged]


def _merge_points(pts: list[tuple[float, float]], dist: float) -> list[tuple[float, float]]:
    """Greedy clustering: merge points closer than *dist* (two halves of a ball)."""
    out: list[list[float]] = []
    counts: list[int] = []
    for px, py in pts:
        for i, (ox, oy) in enumerate(out):
            if (px - ox) ** 2 + (py - oy) ** 2 <= dist * dist:
                n = counts[i]
                out[i] = [(ox * n + px) / (n + 1), (oy * n + py) / (n + 1)]
                counts[i] += 1
                break
        else:
            out.append([px, py])
            counts.append(1)
    return [(p[0], p[1]) for p in out]


# --------------------------------------------------------------------------- #
# Full scene analysis and debugging helpers
# --------------------------------------------------------------------------- #
def analyze(frame_bgr: np.ndarray, vp: config.VisionParams | None = None) -> Scene:
    vp = vp or config.VisionParams()
    rect = find_plot_rect(frame_bgr, vp)
    return Scene(
        rect=rect,
        obstacles=detect_obstacles(frame_bgr, rect, vp),
        soldiers=detect_soldiers(frame_bgr, rect, vp),
        frame_shape=frame_bgr.shape[:2],
    )


def draw_debug(frame_bgr: np.ndarray, scene: Scene) -> np.ndarray:
    """Overlay the detection result on the frame (plot rect, obstacles, soldiers)."""
    out = frame_bgr.copy()
    r = scene.rect
    cv2.rectangle(out, (r.x0, r.y0), (r.x1, r.y1), (0, 200, 0), 2)
    px_per_unit = max(r.width, 1) / (config.WORLD_X_MAX - config.WORLD_X_MIN)
    for ob in scene.obstacles:
        px, py = geometry.world_to_pixel(ob.x, ob.y, r)
        cv2.circle(out, (int(px), int(py)), int(ob.r * px_per_unit), (255, 0, 0), 2)
    for sld in scene.soldiers:
        cv2.circle(out, (int(sld.px), int(sld.py)), 10, (0, 0, 255), 2)
    return out


def save_debug(frame_bgr: np.ndarray, scene: Scene, out_dir: str = "debug") -> str:
    """Write the frame, the overlay and the two detection masks for diagnosis."""
    vp = config.VisionParams()
    os.makedirs(out_dir, exist_ok=True)
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    black = ((gray <= vp.black_threshold) & (hsv[:, :, 1] <= vp.obstacle_max_saturation)).astype(np.uint8) * 255
    colored = ((hsv[:, :, 1] >= vp.soldier_min_saturation) & (hsv[:, :, 2] >= vp.soldier_min_value)).astype(np.uint8) * 255
    cv2.imwrite(os.path.join(out_dir, "01_capture.png"), frame_bgr)
    cv2.imwrite(os.path.join(out_dir, "02_overlay.png"), draw_debug(frame_bgr, scene))
    cv2.imwrite(os.path.join(out_dir, "03_black_mask.png"), black)
    cv2.imwrite(os.path.join(out_dir, "04_colored_mask.png"), colored)
    return os.path.abspath(out_dir)
