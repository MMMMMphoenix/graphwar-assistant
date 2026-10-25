"""Turn a raw screen reading into a team-labelled, uncertainty-aware state.

The vendored graphwar-aim detector returns geometry only: every vivid ball is
a soldier, every black disc is an obstacle. A decision layer also needs to know
which soldier is the shooter, which are allies, and how much to trust each
coordinate.

For the first version this module uses explicit human labels: the caller passes
the shooter index and the ally indices. That is deliberate. Automatic active
player / team recognition can be added later from GraphBot's red-ring
detector, but a single click per game is more robust than a wrong label.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Iterable

import numpy as np

from .vendor.graphwar_aim import capture as aim_capture
from .vendor.graphwar_aim import geometry, vision
from .window_capture import HAS_WIN32, grab_game_client


class Team(str, Enum):
    SELF = "self"
    ALLY = "ally"
    ENEMY = "enemy"
    UNKNOWN = "unknown"


@dataclass
class SoldierObs:
    index: int
    x: float
    y: float
    px: float
    py: float
    team: Team = Team.UNKNOWN
    uncertainty: float = 0.0  # world units, 1-sigma-ish

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "x": round(self.x, 4),
            "y": round(self.y, 4),
            "px": round(self.px, 2),
            "py": round(self.py, 2),
            "team": self.team.value,
            "uncertainty": round(self.uncertainty, 4),
        }


@dataclass
class ObstacleObs:
    x: float
    y: float
    r: float
    uncertainty: float = 0.0

    def to_dict(self) -> dict:
        return {
            "x": round(self.x, 4),
            "y": round(self.y, 4),
            "r": round(self.r, 4),
            "uncertainty": round(self.uncertainty, 4),
        }


@dataclass
class PerceivedState:
    soldiers: list[SoldierObs]
    obstacles: list[ObstacleObs]
    shooter_index: int
    plot_rect: tuple[int, int, int, int]
    frame_shape: tuple[int, int]
    source: str
    timestamp: float = field(default_factory=time)
    notes: list[str] = field(default_factory=list)

    @property
    def shooter(self) -> SoldierObs:
        return self.soldiers[self.shooter_index]

    @property
    def allies(self) -> list[SoldierObs]:
        return [s for s in self.soldiers if s.team is Team.ALLY]

    @property
    def enemies(self) -> list[SoldierObs]:
        return [s for s in self.soldiers if s.team is Team.ENEMY]

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "timestamp": self.timestamp,
            "frame_shape": list(self.frame_shape),
            "plot_rect": list(self.plot_rect),
            "shooter_index": self.shooter_index,
            "soldiers": [s.to_dict() for s in self.soldiers],
            "obstacles": [o.to_dict() for o in self.obstacles],
            "notes": list(self.notes),
        }

    def describe(self) -> str:
        lines = [
            f"source={self.source} frame={self.frame_shape[1]}x{self.frame_shape[0]} "
            f"soldiers={len(self.soldiers)} obstacles={len(self.obstacles)}",
        ]
        for s in self.soldiers:
            marker = "*" if s.index == self.shooter_index else " "
            lines.append(
                f"{marker} [{s.index}] {s.team.value:6s} "
                f"world=({s.x:7.2f},{s.y:6.2f}) px=({s.px:6.1f},{s.py:6.1f}) "
                f"sigma={s.uncertainty:.2f}"
            )
        return "\n".join(lines)


def _pixel_scale(rect: geometry.PlotRect) -> float:
    sx, sy = geometry.world_scale_per_pixel(rect)
    return (sx + sy) / 2.0


def _label_soldiers(
    scene: vision.Scene,
    shooter_index: int | None,
    ally_indices: Iterable[int],
    shooter_xy: tuple[float, float] | None,
) -> tuple[list[SoldierObs], int]:
    if not scene.soldiers:
        raise ValueError("no soldiers detected")

    allies = set(ally_indices)
    if shooter_index is None:
        if shooter_xy is not None:
            shooter_index = min(
                range(len(scene.soldiers)),
                key=lambda i: (scene.soldiers[i].x - shooter_xy[0]) ** 2
                + (scene.soldiers[i].y - shooter_xy[1]) ** 2,
            )
        else:
            # Fall back to the left-most soldier. This is a guess, not a
            # decision; callers should pass an explicit index when possible.
            shooter_index = min(range(len(scene.soldiers)), key=lambda i: scene.soldiers[i].x)

    if not 0 <= shooter_index < len(scene.soldiers):
        raise IndexError(f"shooter_index {shooter_index} out of range")

    if shooter_index in allies:
        allies.discard(shooter_index)

    sigma = max(0.02, 1.0 * _pixel_scale(scene.rect))
    soldiers: list[SoldierObs] = []
    for i, s in enumerate(scene.soldiers):
        if i == shooter_index:
            team = Team.SELF
        elif i in allies:
            team = Team.ALLY
        else:
            team = Team.ENEMY
        soldiers.append(
            SoldierObs(
                index=i,
                x=float(s.x),
                y=float(s.y),
                px=float(s.px),
                py=float(s.py),
                team=team,
                uncertainty=sigma,
            )
        )
    return soldiers, shooter_index


def build_state(
    scene: vision.Scene,
    shooter_index: int | None = None,
    ally_indices: Iterable[int] = (),
    shooter_xy: tuple[float, float] | None = None,
    source: str = "screen",
    notes: Iterable[str] = (),
) -> PerceivedState:
    """Convert a ``vision.Scene`` into a team-labelled ``PerceivedState``."""
    soldiers, shooter_index = _label_soldiers(scene, shooter_index, ally_indices, shooter_xy)
    sigma = max(0.02, 1.0 * _pixel_scale(scene.rect))
    obstacles = [
        ObstacleObs(x=float(o.x), y=float(o.y), r=float(o.r), uncertainty=sigma)
        for o in scene.obstacles
    ]
    return PerceivedState(
        soldiers=soldiers,
        obstacles=obstacles,
        shooter_index=shooter_index,
        plot_rect=(scene.rect.x0, scene.rect.y0, scene.rect.x1, scene.rect.y1),
        frame_shape=scene.frame_shape,
        source=source,
        notes=list(notes),
    )


def _looks_blank(frame: np.ndarray) -> bool:
    return frame is None or frame.size == 0 or float(frame.mean()) < 4.0


def capture_frame(title_substring: str = "Graphwar") -> tuple[np.ndarray, str]:
    """Capture a game frame, preferring an off-screen PrintWindow grab."""
    notes = ""
    if HAS_WIN32:
        try:
            frame, hwnd = grab_game_client(title_substring)
            if not _looks_blank(frame):
                return frame, f"printwindow:{hwnd}"
        except Exception as exc:  # noqa: BLE001 - fall back to desktop capture
            notes = f"printwindow failed: {exc}"

    frame, _bbox = aim_capture.grab_game(title_substring)
    if _looks_blank(frame):
        raise RuntimeError("captured frame is empty or black")
    return frame, "screengrab" + (f" ({notes})" if notes else "")


def capture_state(
    title_substring: str = "Graphwar",
    shooter_index: int | None = None,
    ally_indices: Iterable[int] = (),
    shooter_xy: tuple[float, float] | None = None,
    vp: vision.config.VisionParams | None = None,
) -> tuple[PerceivedState, np.ndarray]:
    """Capture the game, detect the scene, and return a labelled state."""
    frame, source = capture_frame(title_substring)
    scene = vision.analyze(frame, vp)
    state = build_state(
        scene,
        shooter_index=shooter_index,
        ally_indices=ally_indices,
        shooter_xy=shooter_xy,
        source=source,
    )
    return state, frame


def analyze_image(
    path: str,
    shooter_index: int | None = None,
    ally_indices: Iterable[int] = (),
    shooter_xy: tuple[float, float] | None = None,
    vp: vision.config.VisionParams | None = None,
) -> tuple[PerceivedState, np.ndarray]:
    """Analyze a saved screenshot instead of a live window."""
    frame = aim_capture.imread_unicode(path)
    if frame is None:
        raise FileNotFoundError(path)
    scene = vision.analyze(frame, vp)
    state = build_state(
        scene,
        shooter_index=shooter_index,
        ally_indices=ally_indices,
        shooter_xy=shooter_xy,
        source=f"image:{path}",
    )
    return state, frame
