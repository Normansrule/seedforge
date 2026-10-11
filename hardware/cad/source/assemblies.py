"""Viewer assemblies (GLB) for the website: tail-forming fixture, payload
cassette, output tray and the M3 clamp/cut/demold set.

These are LAYOUT/VISUALISATION arrangements of the R3 parts, not
fit-validated assemblies (only the core cell in core_cell.py is
interference-checked).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import cadquery as cq

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sf_cad_common import CAD_ROOT, PALETTE, load_step, write_glb  # noqa: E402
import paper_reference as pr  # noqa: E402


def m(stem):
    return load_step(CAD_ROOT / "step" / "machine" / f"{stem}.step")


def tail_former():
    P = PALETTE
    parts = [("T01_tail_former_left", m("T01_tail_former_left"), P["printed"]),
             ("T02_tail_former_right", m("T02_tail_former_right"), P["printed_accent"]),
             ("T03_tail_sweep_shoe", m("T03_tail_sweep_shoe").translate((0, 0, 9.0)), P["printed"]),
             ("T04_tail_blank_clamp", m("T04_tail_blank_clamp").translate((0, -40.0, 0)), P["printed"])]
    # wet auxiliary-tail blank: straight lead-in clamped in T04, wrapped part on the 14 mm former radius
    r = 14.0 + 0.25
    lead = cq.Workplane("XY").box(0.5, 30.0, 2.5).translate((r, -15.0, 6.0))
    arc = (cq.Workplane("XY").circle(r + 0.25).circle(r - 0.25).extrude(2.5)
           .intersect(cq.Workplane("XY").polyline([(0, 0), (40, 0), (40 * math.cos(math.radians(140)), 40 * math.sin(math.radians(140)))])
                      .close().extrude(2.5)).translate((0, 0, 4.75)))
    parts.append(("tail_blank_wet", lead.union(arc).val(), P["wood"]))
    return parts


def cassette():
    P = PALETTE
    parts = [("D01_four_cell_payload_cassette", m("D01_four_cell_payload_cassette"), P["printed"])]
    door = m("D02_single_drop_door")
    carrier = pr.build_models()[1][2][1]          # PR08 components
    for i, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        parts.append((f"D02_door_{i+1}", door.translate((sx * 37.5, sy * 37.5, -6.0)), P["printed_accent"]))
        for name, obj in carrier:
            parts.append((f"carrier{i+1}_{name}", obj.val().translate((sx * 37.5, sy * 37.5, 18.0)), pr.COLORS[name]))
    servo = m("D03_payload_servo_mount")
    for i, a in enumerate((0, 90, 180, 270)):
        parts.append((f"D03_servo_mount_{i+1}", servo.rotate((0, 0, 0), (0, 0, 1), a).translate(
            (90 * math.cos(math.radians(a)), 90 * math.sin(math.radians(a)), 20.0)), P["printed"]))
    return parts


def output_tray():
    P = PALETTE
    parts = [("O01_finished_seedpod_tray_12", m("O01_finished_seedpod_tray_12"), P["printed"])]
    carrier = pr.build_models()[1][2][1]
    for k in range(3):
        for name, obj in carrier:
            parts.append((f"carrier{k+1}_{name}", obj.val().rotate((0, 0, 0), (0, 1, 0), 90).translate((-40 + 40 * k, 0, 18.0)),
                          pr.COLORS[name]))
    return parts


def m3_station():
    P = PALETTE
    return [("X01_sg90_clamp_mount", m("X01_sg90_clamp_mount"), P["printed"]),
            ("X02_soft_clamp_jaw_a", m("X02_soft_clamp_jaw").translate((0, -8, 32)), P["silicone"]),
            ("X02_soft_clamp_jaw_b", m("X02_soft_clamp_jaw").rotate((0, 0, 0), (0, 0, 1), 180).translate((0, 8, 32)), P["silicone"]),
            ("X03_guarded_shear_mount", m("X03_guarded_shear_mount").translate((100, 0, 0)), P["printed"]),
            ("X04_cutter_guard", m("X04_cutter_guard").translate((100, 0, 6.0)), PALETTE["guard"]),
            ("W07_split_support_lower", m("W07_micro_release_clamp_lower").translate((-70, 0, 0)), P["printed_accent"]),
            ("W08_split_support_upper", m("W08_micro_release_clamp_upper").translate((-70, 6.0, 0)), P["printed_accent"])]


def drying_station():
    P = PALETTE
    carrier = pr.build_models()[1][2][1]
    parts = []
    for k in range(2):
        parts.append((f"Q01_free_dry_tray_{k+1}", m("Q01_free_dry_tray").translate((0, 0, 30.0 * k)), P["printed"]))
        for j in range(3):
            for name, obj in carrier:
                parts.append((f"tray{k+1}_wet_body{j+1}_{name}" if name == "body" else f"_skip_{k}_{j}_{name}",
                              obj.val().rotate((0, 0, 0), (0, 1, 0), 90).translate((-40 + 40 * j, -20 + 40 * (j % 2), 30.0 * k + 13.0)),
                              pr.COLORS[name]))
    parts = [p_ for p_ in parts if not p_[0].startswith("_skip")]
    parts.append(("Q02_120mm_usb_fan_bracket", m("Q02_120mm_usb_fan_bracket").rotate((0, 0, 0), (0, 0, 1), 90).translate((105, 0, 0)), P["printed"]))
    fan = cq.Workplane("YZ").rect(120, 120).extrude(25).cut(cq.Workplane("YZ").circle(56).extrude(25)).translate((108, 0, 64))
    hub = cq.Workplane("YZ").circle(20).extrude(20).translate((110, 0, 64))
    parts.append(("usb_fan_120mm", fan.union(hub).val(), P["dark_metal"]))
    return parts


def assembly_station():
    P = PALETTE
    carrier = pr.build_models()[1][2][1]
    parts = [("S04_three_tail_assembly_nest", m("S04_three_tail_assembly_nest"), P["printed"]),
             ("S05_10ml_syringe_holder", m("S05_10ml_syringe_holder").translate((0, 110, 0)), P["printed"]),
             ("S06_syringe_plunger_carriage", m("S06_syringe_plunger_carriage").translate((0, 110, 30)), P["printed_accent"]),
             ("S01_seed_hopper", m("S01_seed_hopper").translate((-120, 0, 0)), P["printed"]),
             ("S02_seed_singulator_disk_6mm", m("S02_seed_singulator_disk_6mm").translate((-120, 0, -8)), P["printed_accent"]),
             ("S07_tip_mold_half_A", m("S07_tip_mold_half_A").translate((120, 0, 0)), P["printed"]),
             ("S08_tip_mold_half_B", m("S08_tip_mold_half_B").translate((120, 0, 18)), P["printed_accent"])]
    for name, obj in carrier:
        parts.append((f"carrier_{name}", obj.val().translate((0, 0, 9.0)), pr.COLORS[name]))
    return parts


def main():
    glb = CAD_ROOT / "glb"
    write_glb(tail_former(), glb / "tail_former.glb", tol=0.05, ang=0.2)
    write_glb(cassette(), glb / "payload_cassette.glb", tol=0.06, ang=0.2)
    write_glb(output_tray(), glb / "output_tray.glb", tol=0.06, ang=0.2)
    write_glb(m3_station(), glb / "m3_clamp_cut_demold.glb", tol=0.08, ang=0.25)
    write_glb(drying_station(), glb / "drying_station.glb", tol=0.05, ang=0.2)
    write_glb(assembly_station(), glb / "assembly_station.glb", tol=0.05, ang=0.2)


if __name__ == "__main__":
    main()
