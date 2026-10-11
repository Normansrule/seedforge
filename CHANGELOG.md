# Changelog

All notable changes. Versions follow semantic versioning with pre-release tags; engineering
revisions (R1, R2, R3, R3.1) are noted alongside. No version will be called 1.0 before physical
validation justifies it.

## [0.3.0-alpha] - 2026-10-11 (engineering revision R3.1)

First public repository release, built from the supplied *SeedForge R3 RealWorld* package and the
original EECS 149 wood-winder code. Nothing in this release has been physically tested.

### Added
* Reproducible CAD build (`python tools/build_cad.py`): STEP, STL, 3MF, GLB for 71 machine parts and
  24 paper-reference models, with an automated QA report and manifest.
* New R3.1 parts: W09-W14 (linear-axis end blocks, LM8UU carriage, angle-adjustable guide arm,
  W05 riser, limit-switch clamps) and F08-F11 (load-cell mount, bored spool stand, 8 mm spool hub,
  dancer pivot post).
* Core-cell layout with static and swept interference checks and collision-free carriage windows.
* Overhead camera with back-light for silhouette QA (finding E7).
* Arduino Uno firmware: Timer1 ISR step generation with Bresenham synchronisation, trapezoidal
  ramps, homing with skipped-step re-check, HX711 tension trip, E-stop feedback, heartbeat watchdog,
  state machine BOOT ... SAFE_STOP (drivers disabled and all servo outputs switched off), PCA9685 servo
  sequence for clamp/cut/demold, EEPROM calibration, overlong-line rejection, dancer and vibration in STATUS.
* XIAO ESP32-C3 bridge: USB, BLE UART (newline-framed, chunked notifications), optional Wi-Fi TCP,
  ILI9341 status display.
* Python package `seedforge`: geometry model, protocol, recipes with validation, host runner,
  simulator (Python port of the firmware state machine), deterministic vision QA with a synthetic
  labelled set, deployment ledger concept, CSV run logging.
* Firmware host tests (ASan/UBSan) and Python tests; simulator parity test against the compiled core.
* Diagrams A-I, 18 CAD renders, three BOM views, regenerated wiring schedule.
* GitHub Pages site with interactive 3D viewers and animations.
* Documentation: getting started, module docs M1-M10, controls, protocol, electronics, vision,
  calibration, validation framework, safety, drone concept, references.

### Changed
* **M2-only fasteners**: R3 STEP originals kept in `hardware/cad/source/r3_step/` and converted to M2
  holes on every build (`m2_fasteners.py`); all R3.1 parts use M2. New W15/W16 NEMA17 body clamps
  (the motors' face threads are M3), F08/F13 load-cell clamp and F12 roller yoke (2 x MR62ZZ on an
  M2 axle), W17/W18 plywood camera mast and arm for a 38 mm USB board camera. W06 and Q03 superseded.
* **Budget BOM**: generic parts, 12 V 3 A adapter instead of USB-C PD + trigger + 20-12 V buck,
  single-contact E-stop with rail sensing on D8 (`ESTOP_SENSE_RAIL`), ESP32/display/IMU optional.
  View A about $128 to buy with an owned Uno, motors and drivers (draft: $318).
* **Budget drone concept**: separate payload kit (RP2040, SG90 gates, IR confirmation, about $18)
  and a budget ArduPilot F405 quad; companion computer optional; ELRS telemetry (view C about $154,
  draft $451).
* Module numbering unified to M1-M10 (part-ID prefixes unchanged).
* Pin map: R3 core map adopted; R2 map archived.
* Firmware default pitch kept at 4.084 mm/rev but labelled an inconsistent commissioning value.

### Fixed (relative to R3)
* See [docs/project/r3-gap-analysis.md](docs/project/r3-gap-analysis.md): axis-height mismatch,
  W03 without bearing bores, missing linear-axis mounts, F01/F03 bore mismatches, missing load-cell,
  dancer and limit-switch mounts, out-of-sync reference generator, wrong watertightness report.

### Known limitations
* No physical build yet; every mechanical and process acceptance gate is open.
* S01 and T03 need geometry repair (two bodies each).
* M3 mounting, M4-M10 are experimental or upcoming.

## Earlier revisions (archived, not released from this repository)
* **R3** - modular real-world package (CAD, BOMs, R3 controller sketch).
* **R2** - detailed wiring package.
* **R1** - first build guide and parametric parts.
* **EECS 149 course project** - wood-winder prototype sketches (`archive/eecs149-original/`).
