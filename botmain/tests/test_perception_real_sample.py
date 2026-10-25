"""Regression check on a real Graphwar frame from the MIT-licensed reference.

The image belongs to the graphwar-aim repository and is not copied into this
project. The test skips when the local reference checkout is absent, so CI can
still run the synthetic suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gwbot.perception.state import Team, analyze_image

SAMPLE = (
    Path(__file__).resolve().parents[2]
    / "references"
    / "oss"
    / "graphwar-aim"
    / "docs"
    / "img"
    / "sample_capture.png"
)


@pytest.mark.skipif(not SAMPLE.exists(), reason="local graphwar-aim reference is absent")
def test_real_sample_layout_and_labels() -> None:
    state, _frame = analyze_image(str(SAMPLE), shooter_index=3, ally_indices=(1,))

    x0, y0, x1, y1 = state.plot_rect
    assert abs(x0 - 15) <= 1 and abs(y0 - 15) <= 1
    assert abs(x1 - 785) <= 1 and abs(y1 - 465) <= 1
    assert len(state.soldiers) == 4
    # Real terrain circles plus one small projectile-like dot. The exact count
    # is a property of this screenshot, not a promise about other frames.
    assert 15 <= len(state.obstacles) <= 22

    assert state.shooter.team is Team.SELF
    assert state.soldiers[1].team is Team.ALLY
    assert {s.team for s in state.enemies} == {Team.ENEMY}

    # Known pixel centres from the screenshot, checked against the axes.
    shooter = state.shooter
    assert abs(shooter.px - 305.2) < 1.0
    assert abs(shooter.py - 230.8) < 1.0
    assert abs(shooter.x - (-6.16)) < 0.2
    assert abs(shooter.y - 0.61) < 0.2
