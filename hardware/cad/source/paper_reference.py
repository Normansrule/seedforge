"""Paper-inspired reference geometry for SeedForge (MR/PR series).

Source-of-truth generator for the forming-mandrel references (MR01-MR07) and
the seed-carrier reference models (PR01-PR24).

Provenance labels (see docs/references.md):
  SOURCE-SUPPORTED       - mandrel diameter, coil count, body length, ribbon
                           width/thickness, tail path lengths, large-pine
                           dimensions, as reported in Luo et al. (2023) and its
                           supplementary material.
  RECONSTRUCTED REFERENCE - free-shape tail splines, tip surface, seed
                           envelopes.  These are engineering approximations for
                           fixture/clearance design, NOT the authors' CAD.

The 1:1 models are not functional seed carriers: the real device depends on
prepared wood and a biodegradable tip.  Do not print them as carriers.

Refactored in R3.1 from the R2 generator (archived at
archive/seedforge-r3-package/cad/paper_reference/source/): hard-coded paths
removed, MR07 added (it was shipped but missing from the generator) and PR24
generated at 3x (the shipped file is 3x; the old script said 4x).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import cadquery as cq

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sf_cad_common import (CAD_ROOT, PALETTE, export_part, shape_to_trimesh,  # noqa: E402
                           write_3mf, write_glb, write_stl)

PARAMS = {
    "paper_standard_reference": {
        "tails": 3, "coil_layers": 1, "coil_turns": 7, "coil_axial_length_mm": 35.0,
        "mandrel_diameter_mm": 0.8, "ribbon_width_mm": 2.5, "ribbon_thickness_mm": 0.5,
        "tail_path_lengths_mm": [27.0, 29.5, 32.5], "resting_angle_paper_deg_range": [25, 30],
        "provenance": "SOURCE-SUPPORTED dimensions; tail/tip free shape is RECONSTRUCTED REFERENCE",
        "notes": ("Width/thickness/tail dimensions follow the paper/preprint supplementary simulation. "
                  "The published protocol notes many standard three-tail samples used ~0.4 mm veneer; "
                  "0.5 mm is retained to match the course machine specification and the simulation geometry."),
    },
    "large_whitebark_pine_reference": {
        "tails": 3, "coil_layers": 1, "coil_turns": 7, "coil_axial_length_mm": 85.0,
        "mandrel_diameter_mm": 3.0, "ribbon_width_mm": 12.0, "ribbon_thickness_mm": 0.8,
        "flat_veneer_length_mm": 300.0, "seed_length_mm": 11.0,
        "notes": "Large-tail lengths and tip mold geometry were not available, so PR23 omits tails rather than inventing them.",
    },
    "course_target": {
        "strip_width_mm": 4.0, "strip_thickness_mm": 0.5, "mandrel_diameter_mm": 0.8,
        "nominal_guide_angle_deg": 45, "active_turns": 7,
        "notes": "Course/experimental target. See docs/carrier-geometry.md: not gap-free as stated; keep angle and pitch as recipe variables.",
    },
}

COLORS = {"body": PALETTE["wood"], "tail1": PALETTE["wood_light"], "tail2": PALETTE["wood"],
          "tail3": PALETTE["wood_dark"], "tip": PALETTE["tip"], "seed": PALETTE["seed"],
          "hair_envelope": PALETTE["envelope"], "mandrel": PALETTE["metal"],
          "chuck": PALETTE["dark_metal"], "stop": PALETTE["printed"]}


# --------------------------------------------------------------------------- geometry
def helix_ribbon(mandrel_d=0.8, thickness=0.5, width=2.5, turns=7, axial_length=35.0, z0=0.0):
    """Rectangular ribbon swept along a helix on the mandrel surface.

    Pitch = axial_length / turns.  The ribbon centre-line radius is
    mandrel_d/2 + thickness/2 (single layer).
    """
    pitch = axial_length / turns
    r = mandrel_d / 2 + thickness / 2
    helix = cq.Wire.makeHelix(pitch, axial_length, r)
    if z0:
        helix = helix.translate(cq.Vector(0, 0, z0))
    normal = cq.Vector(0, 2 * math.pi * r, pitch).normalized()
    plane = cq.Plane(origin=(r, 0, z0), xDir=cq.Vector(1, 0, 0), normal=normal)
    return cq.Workplane(plane).rect(thickness, width).sweep(helix, isFrenet=True)


def spiral_tail(phi_deg, target_length, width=2.5, thickness=0.5, z0=35.0,
                sweep_deg=205, rise=7.0, drop=7.0, r0=1.3):
    """RECONSTRUCTED free-shape tail: spline whose path length = target_length."""
    phi = math.radians(phi_deg)
    sweep = math.radians(sweep_deg)
    n = 100

    def pts(rend):
        arr = []
        for i in range(n + 1):
            u = i / n
            th = phi + sweep * u
            r = r0 + (rend - r0) * (u ** 0.82)
            z = z0 + rise * math.sin(math.pi * u) - drop * (u ** 1.15)
            arr.append((r * math.cos(th), r * math.sin(th), z))
        return arr

    def plen(a):
        return sum(math.dist(x, y) for x, y in zip(a, a[1:]))

    lo, hi = 1.5, 80.0
    for _ in range(70):           # bisection on end radius
        mid = (lo + hi) / 2
        if plen(pts(mid)) < target_length:
            lo = mid
        else:
            hi = mid
    arr = pts((lo + hi) / 2)
    tangent = cq.Vector(*(arr[1][j] - arr[0][j] for j in range(3))).normalized()
    xdir = cq.Vector(0, 0, 1).cross(tangent)
    if xdir.Length < 1e-8:
        xdir = cq.Vector(1, 0, 0)
    plane = cq.Plane(origin=arr[0], xDir=xdir.normalized(), normal=tangent)
    wire = cq.Wire.assembleEdges([cq.Edge.makeSpline([cq.Vector(*p) for p in arr])])
    return cq.Workplane(plane).rect(width, thickness).sweep(wire, isFrenet=True)


def teardrop_tip(length=14.0, max_d=5.5, neck_d=2.4, z_top=0.4):
    zs = [-length, -0.78 * length, -0.45 * length, -0.12 * length, z_top]
    ds = [0.6, 2.8, max_d, max_d * 0.72, neck_d]
    wires = [cq.Workplane("XY", origin=(0, 0, z)).circle(d / 2).wire().val() for z, d in zip(zs, ds)]
    return cq.Workplane(obj=cq.Solid.makeLoft(wires, ruled=False))


def ellipsoid(rx, ry, rz, center=(0, 0, 0)):
    cx, cy, cz = center
    zs = [-rz, -0.7 * rz, 0, 0.7 * rz, rz]
    scales = [0.05, 0.72, 1.0, 0.72, 0.05]
    wires = [cq.Workplane("XY", origin=(cx, cy, cz + z)).ellipse(rx * s, ry * s).wire().val()
             for z, s in zip(zs, scales)]
    return cq.Workplane(obj=cq.Solid.makeLoft(wires, ruled=False))


def rod(d, length):
    return cq.Workplane("XY").circle(d / 2).extrude(length)


def scaled(obj, factor):
    vals = [v.scale(factor) for v in obj.vals()]
    return cq.Workplane(obj=vals[0] if len(vals) == 1 else cq.Compound.makeCompound(vals))


# --------------------------------------------------------------------------- build
def build_models():
    std = PARAMS["paper_standard_reference"]
    body = helix_ribbon(std["mandrel_diameter_mm"], std["ribbon_thickness_mm"], std["ribbon_width_mm"],
                        std["coil_turns"], std["coil_axial_length_mm"])
    t1 = spiral_tail(0, 27.0)
    t2 = spiral_tail(120, 29.5)
    t3 = spiral_tail(240, 32.5)
    tip = teardrop_tip(14, 5.5, 2.4, 0.5)
    seed = ellipsoid(1.8, 1.25, 2.4, (0, 0, -6.0))
    hair_env = teardrop_tip(16.0, 9.2, 4.0, 0.7)

    mandrel08 = rod(0.8, 100)
    mandrel3 = rod(3.0, 140)
    collet = (cq.Workplane("XY").circle(2.5).circle(0.45).extrude(12)
              .cut(cq.Workplane("XZ").box(0.7, 12, 3.0, centered=(True, False, True)).translate((0, 0, 6))))
    stop = (cq.Workplane("XY").circle(4).circle(0.5).extrude(5)
            .cut(cq.Workplane("YZ", origin=(0, 0, 2.5)).circle(1.1).extrude(10, both=True)))
    bushing = cq.Workplane("XY").circle(4).circle(0.5).extrude(10)
    chuck = (cq.Workplane("XY").circle(6).extrude(18).translate((0, 0, -18))
             .union(cq.Workplane("XY").circle(3).extrude(8).translate((0, 0, -26))))

    large_body = helix_ribbon(3.0, 0.8, 12.0, 7, 85.0)
    pine_seed = ellipsoid(4.5, 2.8, 5.5, (0, 0, -10))
    large_tip = teardrop_tip(28, 14, 5.5, 1.0)

    singles = [
        ("PR01_standard_7coil_body_2p5x0p5_on_0p8", body, "SOURCE-SUPPORTED: 7 turns over 35 mm; 2.5 x 0.5 mm ribbon; 0.8 mm mandrel."),
        ("PR02_standard_tail1_27mm", t1, "Tail path length 27 mm (SOURCE-SUPPORTED); free shape RECONSTRUCTED."),
        ("PR03_standard_tail2_29p5mm", t2, "Tail path length 29.5 mm (SOURCE-SUPPORTED); free shape RECONSTRUCTED."),
        ("PR04_standard_tail3_32p5mm", t3, "Tail path length 32.5 mm (SOURCE-SUPPORTED); free shape RECONSTRUCTED."),
        ("PR05_standard_tip_outer_reference", tip, "RECONSTRUCTED tip envelope for fixture design."),
        ("PR06_standard_seed_payload_envelope", seed, "RECONSTRUCTED small-seed envelope; not a botanical replica."),
        ("PR07_tip_hair_clearance_envelope", hair_env, "RECONSTRUCTED clearance envelope for flocked tip fibres."),
        ("PR10_primary_blank_48x2p5x0p5_reference", cq.Workplane("XY").box(48.0, 2.5, 0.5, centered=(False, True, False)), "Flat primary strip reference."),
        ("PR11_aux_tail_blank_29p5x2p5x0p5_reference", cq.Workplane("XY").box(29.5, 2.5, 0.5, centered=(False, True, False)), "Flat auxiliary tail blank."),
        ("PR12_aux_tail_blank_32p5x2p5x0p5_reference", cq.Workplane("XY").box(32.5, 2.5, 0.5, centered=(False, True, False)), "Flat auxiliary tail blank."),
        ("MR01_0p8mm_x100mm_FORMING_MANDREL_REFERENCE", mandrel08, "Envelope only. Buy straight 0.8 mm stainless/spring-steel rod; never print."),
        ("MR02_0p8mm_to_5mm_split_collet_INSERT", collet, "Experimental printed collet; a metal pin vise/chuck is the baseline."),
        ("MR03_mandrel_depth_stop_M2", stop, "Depth stop collar, M2 cross hole; ream 1.0 mm bore."),
        ("MR04_0p8mm_guide_bushing", bushing, "Guide bushing reference; PTFE/brass tube preferred."),
        ("MR05_3mm_x140mm_LARGE_PINE_MANDREL_REFERENCE", mandrel3, "Large-pine mandrel envelope; actual part is metal."),
        ("PR20_LARGE_PINE_7COIL_BODY_12x0p8_on_3mm", large_body, "SOURCE-SUPPORTED: 12 x 0.8 mm veneer, 3 mm mandrel, 7 coils, 85 mm."),
        ("PR21_whitebark_pine_seed_11mm_ENVELOPE", pine_seed, "11 mm seed clearance envelope."),
        ("PR22_large_pine_tip_outer_ENVELOPE", large_tip, "RECONSTRUCTED large tip envelope."),
    ]
    assemblies = [
        ("MR06_COMPLETE_0p8mm_MANDREL_SUBASSEMBLY_REFERENCE",
         [("mandrel", mandrel08.translate((0, 0, -2))), ("chuck", chuck), ("stop", stop.translate((0, 0, 56)))]),
        ("MR07_0p8mm_MANDREL_WITH_STANDARD_7COIL_BODY_REFERENCE", [("mandrel", mandrel08), ("body", body)]),
        ("PR08_STANDARD_FINISHED_3TAIL_SEED_CARRIER_1TO1",
         [("body", body), ("tail1", t1), ("tail2", t2), ("tail3", t3), ("tip", tip), ("seed", seed)]),
        ("PR09_STANDARD_SEED_CARRIER_EXPLODED_1TO1",
         [("body", body), ("tail1", t1.translate((26, 0, 8))), ("tail2", t2.translate((-14, 24, 8))),
          ("tail3", t3.translate((-14, -24, 8))), ("tip", tip.translate((0, 0, -22))), ("seed", seed.translate((12, 0, -22)))]),
        ("PR23_LARGE_PINE_BODY_TIP_SEED_REFERENCE_NO_TAILS",
         [("body", large_body), ("tip", large_tip), ("seed", pine_seed)]),
    ]
    pr08 = assemblies[2][1]
    assemblies.append(("PR24_STANDARD_FINISHED_CARRIER_3X_DEMO_PRINT", [(n, scaled(o, 3.0)) for n, o in pr08]))
    return singles, assemblies


def export_assembly(stem, components):
    assy = cq.Assembly(name=stem)
    for name, obj in components:
        r, g, b, a = COLORS.get(name, (160, 160, 160, 255))
        assy.add(obj, name=name, color=cq.Color(r / 255, g / 255, b / 255, a / 255))
    path = CAD_ROOT / "step" / "reference" / f"{stem}.step"
    path.parent.mkdir(parents=True, exist_ok=True)
    assy.save(str(path))
    meshes = {name: shape_to_trimesh(obj) for name, obj in components}
    import trimesh
    write_stl(trimesh.util.concatenate(list(meshes.values())), CAD_ROOT / "stl" / "reference" / f"{stem}.stl")
    write_3mf(meshes, CAD_ROOT / "3mf" / "reference" / f"{stem}.3mf")
    return meshes


def main() -> dict:
    singles, assemblies = build_models()
    notes = {}
    for stem, shape, note in singles:
        export_part(shape, stem, "reference")
        notes[stem] = note
    comps = {}
    for stem, components in assemblies:
        export_assembly(stem, components)
        comps[stem] = components
    (CAD_ROOT / "source" / "paper_reference_parameters.json").write_text(json.dumps(PARAMS, indent=2) + "\n")

    # Web-viewer GLBs (finer tolerance: these parts are millimetre-scale).
    glb = CAD_ROOT / "glb"
    write_glb([(n, o, COLORS[n]) for n, o in comps["PR08_STANDARD_FINISHED_3TAIL_SEED_CARRIER_1TO1"]],
              glb / "finished_carrier.glb", tol=0.01, ang=0.2)
    write_glb([(n, o, COLORS[n]) for n, o in comps["PR09_STANDARD_SEED_CARRIER_EXPLODED_1TO1"]],
              glb / "exploded_carrier.glb", tol=0.01, ang=0.2)
    write_glb([(n, o, COLORS[n]) for n, o in comps["MR06_COMPLETE_0p8mm_MANDREL_SUBASSEMBLY_REFERENCE"]],
              glb / "mandrel_assembly.glb", tol=0.01, ang=0.2)
    write_glb([(n, o, COLORS[n]) for n, o in comps["MR07_0p8mm_MANDREL_WITH_STANDARD_7COIL_BODY_REFERENCE"]],
              glb / "mandrel_with_coil.glb", tol=0.008, ang=0.2)
    return notes


if __name__ == "__main__":
    main()
    print("paper reference models regenerated")
