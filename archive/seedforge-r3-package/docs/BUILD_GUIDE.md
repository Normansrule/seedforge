# SeedForge R1-LC — Low-Cost Modular Automated Seed-Carrier System

This revision is deliberately simpler than R0. It uses the sponsored/owned Arduino Uno, two NEMA17 motors, two A4988 drivers, RealSense camera, ICM-20948, ILI9341 and ultrasonic sensor. New hardware is limited to inexpensive motion hardware, a $5–$8 ESP32 bridge, a load cell, a few servos, two tiny geared steppers, USB-C power conversion, and an optional donor-style XY transfer gantry.

**Files delivered:** 55 unique printable designs in STL, STEP and geometry-only 3MF; a parametric CadQuery generator; BOM; point-to-point wiring table; pin map; print manifest; and actual-CAD preview images.

## 1. System architecture

Build the system as independent modules on a single 800 x 350 mm plywood bench. Each station has a 160 x 120 mm footprint. The cheapest build mounts directly to plywood. `C01_module_base_160x120` is optional if you want removable station tiles.

Process:

`M1 FEED -> M2 WIND -> M3 CLAMP/CUT -> M4 DEMOLD/TAIL FORM -> M6 FREE DRY -> M5 SEED/TIP + TAIL ASSEMBLY -> M6 VISION QA -> M7 OUTPUT -> DRONE CASSETTE`

The transfer gantry M8 is optional for the first prototype and required for hands-off movement between stations. To reduce cost, use a donor Ender-style XY carriage or build it from two 2020 extrusions, two NEMA17 motors and GT2 belt hardware.

## 2. Module-by-module build

### M1 — Veneer feed and tension
Print `F01–F07`. Use a 5 mm axle, 608 bearings, felt washers and a spring-loaded dancer. Route the conditioned 4 x 0.5 mm strip through the dancer and then the 4.6 x 1.2 mm guide. Mount the guide on slots so **45 degrees is a calibration setting, not a hard-coded plastic angle**. The load cell is the primary tension measurement; the dancer only buffers feed disturbances.

### M2 — Synchronized body winder
Print `W01–W08`. The rotational NEMA17 drives a purchased small collet/pin chuck holding a polished 0.8 mm steel mandrel. The linear NEMA17 drives a T8x8 lead screw. `W03` rides on four LM8UU bearings over two 8 mm guide rods. `W07/W08` are a split, silicone-lined demold collar: close gently on the wet coil/handling area and retract the steel mandrel.

**Synchronization:** with 200-step motors and 1/16 microstepping, rotation = 3200 microsteps/rev. A T8x8 axis is 400 microsteps/mm. If desired axial pitch is `p` mm/rev, linear steps per revolution are `400 p`; use a DDA/Bresenham accumulator against 3200 rotation microsteps instead of blocking delays.

For a helix angle `alpha` measured to the mandrel axis, a first-order model gives `p = pi(D+t)/tan(alpha)`. With D=0.8 mm, t=0.5 mm and alpha=45 degrees, p≈4.084 mm/rev. However a 4 mm strip under those same nominal dimensions is not automatically gap-free: the geometry predicts overlap. Therefore **do not lock the final recipe until you measure the wet formed diameter and actual edge contact**.

### M3 — Clamp and cut
Print `X01–X04`. Clamp an inactive/sacrificial region with silicone-padded jaws, then actuate a purchased spring-return micro shear after eight turns. The blade is never printed. Keep the guard installed for every automatic test.

### M4 — Tail forming
Print `T01–T04`. The split former has a 14 mm starting radius and 4.8 mm strip channel. A micro servo moves `T03` around the wet strip. Open the two former halves before removing the wet tail. Produce three tails separately for the cheapest body-first prototype. If later biological testing proves that one tail must remain continuous with the body blank, replace M1's continuous-strip feed with a pre-cut blank feeder while keeping the rest of the station architecture.

### M5 — Seed singulation, tip forming, adhesive and final assembly
Print `S01–S08`. `S01` gravity-feeds seed to the species-specific `S02` indexing disk; a 28BYJ-48 indexes one pocket at a time. `S04` holds three tails 120 degrees apart. `S07/S08` are **mold masters**; use them to make a compliant/non-stick working insert rather than assuming bare printed plastic is biologically or chemically suitable. `S05/S06` form a low-cost syringe pump with a second 28BYJ-48 and M5 threaded rod. Validate adhesive and tip material with the actual seed species.

### M6 — Free drying and vision QA
Print `Q01–Q03`. Wet wood should dry unrestrained on `Q01` with gentle room-temperature air from a USB fan. Do not heat the live seed. After assembly, use the existing RealSense or a macro USB camera through `Q03` with fixed illumination. Inspect turn count, overall length, large gap/overlap, tail presence, tip presence and gross defects.

### M7 — Output
Print `O01`. Twelve isolated pockets keep finished carriers from tangling before cassette loading. Pocket diameter is intentionally generous and must be regenerated after measuring the real dry carrier envelope.

### M8 — Automated transfer
Print `R01–R08`. Use a low-cost XY gantry to move fixtures or grip only an inactive handling tab. Do not grip the active coil. A micro-servo Z lift provides about 15–20 mm of vertical pickup travel. This module is the main cost/complexity option: start manually, then add M8 after the individual manufacturing stations work.

