"""Shared CAD export helpers for SeedForge.

Every generated file is derived from editable source in this directory or
from the STEP files under ``hardware/cad/step``.  Tessellation tolerances are
fixed constants so that regenerated meshes are reproducible for a given
CadQuery/OCCT version.

Units: millimetres everywhere.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Iterable, Sequence

import cadquery as cq
import numpy as np
import trimesh

CAD_ROOT = Path(__file__).resolve().parents[1]          # hardware/cad
REPO_ROOT = CAD_ROOT.parents[1]

# Fixed tessellation settings (do not change without regenerating every mesh).
STL_TOL = 0.06          # mm linear deflection for printable/reference STL
STL_ANG = 0.15          # rad angular deflection
GLB_TOL = 0.12          # coarser mesh for web viewers
GLB_ANG = 0.3

# Engineering colour palette (RGBA 0-255) used consistently in renders/GLB.
PALETTE = {
    "printed": (233, 236, 239, 255),      # light grey PETG
    "printed_accent": (47, 111, 79, 255),  # forest green (new R3.1 parts)
    "metal": (168, 174, 181, 255),
    "dark_metal": (72, 78, 86, 255),
    "motor": (52, 58, 66, 255),
    "wood": (184, 134, 78, 255),
    "wood_light": (205, 154, 87, 255),
    "wood_dark": (166, 112, 62, 255),
    "tip": (208, 180, 124, 255),
    "seed": (100, 63, 40, 255),
    "silicone": (214, 92, 72, 255),
    "base": (222, 205, 170, 255),          # plywood
    "pcb": (38, 92, 70, 255),
    "guard": (180, 210, 230, 140),
    "envelope": (120, 100, 80, 70),
}


def to_shape(obj) -> cq.Shape:
    """Return a single OCC shape from a Workplane / Shape / Assembly part."""
    if isinstance(obj, cq.Workplane):
        vals = [v for v in obj.vals() if isinstance(v, cq.Shape)]
        if len(vals) == 1:
            return vals[0]
        return cq.Compound.makeCompound(vals)
    return obj


def shape_to_trimesh(shape, tol: float = STL_TOL, ang: float = STL_ANG) -> trimesh.Trimesh:
    shape = to_shape(shape)
    verts, tris = shape.tessellate(tol, ang)
    v = np.array([(p.x, p.y, p.z) for p in verts], dtype=np.float64)
    f = np.array(tris, dtype=np.int64)
    mesh = trimesh.Trimesh(vertices=v, faces=f, process=True)
    mesh.fix_normals()
    return mesh


def write_step(shape, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(to_shape(shape), str(path), exportType="STEP")


def write_stl(mesh: trimesh.Trimesh, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(mesh.export(file_type="stl"))


def write_3mf(meshes: dict[str, trimesh.Trimesh], path: Path) -> None:
    """Geometry-only 3MF (one object per named mesh), deterministic zip."""
    path.parent.mkdir(parents=True, exist_ok=True)
    scene = trimesh.Scene()
    for name, m in meshes.items():
        scene.add_geometry(m, node_name=name, geom_name=name)
    raw = scene.export(file_type="3mf")
    # Re-pack with fixed timestamps so the archive is byte-stable.
    src = zipfile.ZipFile(io.BytesIO(raw))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in sorted(src.infolist(), key=lambda i: i.filename):
            zi = zipfile.ZipInfo(info.filename, date_time=(2026, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            dst.writestr(zi, src.read(info.filename))
    path.write_bytes(out.getvalue())


def colored(mesh: trimesh.Trimesh, rgba: Sequence[int]) -> trimesh.Trimesh:
    m = mesh.copy()
    color = np.array(rgba, dtype=np.float64) / 255.0
    m.visual = trimesh.visual.TextureVisuals(
        material=trimesh.visual.material.PBRMaterial(
            baseColorFactor=color,
            metallicFactor=0.55 if rgba in (PALETTE["metal"], PALETTE["dark_metal"]) else 0.05,
            roughnessFactor=0.45 if rgba in (PALETTE["metal"], PALETTE["dark_metal"]) else 0.75,
            alphaMode="BLEND" if rgba[3] < 255 else "OPAQUE",
            doubleSided=rgba[3] < 255,
        )
    )
    return m


def write_glb(parts: Iterable[tuple[str, object, Sequence[int]]], path: Path,
              tol: float = GLB_TOL, ang: float = GLB_ANG, extras: dict | None = None) -> None:
    """Write a GLB scene.  ``parts`` = (node name, cq shape | trimesh, rgba).

    Node names are kept so the web viewer can show/hide and label components.
    Coordinates stay in millimetres (the viewer scales them).
    """
    scene = trimesh.Scene()
    for name, obj, rgba in parts:
        mesh = obj if isinstance(obj, trimesh.Trimesh) else shape_to_trimesh(obj, tol, ang)
        scene.add_geometry(colored(mesh, rgba), node_name=name, geom_name=name)
    if extras:
        scene.metadata.update(extras)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(scene.export(file_type="glb"))


def export_part(shape, stem: str, family: str, write_step_file: bool = True) -> trimesh.Trimesh:
    """Export STEP (optional), STL and 3MF for one printable/reference part.

    ``family`` is ``machine`` or ``reference``.
    """
    if write_step_file:
        write_step(shape, CAD_ROOT / "step" / family / f"{stem}.step")
    mesh = shape_to_trimesh(shape)
    write_stl(mesh, CAD_ROOT / "stl" / family / f"{stem}.stl")
    write_3mf({stem: mesh}, CAD_ROOT / "3mf" / family / f"{stem}.3mf")
    return mesh


def load_step(path: Path) -> cq.Shape:
    return cq.importers.importStep(str(path)).val()
