# SeedForge R2 - Nature paper reference CAD additions

These files extend the R1 low-cost manufacturing package with dimensional reference models for the **forming mandrel** and the **fully assembled three-tailed seed carrier**.

## Most important files
- `step/MR01_0p8mm_x100mm_FORMING_MANDREL_REFERENCE.step` - exact 0.8 mm x 100 mm rod envelope. **Use a metal rod; do not print this as the working mandrel.**
- `step/MR06_COMPLETE_0p8mm_MANDREL_SUBASSEMBLY_REFERENCE.step` - fit-planning assembly for rod/chuck/stop.
- `step/MR07_0p8mm_MANDREL_WITH_STANDARD_7COIL_BODY_REFERENCE.step` - shows the seven-turn body directly on the 0.8 mm mandrel.
- `step/PR08_STANDARD_FINISHED_3TAIL_SEED_CARRIER_1TO1.step` - assembled 1:1 carrier reference.
- `step/PR09_STANDARD_SEED_CARRIER_EXPLODED_1TO1.step` - exploded view for assembly-station design.
- `step/PR24_STANDARD_FINISHED_CARRIER_3X_DEMO_PRINT.step` - enlarged FDM demonstration model; fits within the A1 Mini envelope but requires supports.
- `step/PR20_LARGE_PINE_7COIL_BODY_12x0p8_on_3mm.step` - large whitebark-pine carrier body reference.
- `step/PR21_whitebark_pine_seed_11mm_ENVELOPE.step` - 11 mm payload clearance reference.

Each reference model is also supplied as STL and 3MF. STEP is the preferred format for CAD/fixture work.

## Source-grounded dimensions used
**Standard 3-tail reference:** 3 tails, 1 coil layer, 7 coils, 35 mm body length; 0.8 mm mandrel; 2.5 mm tail/body width and 0.5 mm thickness in the supplementary simulation; tail strip/path lengths 27, 29.5 and 32.5 mm; favorable landing/resting angle about 25-30 degrees.

**Large whitebark-pine reference:** 12 mm wide, 0.8 mm thick, 300 mm-long wood veneer; 3 mm mandrel; 7-coil/85 mm body design; seed payload up to about 11 mm length.

## What is exact vs approximate
- Mandrel diameter, coil counts, body-length identifiers, standard tail widths/thicknesses and supplementary tail lengths are source-grounded.
- The detailed 3D free-shape of the dry tails and the flour-based tip surface are **engineering approximations** reconstructed from published figures because the authors' original Rhino/Supplementary File 3 geometry is not publicly supplied in the accessible text.
- `PR05`, `PR07`, `PR22`, and the spline curvature of PR02-PR04 are therefore for **machine clearance, cassette design and visualization**, not claims of author-identical geometry.
- The actual carrier should be wood/dough/fiber material as described by the paper, not FDM plastic.

## Machine integration
For the EECS149 winder, use the 0.8 mm metal mandrel with a miniature metal pin-vise/drill chuck or a precision collet. The printed MR02 insert is a low-cost prototype only. The winder should keep the guide angle and axial pitch adjustable: the course project's 4 mm-wide/45-degree/no-gap specification is not the same geometry as the paper-reference 2.5 mm/7-coil/35 mm carrier.
