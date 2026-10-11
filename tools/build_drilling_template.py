#!/usr/bin/env python3
"""1:1 drilling template for the Phase-1 core-cell plywood base.

    python tools/build_drilling_template.py

Slices every part that stands on the plywood (R3.1 layout in
hardware/cad/source/core_cell.py) 0.3 mm above the base and draws the
footprint outlines, including their bolt holes, at 1 mm = 1 mm.  Holes get a
centre cross so they can be centre-punched through the paper.

Output: hardware/drawings/core_cell_drilling_template.svg
Print at 100 % (poster/tiled printing), check the 100 mm scale bars in both
directions, tape it to the plywood.  CAD-derived: hole positions on the real
parts may differ slightly - mark through the printed parts when in doubt.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hardware" / "cad" / "source"))

import numpy as np  # noqa: E402

import core_cell as cc  # noqa: E402
from sf_cad_common import shape_to_trimesh  # noqa: E402

OUT = ROOT / "hardware" / "drawings" / "core_cell_drilling_template.svg"
Z_CUT = 0.3
SKIP = {"base_plywood_18mm"}
LABELS = {
    "W01_nema17_rotation_mount": "W01", "W13_w05_axis_riser_11mm": "W13", "W09_linear_motor_end_block": "W09",
    "W10_linear_idler_end_block": "W10", "F09_spool_stand_left_608_bore": "F09", "F02_spool_stand_right": "F02",
    "F11_dancer_pivot_post": "F11", "F08_load_cell_mount": "F08", "backlight_standoffs": "back-light standoffs",
    "W15_nema17_body_clamp_rotation": "W15", "W16_nema17_body_clamp_linear": "W16", "W17_camera_mast_foot": "W17",
    "camera_mast_plywood": "plywood mast",
}


def polygons_at(shape, z):
    mesh = shape_to_trimesh(shape, tol=0.05, ang=0.1)
    sec = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if sec is None:
        return []
    out = []
    for ent in sec.entities:
        pts = sec.vertices[ent.points][:, :2]
        out.append(np.asarray(pts))
    return out


def is_hole(poly):
    """Small closed loops roughly circular -> bolt holes."""
    if len(poly) < 8:
        return None
    c = poly.mean(axis=0)
    r = np.linalg.norm(poly - c, axis=1)
    if r.mean() < 8.0 and r.std() < 0.08 * r.mean():
        return c, r.mean()
    return None


def main():
    new_parts = {stem: fn().val() for stem, (fn, *_r) in cc.NEW_PARTS.items()}
    parts = cc.build_layout(cc.Layout(), new_parts, with_material=False)
    base = next(s for n, s, _, _ in parts if n == "base_plywood_18mm").BoundingBox()
    x0, x1, y0, y1 = base.xmin, base.xmax, base.ymin, base.ymax
    W, H = x1 - x0, y1 - y0
    m = 20.0  # paper margin, mm
    # SVG: x to the right, CAD y up -> flip.
    tx = lambda x: x - x0 + m  # noqa: E731
    ty = lambda y: (y1 - y) + m  # noqa: E731
    els = []
    holes_total = 0
    for name, shape, _, _ in parts:
        if name in SKIP:
            continue
        bb = shape.BoundingBox()
        if bb.zmin > 0.5 or bb.zmax < Z_CUT:
            continue
        polys = polygons_at(shape, Z_CUT)
        if not polys:
            continue
        for p in polys:
            h = is_hole(p)
            d = "M " + " L ".join(f"{tx(a):.2f},{ty(b):.2f}" for a, b in p) + " Z"
            if h:
                (cx, cy), r = h
                holes_total += 1
                els.append(f'<path d="{d}" fill="none" stroke="#c0392b" stroke-width="0.25"/>')
                k = r + 2.5
                els.append(f'<path d="M {tx(cx) - k:.2f},{ty(cy):.2f} H {tx(cx) + k:.2f} M {tx(cx):.2f},{ty(cy) - k:.2f} '
                           f'V {ty(cy) + k:.2f}" stroke="#c0392b" stroke-width="0.2"/>')
                els.append(f'<text x="{tx(cx) + r + 1:.2f}" y="{ty(cy) - r - 0.5:.2f}" font-size="2.2" fill="#c0392b">'
                           f'{2 * r:.1f}</text>')
            else:
                els.append(f'<path d="{d}" fill="none" stroke="#14273a" stroke-width="0.35"/>')
        lab = LABELS.get(name, name)
        els.append(f'<text x="{tx((bb.xmin + bb.xmax) / 2):.2f}" y="{ty((bb.ymin + bb.ymax) / 2):.2f}" font-size="5" '
                   f'text-anchor="middle" fill="#2f6f4f" font-weight="bold">{lab}</text>')

    # datum: mandrel axis projection and traverse axis
    els.append(f'<path d="M {tx(-60):.2f},{ty(0):.2f} H {tx(140):.2f}" stroke="#2f6f4f" stroke-width="0.3" stroke-dasharray="4 2"/>')
    els.append(f'<text x="{tx(142):.2f}" y="{ty(0) + 1.2:.2f}" font-size="3.5" fill="#2f6f4f">mandrel axis (y = 0, 37.0 mm above base)</text>')
    els.append(f'<path d="M {tx(-60):.2f},{ty(cc.LIN_Y):.2f} H {tx(200):.2f}" stroke="#2f6f4f" stroke-width="0.3" stroke-dasharray="4 2"/>')
    els.append(f'<text x="{tx(-20):.2f}" y="{ty(cc.LIN_Y) + 5:.2f}" font-size="3.5" fill="#2f6f4f">traverse axis (y = {cc.LIN_Y:.0f}, rods 22 mm above base)</text>')
    # scale bars
    sx, sy = tx(x1) - 110, ty(y0) - 15
    els.append(f'<path d="M {sx:.2f},{sy:.2f} h 100 M {sx:.2f},{sy - 2:.2f} v 4 M {sx + 100:.2f},{sy - 2:.2f} v 4" stroke="#000" stroke-width="0.4"/>')
    els.append(f'<text x="{sx:.2f}" y="{sy - 4:.2f}" font-size="3.5">100 mm - check after printing</text>')
    vx, vy = tx(x1) - 12, ty(y0) - 130
    els.append(f'<path d="M {vx:.2f},{vy:.2f} v 100 M {vx - 2:.2f},{vy:.2f} h 4 M {vx - 2:.2f},{vy + 100:.2f} h 4" stroke="#000" stroke-width="0.4"/>')
    title = (f'<text x="{m + 5}" y="{m + 10}" font-size="7" font-weight="bold" fill="#14273a">SeedForge R3.1 core cell - plywood drilling template 1:1</text>'
             f'<text x="{m + 5}" y="{m + 18}" font-size="3.6" fill="#5b6b7a">Base {W:.0f} x {H:.0f} mm. Outlines = part footprints at the base; red = holes '
             f'(diameter in mm, CAD; all 2.4 mm = M2 wood screws), centre-punch at the crosses. Generated by tools/build_drilling_template.py. CAD-derived: '
             f'measure before final fabrication.</text>')
    border = f'<rect x="{m}" y="{m}" width="{W:.2f}" height="{H:.2f}" fill="none" stroke="#999" stroke-width="0.4"/>'
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W + 2 * m:.0f}mm" height="{H + 2 * m:.0f}mm" '
           f'viewBox="0 0 {W + 2 * m:.2f} {H + 2 * m:.2f}" font-family="Helvetica, Arial, sans-serif">'
           f'<rect width="100%" height="100%" fill="#fff"/>{border}{title}{"".join(els)}</svg>\n')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg)
    print(f"drilling template: {OUT.relative_to(ROOT)} ({holes_total} holes)")


if __name__ == "__main__":
    main()
