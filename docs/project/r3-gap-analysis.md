# R3 gap and inconsistency analysis

This is the engineering record of what was found when the supplied
`SeedForge_R3_RealWorld_COMPLETE.zip` was inspected (file list:
[r3-inventory.md](r3-inventory.md)), and what this repository (release
**v0.3.0-alpha**, internal revision **R3.1**) did about each item.

Status words follow [docs/validation.md](../validation.md#evidence-levels): nothing
below has been **physically tested**.

## 1. CAD geometry

| # | Finding | Evidence | Resolution in R3.1 |
|---|---|---|---|
| G1 | Rotation-axis heights disagree. W01 puts the NEMA17 shaft at **37.0 mm** above its mounting face, W02's 608 bore is at **25.0 mm**, W05's mandrel bore at **26.0 mm**. Bolted to one flat base the mandrel would be 11-12 mm out of line. | cylinder axes extracted from the STEP files | One datum (37.0 mm, from W01). New **W13** 11.0 mm riser for W05. W02 marked *optional* (needs a 12 mm riser) because the R3.1 rotation train mounts a mini chuck directly on the motor shaft. |
| G2 | **W03 "LM8UU linear carriage" has no LM8UU bores.** Its note says "two 15.4 mm bores 56 mm apart"; the solid is a plate and block. | no cylindrical faces near 15 mm in the STEP | New **W11** carriage: two 15.2 mm LM8UU bores 56 mm apart, T8 flange-nut mount (4 x M3 on 16 mm PCD) integrated. W03 and W04 marked *superseded*. |
| G3 | The linear axis has **no motor mount, no rod supports and no screw-end bearing** anywhere in the 55 parts. | part list | New **W09** (NEMA17 face + rod sockets) and **W10** (rod sockets + 608ZZ pocket). |
| G4 | **F01 has no bearing bore**; its partner F02 has a 22.2 mm bore at z = 65 mm. | STEP features | **F09** = F01 with the pocket added (derived from the R3 STEP). |
| G5 | Spool stands take **608 bearings (8 mm bore)** but the F03 hubs are bored **5.2 mm** for a "5 mm axle". These parts cannot be assembled. | STEP features + R1 build guide | **F10** = F03 re-bored to 8.2 mm; BOM specifies an 8 mm axle. |
| G6 | No **load-cell mount**, although the load cell is "the primary process sensor". | part list | New **F08** pedestal for a 1 kg bar cell with the sensing roller on its free end. |
| G7 | No **dancer pivot**: F04's 6.3 mm hole fits a 6 mm potentiometer shaft but nothing holds the pot. | STEP features | New **F11** pivot post (pot bushing = pivot, A0 reads the angle). |
| G8 | No **limit-switch mounts**. | part list | New **W14** rod clamp for KW12-type microswitches (home and end). |
| G9 | W07/W08 split support pocket axis is at 17 mm (vs 37 mm) and only 7 mm long; its mounting on the machine is undefined. | STEP features | Marked *experimental*. Demold sequence implemented in firmware; Phase-2 mounting is an open design item ([M3](../modules/M3-clamp-cut-demold.md)). |
| G10 | S01 seed hopper and T03 sweep shoe are each **two disconnected bodies** (T03's servo tab is 2 mm away from its arc). | mesh connectivity check | Marked *needs repair*; both belong to later modules (M6, M4). |
| G11 | The mandrel **retraction** mechanism needed for demolding is not defined. | docs vs CAD | Documented concept: relative axial retraction by the traverse axis with a removable W05 support; first validated manually (Phase 2). |
| G12 | A 28 mm-wide F06 guide rotated about the contact point hits the mandrel beyond about +-30 deg if it sits close to it. | interference sweep | Guide exit stands 27 mm off the contact point; W12 arc slots give +-60 deg about the contact point. |
| G13 | Machine-part **generator source missing**. The R1 build guide says a parametric CadQuery generator was delivered; only the paper-reference generator is in the package. | file inventory | STEP files declared the source of truth for R3 parts. New parts have Python source. |
| G14 | Paper-reference generator was **out of sync** with its outputs: hard-coded `/mnt/data` paths, no MR07, and it generated PR24 at 4x while the shipped file is 3x. | source vs files | Refactored `paper_reference.py` reproduces all 24 shipped models (volume within 0.54 %, bbox within 0.025 mm). |
| G15 | `QA_reference_models.txt` reports **every** reference STL as not watertight. That came from loading meshes without vertex merging; 22 of 24 are watertight (PR22, PR23 are not). | re-check with trimesh | QA rewritten (`tools/build_cad.py`, `hardware/cad/QA_REPORT.md`). |

## 2. Carrier geometry

| # | Finding | Resolution |
|---|---|---|
| C1 | The **course target is internally inconsistent**. A 4.0 x 0.5 mm strip on a 0.8 mm mandrel at 45 deg gives a 4.084 mm/rev pitch; the first-order helix model then predicts **1.11 mm of overlap** (28 % of the strip width), not "no gap / no overlap". A butt joint needs a 19.8 mm/rev pitch (strip almost parallel to the axis), which makes a 7-turn body about 158 mm long. The strip is also about as wide as the centre-line circumference (4.08 mm), so it cannot lie flat. | Both geometries kept separate ([carrier-geometry.md](../carrier-geometry.md)); angle, pitch, tension, rate, acceleration and turns are recipe variables; `seedforge.recipe` warns about predicted overlap. |
| C2 | R3 firmware hard-coded pitch 4.084 mm/rev, i.e. pi x (0.8 + 0.5): exactly the overlapping 45 deg course case. | Kept as the `course_target_45deg` *commissioning* recipe, labelled inconsistent. |
| C3 | The paper-reference body (7 coils over 35 mm, 2.5 mm ribbon) has 5.0 mm pitch, which the model predicts leaves ~0.66 mm gaps; it needs a 50.8 deg guide angle. | Guide range widened to +-60 deg (G12). |
| C4 | A 0.8 mm steel mandrel is very compliant: about **0.8-1.9 mm** deflection at 0.5 N over a 90 mm span (fixed-pinned to pinned-pinned). | Documented; tension must stay low or the span short; measure deflection in Phase 1. |

## 3. Electronics and firmware

| # | Finding | Resolution |
|---|---|---|
| E1 | Two incompatible **pin maps**: R2 `wiring/pin_map.csv` (display on the Uno, HX711 on A0/A1, ESP32 on D0/D1) vs R3 core map (HX711 on D11/D12, link on A1/A2). | R3 core map adopted (it matches the brief); regenerated schedule in `hardware/wiring/`; R2 archived. |
| E2 | Three **module numberings** (R1 build guide, R3 module map, brief). | Brief numbering (M1-M10) everywhere; part-ID prefixes are the stable key ([manufacturing-process.md](../manufacturing-process.md)). |
| E3 | R3 controller generated steps from `loop()` with `micros()` polling while also transmitting on SoftwareSerial (which disables interrupts for ~0.5 ms per byte at 19200 baud): long status lines stall stepping. Linear steps were emitted in bursts when pitch > 8 mm/rev. | Timer1 ISR step generator; general Bresenham with the larger axis as master (never more than one slave step per tick); link at 38400 baud with low traffic while winding. |
| E4 | R3 controller: no homing, `PRETENSION` declared but unused, HX711 pins reserved but not read, no tension trip, heartbeat checked only while winding (not in `VERIFY`), no skipped-step evidence. | All implemented and unit-tested ([controls.md](../controls.md)). |
| E5 | The original EECS 149 sketch ignored `EMERGENCY_STOP` while paused (R3 noted this). | Fault and stop commands are honoured in every state; tested. |
| E6 | R3 E-stop description did not say that the switch needs a **DC-rated power contact** or how the controller learns it was pressed. | A24 specifies a DC-rated contact; the Uno senses the switched 12 V rail through a divider on D8 (no auxiliary contact needed; an auxiliary contact remains supported). |
| E7 | The fixed camera had an LED ring only; deterministic silhouette QA needs a **back-light**, and a back-light on the feed side would sit in the strip path. | Overhead camera on a mast with a back-light panel under the mandrel. |

## 4. Documentation and data

| # | Finding | Resolution |
|---|---|---|
| D1 | Cost summaries: R1 claims $370/$452; numbers were planning targets, not quotes. | Regenerated BOM views with explicit "estimate" labelling. |
| D2 | `START_HERE.md` mentions `SeedForge_R3_PHASE1_CORE_PRINTS.zip` "beside the package"; it was not in the upload (only `r3_quick_prints/`). | Release script builds the Phase-1 print pack. |
| D3 | The original course repository (`N0rmansrule/eecs149-group3-woodwinder`) is group coursework with no licence. | Archived under `archive/eecs149-original/` and **excluded** from the project licences. |

## 5. Budget and fastener revision (requested after the first draft)

The repository owner asked for **M2 screws only** and the **lowest practical cost** for the
manufacturing bench and the drone concept. Changes:

| # | Change | Why / consequence |
|---|---|---|
| B1 | All project fasteners are M2: R3 STEP originals kept in `hardware/cad/source/r3_step/`; `m2_fasteners.py` converts 3.4 mm clearance holes to 2.4 mm and 2.9 mm pilots to 1.8 mm on every build; R3.1 parts use M2 parameters. | One fastener kit. 3.4 mm adjustment slots stay (M2 + washer). M3 nut traps in R3 parts take an M2 nut + washer. |
| B2 | NEMA17 face holes are M3-threaded, so new W15/W16 split collars hold the motor bodies with M2 pinch screws; the face boss still registers on W01/W09. | Motors are clamped, not bolted. Torque here is small; check for slip in Phase 1. |
| B3 | The load cell's M4/M5 threads are not used: F08 channel + F13 cap clamp its fixed end; F12 yoke on the free end carries 2 x MR62ZZ on an M2 axle (replaces 623ZZ on M3). | Clamping changes where the cell is supported: calibrate in place, as before. |
| B4 | 2020 extrusion + RealSense replaced by a plywood mast (W17 foot) and a 38 x 38 mm USB board camera on the W18 arm (M2 holes). W06, Q03 superseded. | About $25 saved; lens choice now sets px/mm (about 6 mm M12 lens at about 50 mm). |
| B5 | 65 W USB-C PD supply + PD trigger + 20-12 V buck replaced by a certified 12 V 3 A adapter; LM2596 for the 5 V servo rail. | About $35 saved. Deviates from the brief's suggested USB-C PD concept; documented in electronics.md. |
| B6 | E-stop auxiliary contact replaced by rail sensing (divider on D8, `ESTOP_SENSE_RAIL`). | Cheaper single-contact E-stop; also detects a blown fuse or unplugged supply. |
| B7 | ESP32-C3, display and IMU made optional; generic parts priced throughout. | View A about $128 to buy if the Uno, motors and drivers are owned (R3.1 draft: $318). |
| B8 | Drone concept: payload kit (RP2040 + 4 SG90 + IR confirm sensors, about $18) separated from the aircraft; budget ArduPilot F405 quad; companion computer and camera optional; ELRS replaces the telemetry radio. | View C about $154 (R3.1 draft: $451). Not flight-validated. |

## 6. Still open (needs measurement or a design decision)

* Real wet-veneer width, thickness, damage and break tension (Phase 0).
* Purchased-part dimensions: mini chuck, load cell, T8 nut PCD, microswitch, pot bushing, camera board hole pattern.
* Whether the W15/W16 body clamps hold the motors without slipping (Phase 1).
* F06 channel position: inferred from its section, not documented in R3. **Measure before final fabrication.**
* M3 clamp/cut placement relative to the core cell and the demold actuation (Phase 2).
* Seed species (feeder pocket size), tip paste and adhesive (Phase 5).
