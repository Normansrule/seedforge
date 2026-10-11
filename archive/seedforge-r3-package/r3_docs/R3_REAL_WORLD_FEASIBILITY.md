# SeedForge R3 Real-World Feasibility Notes

## What is already feasible with inexpensive hardware

The synchronized winding mechanism is the most mature part of the concept. Two NEMA17 motors, A4988 drivers, a T8 lead screw, straight guide rods, a metal mandrel, an adjustable strip guide, a load cell, and a fixed camera are enough to perform repeatable research winding tests.

The most important design choice is modularity. Each station bolts to a plywood or extrusion base and can be operated manually during commissioning. This makes failures observable and keeps one bad subsystem from stopping the entire project.

## What should remain purchased rather than printed

Do not 3D print safety-critical or wear-critical items when cheap metal parts exist. Purchase:
- 0.8 mm forming mandrels;
- cutting blade/shear;
- motor shafts/couplers where precision matters;
- bearings and guide rods;
- drone frame, arms, propellers, motors, and flight controller;
- electrical safety components and fuses.

Print fixtures, covers, guides, brackets, trays, nests, and low-load grippers.

## Why the winder must remain adjustable

The course requirement and paper-inspired reference geometry differ. Wet wood also deforms, swells, compresses, and changes its effective winding radius. A nominal CAD helix is therefore only a starting point. The machine should expose three recipe parameters:
- guide angle;
- axial pitch per mandrel revolution;
- tension setpoint.

The final recipe is accepted only after dried geometry and functional drilling tests.

## Tension control

Use the load cell as the process variable. The dancer arm absorbs short disturbances. The IMU is a supervisory signal for excessive vibration, resonance, or mechanical looseness.

A practical control structure is:
- low-pass filtered tension measurement;
- PI/PID trim on overall winding velocity or dancer actuator if added;
- acceleration/vibration RMS threshold that derates the maximum allowable speed;
- immediate high-tension trip independent of the slow PID loop.

Do not tune the PID before measuring the actual force range of wet veneer.

## Computer vision

Start with deterministic measurements before training a model:
- calibrated pixels/mm;
- edge detection;
- coil centerline/turn count;
- gap/overlap measurement;
- body length;
- tail-count verification.

Machine learning is useful later for irregular delamination, splintering, and shape defects, but it should not replace simple geometric checks that are easier to debug.

## Electronics architecture

For the lowest-risk student prototype:
- Uno = hard real-time-ish motion and safety state;
- ESP32-C3 = BLE/Wi-Fi/UI bridge;
- host laptop/Pi = computer vision;
- A4988 = two primary axes;
- PCA9685 = servos;
- MCP23017 + ULN2003 = slow 28BYJ auxiliary steppers.

Keep the display on the ESP32-C3, not on the Uno. That avoids consuming the Uno's SPI pins and timing budget.

## USB-C rule

USB-C is excellent for supplying standardized power and programming controllers. It is a bad choice for arbitrary motor-phase wiring because an identical connector invites accidental connection to a laptop or charger.

Recommended:
- USB-C PD: bench input power;
- USB-C: Uno/ESP32/host data and programming;
- keyed JST-XH or locking connector: stepper phases and servo branches;
- screw terminals/ferrules: higher-current distribution.

## Material-process boundary

The research carrier depends on processed wood, not ordinary dry craft veneer. Treat wood preparation as a qualified lab process. Until the exact procedure is validated at your institution, keep chemical handling physically separate from hobby electronics, printed PETG fixtures, seeds, and the dry automation bench.

## Throughput

Do not optimize for speed initially. The highest-value metrics are yield and repeatability. A slow machine producing 20 acceptable carriers in a row is a stronger foundation than a fast line that jams every few cycles.

Once individual cycle times and drying dwell are measured, use parallel trays and multiple simple forming stations rather than making one mechanism extremely fast.

## Drone integration

The Nature paper demonstrates aerial delivery as an application, but the manufacturing project can be completed and validated without autonomous flight. Treat the drone as a downstream module.

A practical architecture is:
- proven ArduPilot-compatible aircraft;
- independent payload controller;
- companion computer for terrain classification only;
- pre-assigned non-overlapping restoration sectors;
- unique drop-point IDs;
- persist release intent before opening a gate;
- do not automatically retry an uncertain release.

This avoids coupling experimental seed hardware to flight stabilization.
