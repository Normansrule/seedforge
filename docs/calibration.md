# Calibration

Record every result in [`validation/CALIBRATION_WORKSHEET.csv`](../validation/CALIBRATION_WORKSHEET.csv)
with the date, operator, commit and machine ID. Re-do a calibration after any mechanical change
that could affect it.

| # | what | when | method | pass |
|---|---|---|---|---|
| C1 | printer fit (Z01 coupon) | before printing machine parts | print Z01, test M2 screws (2.4 clearance, 1.8 pilot), 8 mm rod, LM8UU, 608 | M2 thread-forming screw bites in the pilot; slip fit for rod/bearing, press fit for 608 |
| C2a | 5 V servo buck | before connecting servos | adjust the LM2596 trimmer with a meter on its output | 5.0 +- 0.1 V |
| C2 | driver current (Vref) | before connecting motors | `Vref = I x 8 x Rs` ([getting-started](getting-started.md#7-how-do-i-set-a4988-current-safely)) | within 0.02 V of target |
| C3 | motor direction | first power-up | `JOG=5`: carriage moves away from home; then a short dry cycle (`SET_REQUIRE_VISION=0`, no strip): mandrel turns the intended direction | correct, or set `SET_DIR` (bit 1 linear, bit 0 rotation) |
| C4 | home repeatability | after assembly | 10 x `HOME`, read `HOME_ERROR_MM` on cycles, or dial indicator | spread <= 0.05 mm |
| C5 | translation scale | after assembly | `JOG=50`, measure, 3 repeats each way | 50.00 +- 0.05 mm |
| C6 | rotation count | after assembly | 10-turn cycle without strip, flag on chuck | exactly 10 turns, same stop angle |
| C7 | mandrel runout and deflection | each new mandrel | dial indicator at free end while turning; hang 10/25/50 g at mid-span | record; compare with [carrier-geometry](carrier-geometry.md#mandrel-stiffness) |
| C8 | load cell | after M1 assembly, then weekly | `TARE`, `CAL_TENSION=<N>` with a hanging mass on the real strip path; check with two other masses | linear within 2 %; 3 tare/cal cycles within 5 % |
| C9 | spool drag and dancer | per material lot | measure tension while pulling strip by hand at winding speed; adjust felt washers | steady within the Phase-0 band |
| C10 | guide angle scale | after W12 assembly | protractor against the mandrel at 0, 30, 45, 50.8 deg | within 1 deg of the scale mark |
| C11 | camera scale | after camera mounting, after any bump | photograph a ruler or dot target in the mandrel plane | `px_per_mm` within 1 % across the field |
| C12 | camera exposure | per session | back-light on, coil absent: background saturated but not blooming | Otsu threshold separates cleanly |
| C13 | pitch on material | per recipe | wind 3 coils, measure length / turns under a microscope or calipers | within the recipe tolerance |
| C14 | vibration baseline | after M2 assembly | dry cycles at 10, 30, 60 rev/min without strip; send `STATUS` about once per second and record `vib_mg` | record; derate/trip set later |

## Details

### C4-C6: motion

The firmware assumes 3200 microsteps per mandrel revolution and 400 per mm. A consistent scale
error almost always means wrong microstep pins or a different lead screw (T8x2, T8x4 also exist);
fix the hardware or `sf_config.h`, never hide it in a recipe. Random error means binding, too little
current or too much acceleration.

### C7: mandrel

A 0.8 mm rod deflects about 0.8-1.9 mm at 0.5 N over a 90 mm span (geometry model). Measure your
own: clamp in the chuck, support in W05, hang known masses at the winding position, read the
deflection with a dial indicator or the camera. This sets how much tension the process can use
without changing the pitch the camera sees.

### C8: load cell

1. Strip slack, nothing touching the sensing roller except its own weight: `TARE`.
2. Tie a thread to a known mass, route it over the sensing roller exactly like the strip (same wrap
   angle), let it hang still: `CAL_TENSION=<mass_kg x 9.81>`.
3. Swap in two other masses and read `STATUS` (`tension_N=`). Record all three.
4. The calibration is stored in EEPROM and survives power cycles; it does not survive moving the
   roller or changing the wrap angle.

### C11: camera

Print a dot grid or use a steel rule, place it in the plane of the mandrel axis on the back-light,
capture with the station settings, and measure the pixel distance over at least 40 mm. Update
`px_per_mm` in the recipe's `vision` block. If the scale differs by more than 1 % between the left
and right of the field, correct lens distortion before use.

### C13: pitch on material

The first-order helix model ([carrier-geometry.md](carrier-geometry.md)) only predicts a starting
pitch. Wet veneer compresses, slips and swells. Wind three coils with the recipe, measure, then
adjust `SET_PITCH` and the guide angle together and record the accepted recipe as a new JSON file
with `provenance` explaining the data behind it.
