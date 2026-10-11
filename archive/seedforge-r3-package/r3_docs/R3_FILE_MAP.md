# SeedForge R3 File Map

## Complete machine CAD

`cad/3mf/` - 55 geometry-only 3MF machine/tooling models.

`cad/stl/` - 55 STL machine/tooling models. Use these if a slicer dislikes a generic 3MF container.

`cad/step/` - 55 editable STEP machine/tooling models.

`cad/SeedForge_R1_parts_catalog.step` - spaced reference catalog of the machine parts; not a fully assembled machine.

## Seed carrier and mandrel CAD

`cad/paper_reference/step/` - editable/fixture-design reference models.

Most important:
- `MR01_0p8mm_x100mm_FORMING_MANDREL_REFERENCE.step`
- `MR06_COMPLETE_0p8mm_MANDREL_SUBASSEMBLY_REFERENCE.step`
- `MR07_0p8mm_MANDREL_WITH_STANDARD_7COIL_BODY_REFERENCE.step`
- `PR08_STANDARD_FINISHED_3TAIL_SEED_CARRIER_1TO1.step`
- `PR09_STANDARD_SEED_CARRIER_EXPLODED_1TO1.step`
- `PR24_STANDARD_FINISHED_CARRIER_3X_DEMO_PRINT.step`

`cad/paper_reference/stl/` and `cad/paper_reference/3mf/` contain corresponding mesh/model-container versions.

The 1:1 seed CAD is a manufacturing/clearance reference. The functional carrier should be made from the validated wood/tip process, not from plastic.

## Wiring and schematics

`previews/FACTORY_PIN_WIRING.png` - visual pin-level factory wiring.

`previews/ELECTRONICS_ARCHITECTURE.png` - controller/power architecture.

`wiring/connection_table.csv` - detailed point-to-point connection table.

`wiring/pin_map.csv` - original detailed pin map.

`r3_docs/R3_WIRING_QUICK_REFERENCE.md` - simplified R3 development wiring.

`r3_docs/R3_CORE_PIN_MAP.csv` - R3 core-controller pin allocation.

## BOM

`bom/SeedForge_R2_BOM.csv` - full machine + optional aircraft BOM.

`bom/SeedForge_R3_PHASED_PURCHASE_PLAN.csv` - same BOM tagged by build phase/priority.

`bom/SeedForge_R3_MINIMUM_CORE_BOM.csv` - smallest practical M1/M2/M3 purchase list.

## Build and validation

`START_HERE.md` - begin here.

`r3_docs/R3_BUILD_PLAN.md` - staged commissioning order.

`r3_docs/R3_REAL_WORLD_FEASIBILITY.md` - engineering rationale and boundaries.

`r3_validation/CALIBRATION_WORKSHEET.csv` - fill this in for each accepted recipe.

`r3_validation/RUN_LOG_TEMPLATE.csv` - run-by-run traceability template.

## Software

`software/original_eecs149_repo/` - untouched uploaded project code.

`software/r3_controller/seedforge_r3_core_controller.ino` - safer core winder example.

`software/r3_controller/PROTOCOL.md` - command/event protocol.

`software/r3_controller/host_command_example.py` - simple host integration example.

## Preview images

`previews/LOW_COST_BENCH_LAYOUT.png`

`previews/ALL_PRINTED_PARTS_actual_CAD.png`

`previews/PAPER_STANDARD_FINISHED_SEED_RENDER.png`

`previews/MANDREL_WITH_COIL_RENDER.png`

`previews/DRONE_PAYLOAD_WIRING.png`
