# Manufacturing process and module map

![process](diagrams/A_process_flow.svg)

```
PREPARED VENEER -> M1 FEED + TENSION -> M2 BODY WINDING -> M3 CLAMP + CUT + DEMOLD
 -> M4 AUXILIARY TAIL FORMING -> M5 FREE DRYING -> M6 SEED + TIP + 3-TAIL ASSEMBLY
 -> M7 COMPUTER-VISION QA -> M8 OUTPUT STORAGE -> M9 OPTIONAL XY TRANSFER -> M10 OPTIONAL DRONE CASSETTE
```

SeedForge is a **research-scale** platform. It is not an industrial production line, a
flight-certified payload, a chemically validated wood-processing system, a biologically validated
seed product or a safety-certified machine.

## Modules

Each module can be printed, installed, tested, controlled, replaced and calibrated on its own.
Click through for purpose, inputs, outputs, parts, electronics, software, calibration, acceptance
criteria, risks and figures.

| module | name | build phase | v0.3 status | printed parts | doc |
|---|---|---|---|---|---|
| M0 | Prepared veneer (lab process, not automated) | 0 | procedure only | - | [validation.md](validation.md#phase-0-material) |
| M1 | Feed + tension | 1 | designed, CAD-checked | F02, F04-F11 | [M1](modules/M1-feed-tension.md) |
| M2 | Synchronized winding | 1 | designed, CAD-checked, firmware unit-tested | W01, W05, W09-W14 | [M2](modules/M2-winding.md) |
| M3 | Clamp + cut + demold | 2 | sequence software-tested; mounting open | X01-X04, W07, W08 | [M3](modules/M3-clamp-cut-demold.md) |
| M4 | Auxiliary tail forming | 3 | experimental (R3 parts) | T01-T04 | [M4](modules/M4-tail-forming.md) |
| M5 | Free drying | 4 | experimental | Q01, Q02 | [M5](modules/M5-free-drying.md) |
| M6 | Seed + tip + three-tail assembly | 5 | experimental development tooling | S01-S08 | [M6](modules/M6-assembly.md) |
| M7 | Computer-vision QA | 1 / 6 | software tested on synthetic images | W06, Q03 | [M7](modules/M7-vision-qa.md) |
| M8 | Output storage | 5 | experimental | O01 | [M8](modules/M8-output.md) |
| M9 | XY transfer (optional) | 7 | upcoming | R01-R08 | [M9](modules/M9-xy-transfer.md) |
| M10 | Drone cassette (optional, downstream) | 8 | concept | D01-D06 | [M10](modules/M10-drone-cassette.md) |
| C / Z | Common parts, fit-calibration coupon | - | - | C01-C05, Z01 | [hardware/cad](../hardware/cad/README.md) |

### Numbering history

R1, R3 and the project brief numbered modules differently. Part-ID prefixes never changed, so
they are the stable key:

| prefix | R1 build guide | R3 module map | this repository |
|---|---|---|---|
| F | M1 feed | M1 | **M1** |
| W | M2 winder | M2 | **M2** (W07/W08 demold support -> **M3**, W06 camera -> **M7**) |
| X | M3 clamp/cut | M3 | **M3** |
| T | M4 demold/tail | M4 | **M4** |
| Q01, Q02 | M6 dry + QA | M6 | **M5** |
| S | M5 seed/tip/glue | M5 | **M6** |
| Q03 | M6 dry + QA | M7 | **M7** |
| O | M7 output | M8 | **M8** |
| R | M8 transfer | M9 | **M9** |
| D | drone payload | M10 | **M10** |

## Build order

Do not jump ahead. Each phase has an acceptance gate ([validation.md](validation.md)).

| phase | scope | gate |
|---|---|---|
| 0 | Material characterisation | recipe card from measured wet/dry dimensions and damage/break tension |
| 1 | M1 + M2 + fixed camera (core winding cell) | >= 20 consecutive commanded cycles; exact turns; no skipped steps; tension in band |
| 2 | M3 clamp, cutter, demold | 20/20 cut + release cycles without dragging or delamination |
| 3 | M4 tails | repeatable dried tail shape that seats in the nest |
| 4 | M5 free drying | environment and geometry logged; no fixture-induced deformation |
| 5 | M6 seed/tip assembly | one seed, three tails, no adhesive on active coils, intact tip, viability |
| 6 | M7 vision QA | labelled real-image set with true/false accept/reject counts |
| 7 | M9 transfer | >= 50 transfers without drop or collision |
| 8 | M10 deployment research | bench release tests, mass/CG/thrust margin, permissions |

## Process data

![data flow](diagrams/H_data_flow.svg)

Every carrier gets a carrier ID and a row in `carriers.csv`; every cycle writes a time series to
`trace.csv` ([validation.md](validation.md#run-logging)).