### Drone payload
Print `D01–D06`; buy the airframe. `D01` has four independent cells so long tails cannot entangle. Each `D02` door has its own servo and must be mechanically fail-closed. `D04` is only a payload adapter; it is **not** a flight structural member or motor arm. Start with a conventional 450-class quad and ArduPilot-capable flight controller.

The cheapest useful swarm architecture is centrally coordinated rather than full peer-to-peer AI: the ground planner divides the restoration zone into non-overlapping polygons; each drone receives a unique sector and unique planting-point IDs. The Pi runs local terrain/landing-site rejection and reports completed point IDs. If communications are lost, a drone stays inside its preassigned sector, which prevents two aircraft from independently replanning into the same area.

## 3. Controls philosophy

Use the Uno for deterministic motor pulses, tension sensing, limits and the finite-state machine. Use the ESP32-C3 only as a communications bridge. The camera host should transmit compact events such as `VISION_OK`, `FAULT_GAP`, `FAULT_OVERLAP`, `LENGTH_MM`, and `HEARTBEAT`; do not stream camera frames through the Uno.

A good control split is:

- **Inner motion synchronization:** DDA/Bresenham step scheduling between rotation and translation.
- **Tension loop:** load-cell PI/PID slowly trims overall winding speed or dancer setpoint.
- **Vibration supervisor:** calculate IMU RMS acceleration over a moving window and derate speed if vibration exceeds a calibrated threshold. Do not use IMU acceleration as the primary PID process variable because vibration is not the same quantity as strip tension or coil spacing.
- **Vision interrupt:** a sustained defect detection changes the FSM to `SAFE_STOP` and disables A4988 outputs after controlled deceleration.

Suggested top-level FSM:

`BOOT -> HOME -> READY -> PRETENSION -> WIND -> VISION_VERIFY -> CLAMP -> CUT -> DEMOLD -> TRANSFER -> TAIL_FORM / DRY_BUFFER -> ASSEMBLE -> FINAL_QA -> STORE -> READY`

Any hard limit, E-stop, camera fault, communication timeout or tension excursion goes to `SAFE_STOP`. Recovery requires the physical condition to clear and a deliberate RESET.

## 4. USB-C power architecture

One 65 W USB-C PD brick is the low-cost bench source. A PD trigger requests 20 V; a buck generates 12 V for the NEMA/A4988 rail; a second buck makes a separate 5 V servo/auxiliary rail. The Uno and ESP32 remain USB powered during development. All signal grounds meet at one star point. The E-stop interrupts actuator power, not merely software.

Do **not** connect 20 V directly to Arduino USB/5V, ESP32 USB/5V, A4988 VDD or servos. Put a bulk capacitor at each A4988 VMOT input and set driver current before coupling the motors to the mechanism.

See `wiring/connection_table.csv` for the point-to-point schedule and `wiring/pin_map.csv` for the proposed controller pin allocation.

## 5. Print strategy for Bambu A1 / A1 mini

All delivered parts fit inside a 180 x 180 x 180 mm bounding box. Start with `Z01_fit_calibration_coupon`.

Recommended baseline:

- PETG for wet-contact/mechanical parts; PLA is acceptable for dry electronics-only covers.
- 0.20 mm layer height for structural parts; 0.12–0.16 mm for F06/F07, W05/W07/W08 and S02.
- 3 wall loops and 4 top/bottom layers.
- 15–20% infill for housings/bases; 35–50% for motor brackets; 100% for very small jaws/couplers where slicer infill would be meaningless.
- Use silicone/PTFE liners rather than expecting printed PETG to be the final low-friction material interface.
- Do not print the 0.8 mm mandrel, cutting blade, drone arms, propellers, motor shafts or safety interlock hardware.

For the **lowest filament cost**, skip the seven large C01 tiles and screw modules directly to plywood. Use the C01 STEP as a drilling reference.

## 6. Cost target

Using the hardware already listed as owned/sponsored, the target purchased factory bill in this BOM is approximately **$370 without the optional automated transfer gantry** and **$452 with the low-cost transfer gantry**, before tax/shipping and excluding the actual veneer/seed/validated chemistry. The drone hardware target is approximately **$450** if nothing in the aircraft stack is already owned.

These are planning values, not live quotations. Reusing a donor 3D printer gantry and an existing RC transmitter/charger can remove roughly $100+ from the combined prototype.

## 7. Build order — do not print everything first

1. Print Z01, F06/F07, W01–W05 and X01/X02. Build only the core winder.
2. Characterize tension-to-break on wet veneer and establish a safe setpoint window.
3. Calibrate rotational/linear ratio and prove eight repeatable turns.
4. Add camera + fixed lighting and validate defect detection against hand-labelled samples.
5. Add X03/X04 and automated cut.
6. Add W07/W08 and prove reliable demolding without deforming the body.
7. Build M4 tails and M6 free-dry trays; validate recovered geometry.
8. Build M5 seed/tip assembly and verify seed viability after all materials/processes.
9. Add M8 transfer automation only after every station works independently.
10. Build D01–D06 on a bench and perform repeated gate-release tests before mounting to an aircraft.
11. Only then do tethered/contained flight testing, mass/CG checks and field validation under applicable rules/permissions.

## 8. What is still experimental

The actual tension window, wet-material bending radius, demold force, seed-tip chemistry, adhesive dose, final 45-degree/gap-free geometry, camera thresholds, and aircraft drop accuracy are physical experimental quantities. The CAD intentionally makes these interfaces adjustable instead of inventing values.
