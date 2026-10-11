#!/usr/bin/env python3
"""Build the release bundles into releases/dist/.

    python tools/make_release.py [--version v0.3.0-alpha]

Bundles:
  SeedForge_<v>_COMPLETE.zip            every tracked file (git ls-files; falls back to a filtered walk)
  SeedForge_<v>_PHASE1_PRINTS.zip       core-cell + fit coupon (+ M3 in phase2_M3/), 3MF/STL/STEP, print list
  SeedForge_<v>_SEED_REFERENCE_CAD.zip  MR/PR reference models + carrier GLBs + geometry notes
  SeedForge_<v>_DOCUMENTATION.zip       Markdown docs, figures, and website/dist if it has been built
  SHA256SUMS.txt
Zip entries use a fixed timestamp so rebuilding the same tree gives identical archives.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "releases" / "dist"
FIXED = (2026, 1, 1, 0, 0, 0)
EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache", "dist", "build", "synthetic", "runs", "img"}

PHASE1 = ["Z01", "W01", "W05", "W09", "W10", "W11", "W12", "W13", "W14", "W15", "W16", "W17", "W18",
          "F02", "F04", "F05", "F06", "F07", "F08", "F09", "F10", "F11", "F12", "F13", "C02", "C03", "C04"]
PHASE2 = ["X01", "X02", "X03", "X04"]


def version() -> str:
    sys.path.insert(0, str(ROOT / "software"))
    from seedforge import __version__  # 0.3.0a0
    v = __version__.replace("a0", "-alpha").replace("b0", "-beta")
    return "v" + v


def tracked_files() -> list[Path]:
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split("\n")
        files = [ROOT / f for f in out if f]
        if files:
            return [f for f in files if f.is_file()]
    except (OSError, subprocess.CalledProcessError):
        pass
    return [p for p in ROOT.rglob("*") if p.is_file() and not any(part in EXCLUDE_DIRS for part in p.relative_to(ROOT).parts)
            and "releases/dist" not in p.as_posix()]


def add(z: zipfile.ZipFile, src: Path, arc: str):
    info = zipfile.ZipInfo(arc, FIXED)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    z.writestr(info, src.read_bytes())


def write_zip(path: Path, entries: list[tuple[Path, str]], extra: dict[str, str] | None = None):
    with zipfile.ZipFile(path, "w") as z:
        for src, arc in sorted(entries, key=lambda e: e[1]):
            add(z, src, arc)
        for arc, text in (extra or {}).items():
            info = zipfile.ZipInfo(arc, FIXED)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, text)
    print(f"{path.name}: {len(entries) + len(extra or {})} files, {path.stat().st_size / 1e6:.1f} MB")


def manifest_rows() -> dict[str, dict]:
    rows = csv.DictReader((ROOT / "hardware" / "cad" / "manifest.csv").open())
    return {r["part_id"]: r for r in rows if r["family"] == "machine"}


def print_pack(v: str, top: str) -> tuple[list[tuple[Path, str]], dict[str, str]]:
    rows = manifest_rows()
    cad = ROOT / "hardware" / "cad"
    entries = []
    lines = ["part_id,file_stem,module,status,qty,material,bbox_x_mm,bbox_y_mm,bbox_z_mm,notes"]
    for group, ids in (("phase1_core_cell", PHASE1), ("phase2_M3", PHASE2)):
        for pid in ids:
            r = rows[pid]
            stem = r["file_stem"]
            for kind in ("3mf", "stl", "step"):
                f = cad / kind / "machine" / f"{stem}.{kind}"
                entries.append((f, f"{top}/{group}/{kind}/{f.name}"))
            note = r["notes"].replace('"', "'")
            lines.append(f'{pid},{stem},{r["module"]},{r["status"]},{r["qty"]},{r["material"]},{r["bbox_x_mm"]},'
                         f'{r["bbox_y_mm"]},{r["bbox_z_mm"]},"{note}"')
    readme = f"""SeedForge {v} - Phase-1 print pack

phase1_core_cell/  M1 feed + tension, M2 winder, M7 camera mount, common parts, Z01 fit coupon
phase2_M3/         M3 clamp + cut parts (build after the Phase-1 gate)

