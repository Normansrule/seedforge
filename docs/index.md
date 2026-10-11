# SeedForge documentation

**Start here:** [getting-started.md](getting-started.md) answers the seventeen questions a new
builder asks, from "what am I building?" to "when may I build Phase 2?".

## Understand

| page | what it covers |
|---|---|
| [system-overview.md](system-overview.md) | layout, control layers, one cycle, software map |
| [manufacturing-process.md](manufacturing-process.md) | the ten modules, build order and phase gates |
| [carrier-geometry.md](carrier-geometry.md) | helix model, course target vs paper reference, mandrel stiffness |
| [modules/](modules/README.md) | M1-M10, one page each (purpose, parts, electronics, software, calibration, acceptance, risks) |

## Build

| page | what it covers |
|---|---|
| [getting-started.md](getting-started.md) | buy, print, assemble, wire, flash, home, calibrate, first runs |
| [../hardware/cad/README.md](../hardware/cad/README.md) | CAD sources of truth, units, printer settings, tolerances, part numbering |
| [../hardware/bom/BOM.md](../hardware/bom/BOM.md) | three BOM views and printed parts |
| [electronics.md](electronics.md) | schematic, power tree, pin map, connector policy, safety circuit |
| [../hardware/wiring/WIRING.md](../hardware/wiring/WIRING.md) | generated pin map and point-to-point table |
| [calibration.md](calibration.md) | fourteen calibrations with methods and pass criteria |

## Operate and develop

| page | what it covers |
|---|---|
| [controls.md](controls.md) | step generation, state machine, safety stops, recipe variables |
| [protocol.md](protocol.md) | serial/BLE/TCP line protocol |
| [computer-vision.md](computer-vision.md) | deterministic silhouette QA |
| [simulator.md](simulator.md) | hardware-free simulation and scenario files |
| [../firmware/README.md](../firmware/README.md), [../software/README.md](../software/README.md) | building firmware and the Python package |

## Trust

| page | what it covers |
|---|---|
| [validation.md](validation.md) | evidence levels, phase gates, current status, run logging |
| [safety.md](safety.md) | hazards, chemical and ecological boundaries, aviation |
| [drone-concept.md](drone-concept.md) | optional downstream deployment architecture (concept) |
| [references.md](references.md) | the Nature paper, algorithms, datasheets, tools |
| [project/r3-gap-analysis.md](project/r3-gap-analysis.md) | what was wrong in R3 and what R3.1 changed |
| [project/r3-inventory.md](project/r3-inventory.md) | every file of the supplied package and where it went |
| [project/implementation-plan.md](project/implementation-plan.md) | how this repository was built and what remains |
| [project/licensing.md](project/licensing.md) | why three licences |
| [project/large-files.md](project/large-files.md) | repository size and the no-LFS decision |

## Figures

* Renders: [images/](images/) (CAD renders, not photographs)
* Diagrams A-I: [diagrams/](diagrams/) (Mermaid sources in [diagrams/src/](diagrams/src/))
* Animations: [animations/](animations/) and the [interactive site](https://normansrule.github.io/seedforge/)
