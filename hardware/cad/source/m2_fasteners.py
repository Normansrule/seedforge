"""M2-only fastener conversion for the R3 machine parts (R3.2 fastener standard).

SeedForge uses one fastener size everywhere: M2 (screws, nuts, washers, M2 wood
screws into the plywood, M2 thread-forming screws into printed pilots).  The R3
parts were drawn for M3/M4/M5.  Their STEP files are kept unchanged in
``r3_step/`` as the source of truth; this module rewrites the screw holes and
writes the converted STEP to ``hardware/cad/step/machine/`` on every build.

How a hole is converted
-----------------------
Concave cylindrical faces are grouped by axis and radius.  A group whose faces
sweep a full 360 degrees is a hole (half-cylinders such as slot ends and concave
fillets are left alone).  The hole is filled with a tube from the new to the old
diameter over exactly the same axial extent, so through holes stay through, blind
holes keep their depth, and counterbores above a converted hole are untouched
(an M2 head simply sits lower).

Rules (diameter in mm, +-0.06):
  3.4 -> 2.4   M3 clearance  -> M2 clearance
  2.9 -> 1.8   M3 tap/pilot  -> M2 thread-forming pilot
  plus per-part rules below (M4/M5 base screws -> M2 wood-screw clearance, etc.)

Not converted, on purpose: bearing/rod/shaft bores, vent and drain holes, pins
and hinge holes, slot ends, the C01/D04/R05/R06 M5 slots and 2020-extrusion
interfaces (optional/upcoming parts; see hardware/cad/README.md), and M3 hex nut
traps (an M2 nut + M2 washer sits in them).
"""
from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder

M2_CLEAR = 2.4
M2_PILOT = 1.8

GLOBAL_RULES = {3.4: M2_CLEAR, 2.9: M2_PILOT}
PART_RULES = {
    "W01": {5.5: M2_CLEAR},            # base screws (M5) -> M2 wood screws
    "Q02": {4.5: M2_CLEAR},            # 120 mm fan corners: M2 + washers through the fan's own holes
    "S07": {3.2: M2_CLEAR},            # mould-half clamp holes
    "S08": {3.2: M2_CLEAR},
}
TOL = 0.06


def _rules(part_id: str) -> dict[float, float]:
    r = dict(GLOBAL_RULES)
    r.update(PART_RULES.get(part_id, {}))
    return r


def holes(shape: cq.Shape):
    """Yield (diameter, axis point, axis dir, v0, v1) for full 360-degree concave cylinders."""
    groups = defaultdict(list)
    for face in shape.Faces():
        ad = BRepAdaptor_Surface(face.wrapped)
        if ad.GetType() != GeomAbs_Cylinder:
            continue
        cyl = ad.Cylinder()
        r = cyl.Radius()
        if 2 * r > 12:
            continue
        ax = cyl.Axis()
        p0, d = ax.Location(), ax.Direction()
        u0, u1, v0, v1 = ad.FirstUParameter(), ad.LastUParameter(), ad.FirstVParameter(), ad.LastVParameter()
        P = ad.Value((u0 + u1) / 2, (v0 + v1) / 2)
        c = cq.Vector(P.X(), P.Y(), P.Z())
        try:
            n = face.normalAt(c)
        except Exception:      # noqa: BLE001 - degenerate face: skip
            continue
        o = cq.Vector(p0.X(), p0.Y(), p0.Z())
        dv = cq.Vector(d.X(), d.Y(), d.Z())
        radial = (c - o) - dv * (c - o).dot(dv)
        if radial.dot(n) >= 0:          # convex: a boss or shaft, not a hole
            continue
        # canonical axis: direction with positive largest component, point = foot of perpendicular from origin
        if max((abs(dv.x), dv.x), (abs(dv.y), dv.y), (abs(dv.z), dv.z))[1] < 0:
            dv = dv * -1
            v0, v1 = -v1, -v0
        t = o.dot(dv)
        foot = o - dv * t
        key = (round(2 * r, 2), round(foot.x, 2), round(foot.y, 2), round(foot.z, 2),
               round(dv.x, 3), round(dv.y, 3), round(dv.z, 3))
        groups[key].append((u1 - u0, v0 + t, v1 + t))
    for key, items in groups.items():
        span = sum(i[0] for i in items)
        if span < 2 * math.pi - 0.02:
            continue
        v0 = min(i[1] for i in items)
        v1 = max(i[2] for i in items)
        dia = key[0]
        foot = cq.Vector(*key[1:4])
        dv = cq.Vector(*key[4:7])
        yield dia, foot, dv, v0, v1


def _tube(d_out, d_in, foot, dv, v0, v1):
    base = foot + dv * v0
    length = v1 - v0
    pl = cq.Plane(origin=base.toTuple(), xDir=_perp(dv).toTuple(), normal=dv.toTuple())
    return cq.Workplane(pl).circle(d_out / 2).circle(d_in / 2).extrude(length).val()


def _perp(v: cq.Vector) -> cq.Vector:
    a = cq.Vector(1, 0, 0) if abs(v.x) < 0.9 else cq.Vector(0, 1, 0)
    return v.cross(a).normalized()


def convert(shape: cq.Shape, part_id: str) -> tuple[cq.Shape, list[tuple[float, float]]]:
    rules = _rules(part_id)
    changes = []
    tubes = []
    for dia, foot, dv, v0, v1 in holes(shape):
        new = next((nd for od, nd in rules.items() if abs(dia - od) <= TOL), None)
        if new is None:
            continue
        tubes.append(_tube(dia + 0.002, new, foot, dv, v0, v1))
        changes.append((dia, new))
    if not tubes:
        return shape, changes
    out = shape
    for t in tubes:
        out = out.fuse(t, tol=1e-4)
    out = out.clean()
    solids = out.Solids()
    if len(solids) == 1:
        out = solids[0]
    return out, changes


def convert_file(src: Path, dst: Path, part_id: str) -> list[tuple[float, float]]:
    shape = cq.importers.importStep(str(src)).val()
    out, changes = convert(shape, part_id)
    dst.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(out, str(dst), exportType="STEP")
    return changes
