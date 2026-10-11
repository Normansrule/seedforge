#!/usr/bin/env python3
"""Prepare generated data and figures for the website (run before `npm run build`).

    python tools/build_site_data.py

Writes website/public/data/{status,parts,geometry,site}.json and copies the
renders and diagrams from docs/ into website/public/img/ (git-ignored copy;
docs/ is the source).
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "software"))

from seedforge import __version__  # noqa: E402
from seedforge import geometry as geo  # noqa: E402

SITE = ROOT / "website" / "public"


def status() -> dict:
    import yaml  # pyyaml, in the dev extra
    return yaml.safe_load((ROOT / "validation" / "status.yaml").read_text())


def parts() -> list[dict]:
    rows = list(csv.DictReader((ROOT / "hardware" / "cad" / "manifest.csv").open()))
    keep = ["part_id", "file_stem", "family", "module", "status", "qty", "material", "bbox_x_mm", "bbox_y_mm",
            "bbox_z_mm", "volume_cm3", "watertight", "bodies", "fits_a1_mini", "cad_valid", "print_successful",
            "physically_fits", "notes"]
    return [{k: r.get(k, "") for k in keep} for r in rows]


def geometry() -> list[dict]:
    out = []
    for r in geo.reference_cases():
        out.append({"name": r.name, "pitch_mm": r.p, "strip_angle_deg": r.strip_angle_deg, "guide_angle_deg": r.guide_angle_deg,
                    "normal_gap_mm": r.normal_gap_mm, "butt_joint_pitch_mm": r.butt_joint_pitch_mm,
                    "body_length_mm": r.body_length_mm, "width_mm": r.w})
    return out


def sim_traces() -> dict:
    """Real output of the Python simulator (same state machine as the firmware) for the site replay."""
    from importlib import resources
    from seedforge.simulator.plant import run_script
    out = {}
    for name in ("normal_cycle", "estop", "tension_high", "vision_gap", "heartbeat_timeout", "home_switch_fault", "m3_cycle"):
        text = (resources.files("seedforge.simulator") / "scenarios" / f"{name}.txt").read_text()
        p = run_script(text)
        desc = next((l[1:].strip() for l in text.splitlines() if l.startswith("#")), "")
        lines = [[ms, line] for ms, line in p.trace if not line.startswith("STATUS")]
        out[name] = {"description": desc, "final_state": p.ctrl.state, "fault": p.ctrl.fault, "trace": lines}
    return out


def main():
    data = SITE / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / "status.json").write_text(json.dumps(status(), indent=1, default=str))
    (data / "parts.json").write_text(json.dumps(parts(), indent=1))
    (data / "geometry.json").write_text(json.dumps(geometry(), indent=1))
    layout = json.loads((ROOT / "hardware" / "cad" / "source" / "core_cell_layout.json").read_text())
    (data / "site.json").write_text(json.dumps({
        "version": "v0.3.0-alpha", "package_version": __version__, "revision": "R3.1",
        "repo": "https://github.com/Normansrule/seedforge",
        "windows": layout.get("collision_free_carriage_window_mm", {}),
        "static_interference": len(layout.get("static_interference", [])),
    }, indent=1))
    vis = ROOT / "datasets" / "synthetic_reference" / "report.json"
    if vis.exists():
        (data / "vision.json").write_text(vis.read_text())
    (data / "sim_traces.json").write_text(json.dumps(sim_traces(), indent=0))
    # viewer models: copies of hardware/cad/glb (source of truth), not tracked in git
    models = SITE / "models"
    if models.exists():
        shutil.rmtree(models)
    shutil.copytree(ROOT / "hardware" / "cad" / "glb", models)
    img = SITE / "img"
    if img.exists():
        shutil.rmtree(img)
    img.mkdir(parents=True)
    n = 0
    for src in list((ROOT / "docs" / "images").glob("*.png")) + list((ROOT / "docs" / "diagrams").glob("*.svg")) + \
            list((ROOT / "docs" / "animations").glob("*.gif")) + [ROOT / "hardware" / "electronics" / "seedforge_core_schematic.svg"]:
        shutil.copy2(src, img / src.name)
        n += 1
    print(f"site data written; {n} figures copied to website/public/img")


if __name__ == "__main__":
    main()
