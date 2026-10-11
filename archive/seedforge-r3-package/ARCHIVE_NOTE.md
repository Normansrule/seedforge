# SeedForge R3 RealWorld package (archived input)

The supplied `SeedForge_R3_RealWorld_COMPLETE.zip`, minus the CAD meshes (see below), unchanged.
Every one of its 316 files is listed with its disposition in
[docs/project/r3-inventory.md](../../docs/project/r3-inventory.md); problems found are in
[docs/project/r3-gap-analysis.md](../../docs/project/r3-gap-analysis.md).

| folder | content | current replacement |
|---|---|---|
| `START_HERE.md`, `r3_docs/`, `docs/` | R1-R3 build guides, module map, checklists, summary | `docs/` |
| `bom/` | R1/R2/R3 BOMs and cost summaries | `hardware/bom/` (regenerated, estimates labelled) |
| `wiring/` | R2 pin map and connection table (different pin map) | `hardware/wiring/` |
| `software/` | R3 controller sketch | `firmware/arduino/seedforge_core` |
| `cad/` | manifests, parameters, original paper-reference generator | `hardware/cad/` (STEP kept there as source of truth; meshes regenerated) |
| `previews/` | R3 preview images | `docs/images/` (new CAD renders) |
| `r3_validation/` | calibration worksheet and run-log template | `validation/` (expanded) |

Not covered by the repository licences.
