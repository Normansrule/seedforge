"""Run the hardware-free simulator.

    python -m seedforge.simulator --list
    python -m seedforge.simulator normal [--log runs/] [--quiet]
    python -m seedforge.simulator path/to/custom_scenario.txt

Scenarios exercise the same state machine as the Uno firmware (see
seedforge/simulator/core.py).  This simulates logic and timing only - it says
nothing about whether real veneer will wind well.
"""
from __future__ import annotations

import argparse
import sys
from importlib import resources
from pathlib import Path

from ..runlog import CARRIER_FIELDS, TRACE_FIELDS, CsvLog, new_id, now_iso
from .plant import Plant, run_script

ALIASES = {
    "normal": "normal_cycle", "estop": "estop", "tension-high": "tension_high", "vision-gap": "vision_gap",
    "heartbeat-timeout": "heartbeat_timeout", "home-switch-fault": "home_switch_fault", "m3": "m3_cycle",
}


def scenario_text(name: str) -> tuple[str, str]:
    p = Path(name)
    if p.suffix == ".txt" and p.exists():
        return p.stem, p.read_text()
    stem = ALIASES.get(name, name)
    ref = resources.files("seedforge.simulator") / "scenarios" / f"{stem}.txt"
    if not ref.is_file():
        raise SystemExit(f"unknown scenario {name!r}; try --list")
    return stem, ref.read_text()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m seedforge.simulator", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scenario", nargs="?", default="normal")
    ap.add_argument("--list", action="store_true", help="list built-in scenarios")
    ap.add_argument("--log", metavar="DIR", help="write carriers.csv and trace.csv into DIR")
    ap.add_argument("--quiet", action="store_true", help="hide STATUS lines")
    args = ap.parse_args(argv)

    if args.list:
        for alias, stem in ALIASES.items():
            text = (resources.files("seedforge.simulator") / "scenarios" / f"{stem}.txt").read_text()
            first = next((l[1:].strip() for l in text.splitlines() if l.startswith("#")), "")
            print(f"{alias:20s} {first}")
        return 0

    stem, text = scenario_text(args.scenario)
    plant = run_script(text, Plant())
    c = plant.ctrl
    for ms, line in plant.trace:
        if args.quiet and line.startswith("STATUS"):
            continue
        print(f"{ms / 1000:9.3f} s  {line}")
    print(f"\nfinal state {c.state}, fault {c.fault}; simulated {plant.now_ms / 1000:.1f} s; "
          f"mandrel turns {plant.phys_rot / 3200:.3f}; carriage {plant.phys_steps / 400:.2f} mm from home")

    if args.log:
        out = Path(args.log)
        run_id = new_id(f"SIM-{stem}")
        with CsvLog(out / "trace.csv", TRACE_FIELDS) as tr:
            for ms, state, rot, lin, pos, turns, tension, estop, home, end in plant.record:
                tr.write({"timestamp": f"{ms / 1000:.3f}", "run_id": run_id, "state": state, "rot_steps": rot,
                          "lin_steps": lin, "tension_N": None if tension is None else tension / 1000,
                          "limit_home": home, "limit_end": end, "estop_ok": estop, "notes": "simulated"})
        complete = [l for _, l in plant.trace if l.startswith("COMPLETE ")]
        fields = dict(t.split("=", 1) for t in complete[-1].split()[1:]) if complete else {}
        with CsvLog(out / "carriers.csv", CARRIER_FIELDS) as cl:
            cl.write({"timestamp": now_iso(), "carrier_id": new_id("SIMCARRIER"), "run_id": run_id,
                      "data_source": "SIMULATION - not a physical carrier", "pitch_mm": c.recipe.pitch_um / 1000,
                      "active_turns": c.recipe.active_turns, "sacrificial_turns": c.recipe.sacrificial_turns,
                      "winding_rate_rpm": c.recipe.rate_rpm_x10 / 10, "turn_count": fields.get("turns"),
                      "lin_steps": fields.get("lin_steps"), "mandrel_diameter_mm": 0.8,
                      "final_result": "SIM_COMPLETE" if c.state == "COMPLETE" else "SIM_STOPPED",
                      "fault": c.fault, "notes": f"scenario {stem}"})
        print(f"logs written to {out}/carriers.csv and {out}/trace.csv (run {run_id})")
    return 0 if c.state in ("COMPLETE", "SAFE_STOP", "READY", "BOOT") else 1


if __name__ == "__main__":
    sys.exit(main())
