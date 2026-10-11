# SeedForge R3 - Real-World Modular Seed-Carrier Manufacturing Prototype

This package turns the EECS 149 wood-winder prototype into a staged, modular research manufacturing system for moisture-responsive wooden seed carriers inspired by Luo et al., Nature 614, 463-470 (2023).

## What R3 is designed to do

R3 is a buildable laboratory prototype, not an industrial production line. It is organized so each station can be built, tested, and accepted independently before adding transfer automation or drone deployment.

The recommended process is:

`PREPARED VENEER -> FEED/TENSION -> WIND -> CLAMP/CUT -> DEMOLD -> TAIL FORM -> FREE DRY -> SEED/TIP ASSEMBLY -> VISION QA -> OUTPUT TRAY -> OPTIONAL DRONE CASSETTE`

The wet-material preparation step should remain a separate, approved lab process until your team has validated the material protocol and safety procedures. R3 does not automate chemical dosing or waste handling.

## The three files to open first

1. `r3_docs/R3_BUILD_PLAN.md` - exact build order and acceptance gates.
2. `r3_docs/R3_WIRING_QUICK_REFERENCE.md` - simplified electronics/power wiring.
3. `r3_docs/R3_MODULE_MAP.csv` - module-by-module hardware, prints, and test criteria.

For exact point-to-point wiring, use `wiring/connection_table.csv` and `wiring/pin_map.csv` from the detailed R2 engineering package. R3 also includes an updated controller-oriented pin map under `r3_docs/R3_CORE_PIN_MAP.csv`.

## The first parts to print

Do not print the entire machine first. For the first functional station, print:

- `cad/3mf/Z01_fit_calibration_coupon.3mf`
- `cad/3mf/F06_veneer_guide_45deg_lower.3mf`
- `cad/3mf/F07_veneer_guide_lid.3mf`
- `cad/3mf/W01_nema17_rotation_mount.3mf`
- `cad/3mf/W02_608_mandrel_support.3mf`
- `cad/3mf/W03_lm8uu_linear_carriage.3mf`
- `cad/3mf/W04_t8_nut_carrier.3mf`
- `cad/3mf/W05_mandrel_end_guide.3mf`
- `cad/3mf/W07_micro_release_clamp_lower.3mf`
- `cad/3mf/W08_micro_release_clamp_upper.3mf`
- `cad/3mf/X01_sg90_clamp_mount.3mf`
- `cad/3mf/X02_soft_clamp_jaw.3mf`

A ready-to-print ZIP containing this subset is included as `SeedForge_R3_PHASE1_CORE_PRINTS.zip` beside the complete package.

## The actual forming rod

Use a purchased straight metal rod, not a printed rod.

- Standard paper-reference mandrel: 0.8 mm diameter.
- R3 machine working length: about 100 mm, chosen to leave room for chucking and support.
- CAD reference: `cad/paper_reference/step/MR01_0p8mm_x100mm_FORMING_MANDREL_REFERENCE.step`.
- Full mandrel fit reference: `cad/paper_reference/step/MR06_COMPLETE_0p8mm_MANDREL_SUBASSEMBLY_REFERENCE.step`.
- Mandrel plus seven-coil reference: `cad/paper_reference/step/MR07_0p8mm_MANDREL_WITH_STANDARD_7COIL_BODY_REFERENCE.step`.

Use a miniature metal pin vise or chuck that actually grips 0.8 mm stock. The printed split-collet model is only a fit experiment.

## The finished seed-carrier reference

The Nature work uses a three-tailed, hygromorphic wooden carrier. R3 includes a machine-clearance reference model:

- `cad/paper_reference/step/PR08_STANDARD_FINISHED_3TAIL_SEED_CARRIER_1TO1.step`
- `cad/paper_reference/step/PR09_STANDARD_SEED_CARRIER_EXPLODED_1TO1.step`
- `cad/paper_reference/3mf/PR24_STANDARD_FINISHED_CARRIER_3X_DEMO_PRINT.3mf`

The 1:1 CAD is for fixture, clearance, and process planning. Do not print the 1:1 plastic model and treat it as a functional seed carrier. The functional device depends on wood material, moisture response, and the seed/tip assembly.

## Important geometry distinction

Your course specification and the published paper reference are not identical recipes.

Your course target uses approximately 4 mm x 0.5 mm veneer on a 0.8 mm mandrel at a nominal 45 degree winding angle. The Nature paper and supplementary models include seven-coil, 0.5 mm-thick actuators around a 0.8 mm mandrel, with source examples around 2.5-3 mm width. Therefore keep guide angle and axial pitch adjustable and calibrate the actual wet material rather than hard-coding one ratio.

## Control architecture

Use two layers:

- Arduino Uno: deterministic motor stepping, limit switches, E-stop sensing, tension input, and core finite-state machine.
- ESP32-C3 USB-C board: BLE/Wi-Fi communications, UI/display, and communication with the vision host.

Do not stream images through the Uno. The vision computer should send compact events such as `VISION_OK`, `FAULT_GAP`, `FAULT_OVERLAP`, `LENGTH_MM=...`, and `HEARTBEAT`.

## Power architecture

Use USB-C only where USB-C is appropriate:

- USB-C PD supply -> PD trigger -> 12 V motor rail.
- 12 V -> 5 V buck -> servos and low-voltage auxiliaries.
- Uno and ESP32 can remain separately USB powered during development.

Do not use USB-C plugs as arbitrary stepper-motor connectors. Use keyed 4-pin motor connectors or screw terminals for motor phases so a motor cable cannot be accidentally plugged into a computer or charger.

## Minimum success criteria before adding more automation

The core winder must demonstrate all of the following before you build the full line:

- repeatable seven active turns plus the chosen sacrificial allowance;
- stable tension below measured break/delamination limits;
- no uncontrolled overlap/gap according to the selected recipe;
- reliable stop on vision fault;
- repeatable clamp/cut;
- wet-part demolding without dragging the coil over an undercut;
- at least 20 consecutive cycles without a mechanical jam.

Only after the core passes should you add automatic tail forming, seed handling, XY transfer, or drone loading.

## Source basis

Primary paper: Luo, D. et al. "Autonomous self-burying seed carriers for aerial seeding." Nature 614, 463-470 (2023). DOI 10.1038/s41586-022-05656-3.

R3 preserves the original EECS 149 repository under `software/original_eecs149_repo/` and adds a safer core-controller example under `software/r3_controller/`.
