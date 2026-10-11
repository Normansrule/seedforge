# Implementation plan and record

How v0.3.0-alpha was produced from the supplied R3 package, and what remains. Steps are listed in
the order executed; each links to its output.

## 1. Inspect and inventory

* Unpacked `SeedForge_R3_RealWorld_COMPLETE.zip` (316 files) and the original EECS 149 code.
* Inventory with a disposition for each file: [r3-inventory.md](r3-inventory.md).
* Read all Markdown, BOMs, wiring tables, both firmware generations; extracted feature geometry from
  every STEP file (bores, axes, bounding boxes) to check fits.

## 2. Gaps and inconsistencies

[r3-gap-analysis.md](r3-gap-analysis.md): 15 CAD findings (G1-G15), 4 geometry findings (C1-C4),
7 electronics/firmware findings (E1-E7), 3 documentation findings (D1-D3).

## 3. Decisions (documented assumptions, no blocking questions)

| decision | choice | where |
|---|---|---|
| licence | MIT / CERN-OHL-S-2.0 / CC BY-SA 4.0, archive excluded | [licensing.md](licensing.md) |
| module numbering | brief's M1-M10; prefixes stable | [manufacturing-process.md](../manufacturing-process.md) |
| pin map | R3 core map | [electronics.md](../electronics.md) |
| axis datum | 37.0 mm from W01, new W13 riser | gap G1 |
| first build target | M1 + M2 + overhead camera, then M3 | [getting-started.md](../getting-started.md) |
| carrier geometry | course target and paper reference kept separate; all angles/pitches are recipe variables | [carrier-geometry.md](../carrier-geometry.md) |
| versioning | v0.3.0-alpha (engineering revision R3.1) | [CHANGELOG](../../CHANGELOG.md) |
| large files | no Git LFS | [large-files.md](large-files.md) |
| repository owner | `Normansrule/seedforge` (the account that hosts the other project repositories; the course repository was under `N0rmansrule`) | README links |

## 4. Execution

| # | work | output | verification |
|---|---|---|---|
| 1 | reorganise, archive originals | `archive/` | inventory cross-check |
| 2 | reproducible CAD build, new R3.1 parts, layout + interference | `hardware/cad/`, `tools/build_cad.py` | QA report; 0 static interferences |
| 3 | renders and diagrams A-I | `docs/images/`, `docs/diagrams/` | visual review of every image |
| 4 | Uno firmware rewrite | `firmware/arduino/` | arduino-cli build; 22 host tests under ASan/UBSan |
| 5 | ESP32-C3 bridge | `firmware/esp32/` | arduino-cli build |
| 6 | Python package: geometry, protocol, recipes, simulator, host, vision, ledger | `software/seedforge/` | pytest; simulator/C++ parity |
| 7 | BOM views, wiring schedule, schematic, drilling template | `hardware/bom/`, `hardware/wiring/`, `hardware/electronics/`, `hardware/drawings/` | generated from one source each |
| 8 | documentation | `docs/`, root files | link check in CI |
| 9 | validation framework | `validation/` | templates checked against `runlog.py` |
| 10 | website | `website/` | `npm run build`; headless screenshots |
| 11 | CI, release packaging | `.github/`, `tools/make_release.py` | local dry run |

## 5. Remaining work (needs hardware or decisions)

1. **Build Phase 1** and fill in the calibration worksheet (all "Measure before final fabrication"
   items first).
2. Phase-0 material data -> real tension band; enable the tension speed trim only after that.
3. Real labelled images for the vision set; re-tune thresholds.
4. Phase-2 M3 mounting design relative to the core cell (W07/W08 axis height, X01-X04 placement).
5. Repair S01 and T03 geometry (two bodies each).
6. Vibration baseline -> derate/trip levels.
7. Machine-part generator source for the remaining R3 parts (currently STEP is the source).
8. Publish: create the GitHub repository, enable Pages, push the `v0.3.0-alpha` tag.
