"""Run winding cycles from a recipe.

    python -m seedforge.host --port sim --recipe paper_reference --vision synthetic
    python -m seedforge.host --port /dev/ttyACM0 --recipe my_recipe.json --vision camera:0 --log runs/
    python -m seedforge.host --check-recipe course_target_45deg

--vision
  synthetic   render a synthetic image of the recipe's ideal coil and inspect it (software test only)
  camera:N    grab a frame from OpenCV camera N (fixed station camera) and inspect it
  manual      ask the operator to type the verdict (VISION_OK / FAULT_GAP / ...)
  none        recipe must have require_vision=false
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .. import recipe as rmod
from .runner import Runner, open_transport


def load_recipe(name: str) -> rmod.Recipe:
    p = Path(name)
    return rmod.load(p) if p.suffix == ".json" else rmod.builtin(name)


def make_vision(spec: str):
    from ..vision.pipeline import Thresholds, inspect
    if spec == "none":
        return None

    def thresholds(r: rmod.Recipe) -> Thresholds:
        v = r.vision
        return Thresholds(px_per_mm=v.get("px_per_mm", 40.0), strip_w_mm=r.strip_width_mm, strip_t_mm=r.strip_thickness_mm,
                          mandrel_d_mm=r.mandrel_diameter_mm, expected_pitch_mm=r.pitch_mm,
                          # every turn still on the mandrel at VERIFY is visible: active + sacrificial
                          expected_turns=r.active_turns + r.sacrificial_turns,
                          pitch_tol_frac=v.get("pitch_tol_frac", 0.15), turns_tol=v.get("turns_tol", 0.5),
                          max_gap_mm=v.get("max_gap_mm", 1.6), max_overlap_mm=v.get("max_overlap_mm", 0.4),
                          max_axis_sag_mm=v.get("max_axis_sag_mm", 0.5))

    if spec == "synthetic":
        from ..vision.synth import CoilSpec, render

        def run(r):
            img = render(CoilSpec(mandrel_d=r.mandrel_diameter_mm, strip_w=r.strip_width_mm, strip_t=r.strip_thickness_mm,
                                  pitch=r.pitch_mm, turns=r.active_turns + r.sacrificial_turns, px_per_mm=r.vision.get("px_per_mm", 40.0)))
            return inspect(img, thresholds(r)).summary()
        return run
    if spec.startswith("camera:"):
        import cv2
        idx = int(spec.split(":", 1)[1])

        def run(r):
            cap = cv2.VideoCapture(idx)
            ok, frame = cap.read()
            cap.release()
            if not ok:
                return {"event": "FAULT_CAMERA", "ok": False, "reasons": ["camera read failed"]}
            return inspect(frame, thresholds(r)).summary()
        return run
    if spec == "manual":
        def run(r):
            ans = input("verdict [VISION_OK/FAULT_GAP/FAULT_OVERLAP/FAULT_LENGTH/FAULT_TAIL/FAULT_CAMERA]: ").strip().upper()
            return {"event": ans if ans.startswith(("VISION_OK", "FAULT_")) else "FAULT_CAMERA", "ok": ans == "VISION_OK"}
        return run
    raise SystemExit(f"unknown --vision {spec}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m seedforge.host", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", default="sim", help="serial port, tcp:HOST[:PORT], or sim")
    ap.add_argument("--recipe", default="paper_reference", help="built-in name or path to a .json recipe")
    ap.add_argument("--vision", default="synthetic")
    ap.add_argument("--cycles", type=int, default=1)
    ap.add_argument("--log", metavar="DIR")
    ap.add_argument("--speed", type=float, default=20.0, help="simulator time scale (sim only)")
    ap.add_argument("--check-recipe", metavar="RECIPE", help="validate a recipe and exit")
    args = ap.parse_args(argv)

    if args.check_recipe:
        r = load_recipe(args.check_recipe)
        errs, warns = r.validate()
        print(f"recipe {r.name}: guide angle {r.derived_guide_angle:.1f} deg (from pitch)")
        for w in warns:
            print("  WARNING", w)
        for e in errs:
            print("  ERROR  ", e)
        return 1 if errs else 0

    r = load_recipe(args.recipe)
    t = open_transport(args.port, args.speed)
    try:
        runner = Runner(t, r, args.log, make_vision(args.vision))
        if not runner.prepare():
            print("not ready; stopping (no automatic RESET)")
            return 2
        for k in range(args.cycles):
            res = runner.cycle()
            print(f"cycle {k + 1}: {res.final_state} fault={res.fault} vision={res.vision and res.vision.get('event')} "
                  f"carrier={res.carrier_id}")
            if res.final_state != "COMPLETE":
                return 3
    finally:
        t.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
