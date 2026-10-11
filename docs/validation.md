# Validation

"It moved once" is not validation. This page defines the evidence levels used throughout the
repository, the acceptance gate for each build phase, and the run log that records the evidence.
Current status: [`validation/status.yaml`](../validation/status.yaml). Procedures:
[`validation/TEST_PROCEDURES.md`](../validation/TEST_PROCEDURES.md). Gates in one table:
[`validation/ACCEPTANCE_CRITERIA.md`](../validation/ACCEPTANCE_CRITERIA.md).

## Evidence levels

| level | means | does **not** mean |
|---|---|---|
| SOURCE-SUPPORTED | stated in a cited source (paper, datasheet) | that our reproduction matches it |
| ENGINEERING ASSUMPTION | a reasoned choice or starting value | that it is correct |
| RECONSTRUCTED REFERENCE | modelled to be consistent with sources where they are silent | that it matches the original |
| CAD-VALIDATED | geometry checked by software (watertight, volume, interference) | that it prints, fits or works |
| SOFTWARE-TESTED | code builds for its target and passes automated tests on a PC, simulator or synthetic data | that it works on the real machine or real material |
| PHYSICALLY TESTED | measured on built hardware, with logged data | that the process or product works |
| BIOLOGICALLY VALIDATED | germination / burial / survival measured in controlled trials | field performance |
| FLIGHT-VALIDATED | flown and released under permission with logged results | safety certification |

SOFTWARE-TESTED is not one of the physical evidence levels; it is listed so software status is not
mislabelled as an assumption. Rules: never imply one level means another ("STL is watertight" is not "mechanism works"; "the
reference CAD matches stated dimensions" is not "a plastic print behaves like wood"; "a drone
payload model exists" is not "the aircraft is flight safe"). A status only rises with recorded
data. The CAD manifest keeps separate columns for *CAD valid*, *print successful*, *physically
fits*, *mechanism works* and *process validated*.

Firmware status phrases: **Compile-tested; hardware testing pending** (built for the target and
unit-tested on a PC) and **Not yet physically validated**. Purchased-part dimensions that drive CAD
are marked **Measure before final fabrication**.

## Phase gates

### Phase 0 material

Measure per material lot: wet width, wet thickness, dry width, dry thickness, **damage tension**
(first visible cracking, splitting or permanent set) and **break tension**, and dry geometry of a
hand-wound reference coil. Output: a recipe card with the tension band (`SET_TENSION_MIN/MAX`) set
well below the damage tension. Chemical preparation stays a separate, approved lab procedure.

### Phase 1 winder

* >= 20 **consecutive** commanded winding cycles on real material without a mechanical jam.
* Exact commanded turn count on every coil (`COMPLETE` line, camera and manual count agree).
* No `SKIPPED_STEPS`; home error within 0.3 mm.
* Tension stays inside the Phase-0 band; trips are logged and explained.
* The camera (or a documented manual check) stops a deliberately bad coil.
* Recorded per cycle: turn count, pitch, tension mean/max, result, visual QA.

### Phase 2 cut / demold

* 20/20 successful clamp + cut + release cycles.
* Wet coil leaves the mandrel without dragging across an undercut, delaminating or uncoiling.
* Cutter guard and E-stop tested every session.

### Phase 3 tails

Dried tail shape repeatability (angle, length, curvature) within a tolerance that still seats in the
assembly nest, measured on >= 20 tails.

### Phase 4 drying

Temperature, humidity and duration logged; dried geometry measured; no fixture-induced deformation.

### Phase 5 final assembly

Exactly one seed, exactly three tails, no adhesive on active coils, intact tip, survives a defined
handling test; seed viability checked against untreated controls before any biological claim.

### Phase 6 vision

A labelled set of real images, split by material lot. Report true accepts, true rejects, false
accepts and false rejects on the held-out test split. Start target: zero false accepts on gaps and
overlaps over at least 100 test images; false rejects below 10 %.

### Phase 7 transfer

>= 50 consecutive transfers without a drop or collision.

### Phase 8 deployment

Only after manufacturing works. Bench release tests of the cassette, mass / centre-of-gravity /
thrust-margin analysis for a proven aircraft, written landowner and ecological permission, and
aviation compliance. Never automatic retries at uncertain drop points
([drone-concept.md](drone-concept.md)).

## Current status (v0.3.0-alpha)

| item | level | evidence |
|---|---|---|
| carrier reference dimensions | SOURCE-SUPPORTED (body, tail lengths) / RECONSTRUCTED (tail and tip shape) | [carrier-geometry.md](carrier-geometry.md) |
| geometry model | ENGINEERING ASSUMPTION, unit-tested | `tests/geometry` |
| 71 machine parts | CAD-VALIDATED (69 single-body; S01, T03 need repair) | [QA report](../hardware/cad/QA_REPORT.md) |
| core-cell layout | CAD-VALIDATED: no static interference; traverse sweep windows | `hardware/cad/source/core_cell_layout.json` |
| Uno firmware | SOFTWARE-TESTED (Compile-tested; hardware testing pending) | arduino-cli build + `tests/firmware` |
| ESP32 bridge | SOFTWARE-TESTED (Compile-tested; hardware testing pending) | arduino-cli build |
| simulator | SOFTWARE-TESTED: logic only; parity with the C++ core tested | `tests/host/test_sim_parity.py` |
| vision | SOFTWARE-TESTED on a synthetic set: 6 TA / 10 TR / 0 FA / 0 FR | `datasets/synthetic_reference/report.md` |
| Phases 0-8 | **Not yet physically validated** | - |

## Run logging

Every carrier gets an ID (`SFC-<UTC timestamp>-<6 hex>`; each run a `RUN-...` ID). The host writes two CSV files per session
(`python -m seedforge.host ... --log runs/`, also the simulator's `--log`):

**carriers.csv** - one row per carrier:

`timestamp, carrier_id, run_id, data_source, material_lot, width_mm, thickness_mm,
mandrel_diameter_mm, guide_angle_deg, pitch_mm, active_turns, sacrificial_turns, tension_target_N,
tension_mean_N, tension_max_N, vibration_rms_mg, winding_rate_rpm, turn_count, lin_steps,
camera_result, measured_length_mm, demold_result, tail_form_recipe, drying_duration_h,
final_result, fault, notes`

`data_source` is `machine` for real hardware and `SIMULATION ...` for simulated runs, so simulated
rows can never be mistaken for evidence.

**trace.csv** - time series during a cycle (same columns as
[`validation/RUN_LOG_TEMPLATE.csv`](../validation/RUN_LOG_TEMPLATE.csv)):

`timestamp, run_id, state, rot_steps, lin_steps, tension_N, dancer_raw, vibration_rms,
vision_event, limit_home, limit_end, estop_ok, result, notes`

The host fills the columns it can derive from controller messages (state, turns, tension,
`HOME_ERROR_MM`, positions, events, faults) and keeps each raw line in `notes`; `dancer_raw` and
`vibration_rms` come from `STATUS` lines (`dancer=`, `vib_mg=`) when you request them.

CSV first; the field names are stable so an SQLite store can be added later.