Print Z01 first and tune hole fit. Every fastener is M2 (2.4 mm clearance, 1.8 mm pilot). PETG, 0.4 mm nozzle, 0.16-0.20 mm layers, 4 walls for
W01/W09/W10/W11. Quantities and notes: PRINT_LIST.csv. Settings and tolerances:
hardware/cad/README.md in the repository. Superseded parts (F01, F03, W03, W04, W06, Q03) and the optional C05 bezel are not included.

Status: CAD-validated meshes. Not yet printed or physically fitted by the project.
Measure before final fabrication: chuck, T8 nut PCD, load cell, microswitch, pot bushing, camera board.
Licence: CERN-OHL-S-2.0.
"""
    drill = ROOT / "hardware" / "drawings" / "core_cell_drilling_template.svg"
    if drill.exists():
        entries.append((drill, f"{top}/core_cell_drilling_template.svg"))
    return entries, {f"{top}/PRINT_LIST.csv": "\n".join(lines) + "\n", f"{top}/README.txt": readme}


def reference_pack(v: str, top: str):
    cad = ROOT / "hardware" / "cad"
    entries = []
    for kind in ("step", "stl", "3mf"):
        for f in sorted((cad / kind / "reference").glob("*")):
            entries.append((f, f"{top}/{kind}/{f.name}"))
    for g in ("finished_carrier", "exploded_carrier", "mandrel_assembly", "mandrel_with_coil"):
        f = cad / "glb" / f"{g}.glb"
        if f.exists():
            entries.append((f, f"{top}/glb/{f.name}"))
    for f in (ROOT / "docs" / "carrier-geometry.md", cad / "source" / "paper_reference.py", cad / "source" / "paper_reference_parameters.json"):
        entries.append((f, f"{top}/{f.name}"))
    readme = f"""SeedForge {v} - seed-carrier reference CAD

MR = mandrel references, PR = paper-reference carrier models (Luo et al., Nature 614, 463-470, 2023).
Dimensions marked SOURCE-SUPPORTED come from the paper; tail and tip shapes are RECONSTRUCTED.
These models are for fixture design and clearance checks. A plastic print is not a functional
seed carrier. Not the authors' CAD. Licence: CERN-OHL-S-2.0. See carrier-geometry.md.
"""
    return entries, {f"{top}/README.txt": readme}


def docs_pack(top: str):
    entries = []
    for f in ["README.md", "LICENSE", "CITATION.cff", "CHANGELOG.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md",
              "DISCLAIMER.md"]:
        entries.append((ROOT / f, f"{top}/{f}"))
    for base in ("docs", "validation", "hardware/bom", "hardware/wiring", "hardware/electronics", "hardware/drawings"):
        for p in sorted((ROOT / base).rglob("*")):
            if p.is_file():
                entries.append((p, f"{top}/{p.relative_to(ROOT).as_posix()}"))
    entries.append((ROOT / "hardware" / "cad" / "README.md", f"{top}/hardware/cad/README.md"))
    entries.append((ROOT / "hardware" / "cad" / "QA_REPORT.md", f"{top}/hardware/cad/QA_REPORT.md"))
    site = ROOT / "website" / "dist"
    if site.exists():
        for p in sorted(site.rglob("*")):
            if p.is_file():
                entries.append((p, f"{top}/site/{p.relative_to(site).as_posix()}"))
    return entries


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=None)
    v = ap.parse_args().version or version()
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*"):
        old.unlink()
    name = f"SeedForge_{v}"
    files = [(p, f"{name}/{p.relative_to(ROOT).as_posix()}") for p in tracked_files()]
    write_zip(OUT / f"{name}_COMPLETE.zip", files)
    e, x = print_pack(v, f"{name}_PHASE1_PRINTS")
    write_zip(OUT / f"{name}_PHASE1_PRINTS.zip", e, x)
    e, x = reference_pack(v, f"{name}_SEED_REFERENCE_CAD")
    write_zip(OUT / f"{name}_SEED_REFERENCE_CAD.zip", e, x)
    write_zip(OUT / f"{name}_DOCUMENTATION.zip", docs_pack(f"{name}_DOCUMENTATION"))
    sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}" for p in sorted(OUT.glob("*.zip"))]
    (OUT / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n")
    print("\n".join(sums))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
