"""Perception probe: read one Graphwar frame and print what was detected.

Usage examples (run from the botmain directory):

    py -3 scripts/perception_probe.py --image shots/game.png --save-debug debug
    py -3 scripts/perception_probe.py --window Graphwar --shooter-index 0 --allies 1,2

The probe only reads the screen. It does not solve, decide, or type anything.
Use it to check the plot rectangle, the soldier indices, and the obstacle
circles before trusting any downstream recommendation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gwbot.perception import state as state_mod  # noqa: E402
from gwbot.perception.vendor.graphwar_aim import capture as aim_capture  # noqa: E402
from gwbot.perception.vendor.graphwar_aim import vision  # noqa: E402


def _parse_indices(text: str) -> tuple[int, ...]:
    if not text.strip():
        return ()
    return tuple(int(part) for part in text.replace(" ", "").split(",") if part)


def _parse_xy(text: str) -> tuple[float, float] | None:
    if not text.strip():
        return None
    parts = text.replace(" ", "").split(",")
    if len(parts) != 2:
        raise ValueError("--shooter-xy expects 'x,y'")
    return float(parts[0]), float(parts[1])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--image", help="analyze a saved screenshot instead of the live window")
    source.add_argument("--window", default="Graphwar", help="window title substring (default: Graphwar)")
    parser.add_argument("--shooter-index", type=int, default=None, help="index of the soldier that is firing")
    parser.add_argument("--allies", default="", help="comma-separated ally indices, e.g. 1,2")
    parser.add_argument("--shooter-xy", default="", help="fallback shooter position in world units, e.g. -12,3")
    parser.add_argument("--save-debug", default="", help="directory for capture, overlay, and mask images")
    parser.add_argument("--json", dest="json_out", default="", help="write the detected state as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        allies = _parse_indices(args.allies)
        shooter_xy = _parse_xy(args.shooter_xy)
        if args.image:
            frame = aim_capture.imread_unicode(args.image)
            if frame is None:
                print(f"cannot read image: {args.image}", file=sys.stderr)
                return 2
            source = f"image:{args.image}"
        else:
            frame, source = state_mod.capture_frame(args.window)

        scene = vision.analyze(frame)
        state = state_mod.build_state(
            scene,
            shooter_index=args.shooter_index,
            ally_indices=allies,
            shooter_xy=shooter_xy,
            source=source,
        )
    except Exception as exc:  # noqa: BLE001 - the probe is a diagnostic tool
        print(f"perception failed: {exc}", file=sys.stderr)
        return 1

    rect = scene.rect
    print(f"plot_rect=({rect.x0},{rect.y0},{rect.x1},{rect.y1}) "
          f"size={rect.width}x{rect.height} aspect={rect.width / max(rect.height, 1):.3f}")
    print(state.describe())
    print("obstacles:")
    for i, obstacle in enumerate(state.obstacles):
        print(f"  [{i}] world=({obstacle.x:7.2f},{obstacle.y:6.2f}) "
              f"r={obstacle.r:5.2f} sigma={obstacle.uncertainty:.2f}")

    if args.shooter_index is None and not args.shooter_xy:
        print("note: shooter_index was not given; the left-most soldier was assumed. "
              "Re-run with --shooter-index or --shooter-xy after checking the list above.")

    if args.save_debug:
        out_dir = vision.save_debug(frame, scene, args.save_debug)
        print(f"debug images: {out_dir}")

    if args.json_out:
        path = Path(args.json_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"state json: {path.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
