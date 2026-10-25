"""Synthetic checks for the vendored perception pipeline and state adapter.

These tests do not prove anything about the real game. They only catch broken
coordinate math, thresholds, or labelling logic before a real screenshot is
available. Real-game calibration lives in the perception benchmark.
"""

from __future__ import annotations

import cv2
import numpy as np

from gwbot.perception.state import Team, build_state
from gwbot.perception.vendor.graphwar_aim import geometry, vision

RECT = (60, 40, 830, 490)  # x0, y0, x1, y1 in the synthetic frame
SOLDIERS_PX = [(215, 175), (650, 400)]
OBSTACLE_PX = (400, 250, 30)  # cx, cy, r


def make_frame() -> np.ndarray:
    frame = np.full((600, 900, 3), 90, dtype=np.uint8)
    x0, y0, x1, y1 = RECT
    cv2.rectangle(frame, (x0, y0), (x1, y1), (255, 255, 255), thickness=-1)
    cx, cy, r = OBSTACLE_PX
    cv2.circle(frame, (cx, cy), r, (0, 0, 0), thickness=-1, lineType=cv2.LINE_AA)
    cv2.circle(frame, SOLDIERS_PX[0], 7, (0, 0, 255), thickness=-1, lineType=cv2.LINE_AA)
    cv2.circle(frame, SOLDIERS_PX[1], 7, (255, 0, 0), thickness=-1, lineType=cv2.LINE_AA)
    return frame


def expected_world(px: float, py: float) -> tuple[float, float]:
    rect = geometry.PlotRect(*RECT)
    return geometry.pixel_to_world(px, py, rect)


def test_find_plot_rect() -> None:
    rect = vision.find_plot_rect(make_frame())
    assert abs(rect.x0 - RECT[0]) <= 2
    assert abs(rect.y0 - RECT[1]) <= 2
    assert abs(rect.x1 - RECT[2]) <= 2
    assert abs(rect.y1 - RECT[3]) <= 2


def test_detects_one_obstacle_and_two_soldiers() -> None:
    scene = vision.analyze(make_frame())
    assert len(scene.obstacles) == 1, scene.obstacles
    assert len(scene.soldiers) == 2, scene.soldiers

    obstacle = scene.obstacles[0]
    cx, cy, r = OBSTACLE_PX
    wx, wy = expected_world(cx, cy)
    assert abs(obstacle.x - wx) < 0.5
    assert abs(obstacle.y - wy) < 0.5
    assert abs(obstacle.r - r * 50.0 / geometry.PlotRect(*RECT).width) < 0.35

    for px, py in SOLDIERS_PX:
        wx, wy = expected_world(px, py)
        nearest = min(scene.soldiers, key=lambda s: (s.x - wx) ** 2 + (s.y - wy) ** 2)
        assert abs(nearest.x - wx) < 0.4, (nearest, wx, wy)
        assert abs(nearest.y - wy) < 0.4, (nearest, wx, wy)


def test_state_labels_teams_and_uncertainty() -> None:
    scene = vision.analyze(make_frame())
    state = build_state(scene, shooter_index=1, ally_indices=(0,))

    assert state.soldiers[1].team is Team.SELF
    assert state.soldiers[0].team is Team.ALLY
    assert state.shooter.index == 1
    assert state.enemies == []
    assert all(s.uncertainty > 0 for s in state.soldiers)
    assert state.obstacles[0].uncertainty > 0
    assert state.plot_rect == (scene.rect.x0, scene.rect.y0, scene.rect.x1, scene.rect.y1)


def test_unknown_third_soldier_becomes_enemy() -> None:
    frame = make_frame()
    cv2.circle(frame, (500, 350), 7, (0, 200, 0), thickness=-1, lineType=cv2.LINE_AA)
    scene = vision.analyze(frame)
    assert len(scene.soldiers) == 3, scene.soldiers
    state = build_state(scene, shooter_index=0, ally_indices=(1,))
    assert [s.team for s in state.soldiers].count(Team.ENEMY) == 1


def test_world_pixel_roundtrip() -> None:
    rect = geometry.PlotRect(*RECT)
    for px, py in [(60, 40), (445, 265), (830, 490)]:
        wx, wy = geometry.pixel_to_world(px, py, rect)
        back_px, back_py = geometry.world_to_pixel(wx, wy, rect)
        assert abs(back_px - px) < 1e-6
        assert abs(back_py - py) < 1e-6
