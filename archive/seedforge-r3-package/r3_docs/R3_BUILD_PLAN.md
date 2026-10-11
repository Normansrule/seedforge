# SeedForge R3 Build Plan

## Design objective

Build a reliable research-scale automated manufacturing line by proving one mechanism at a time. The correct engineering order is not "print everything and integrate." It is "characterize -> wind -> demold -> form -> assemble -> inspect -> automate transfer -> deploy."

## Phase 0 - Material and metrology

Hardware:
- digital caliper;
- scale capable of measuring small carrier mass changes if available;
- 0.8 mm metal mandrels;
- prepared veneer samples from your approved material process.

Measure for every test lot:
- wet width and thickness;
- dry width and thickness;
- mandrel diameter;
- force/tension at first visible damage and at break;
- dry coil diameter and pitch after release;
- body length after drying.

Output: a recipe card, not an assumption.

## Phase 1 - Core synchronized winder

Build M1 feed/tension and M2 winder only.

Mechanics:
- spool/blank feed;
- dancer and load-cell tension path;
- rotation NEMA17;
- 0.8 mm metal mandrel in metal chuck;
- T8x8 linear axis;
- two 8 mm guide rods with LM8UU carriage;
- adjustable guide;
- end support.

Control:
- rotation microsteps/rev = 200 x selected microstepping;
- T8x8 translation microsteps/mm = 200 x microstepping / 8;
- DDA/Bresenham synchronization so linear motion is derived from the calibrated pitch, not from blocking delays.

Acceptance gate:
- 20 consecutive bodies with exact commanded turn count;
- no skipped steps;
- measured pitch repeatability within the tolerance your functional carrier tests accept;
- tension trace remains inside the experimentally established safe band.

## Phase 2 - Clamp, cut, and wet demold

Add M3 cutter and W07/W08 split demold collar.

Sequence:
1. finish the sacrificial turn;
2. stop both axes;
3. clamp only the inactive handling region;
4. cut with a guarded purchased blade/shear;
5. close the silicone-lined split demold support lightly;
6. retract the mandrel axially;
7. open the support and transfer the wet coil to a free-dry tray.

Acceptance gate:
- 20/20 cuts complete without pulling the coil;
- no visible delamination caused by clamp or demold;
- coil does not have to be dragged over a closed undercut.

## Phase 3 - Tail forming

Build M4 as its own bench station.

Use a split former so the wet part can be released by opening the fixture rather than sliding it over a hook. Start with separately formed tails because that isolates process variables. If biological testing requires one continuous primary tail/body blank, change only the blank presentation step rather than redesigning the whole machine.

Acceptance gate:
- tails release without tearing;
- dried shape is repeatable enough to seat in the assembly fixture;
- three tails can be located 120 degrees apart without forcing them.

## Phase 4 - Free drying

Use Q01 trays with a low-adhesion liner and room-temperature air movement. Drying must be asynchronous: trays are a buffer so the machine can continue making other parts while earlier parts dry.

Record:
- material lot;
- start time;
- temperature/humidity if available;
- tray position;
- dry release time;
- final geometry.

Acceptance gate:
- dry carrier geometry is stable enough to assemble;
- no fixture-induced flattening or permanent deformation.

## Phase 5 - Seed/tip/tail assembly

Use M5 only after dry-body and tail geometry are stable.

Recommended low-cost sequence:
1. index one seed from a species-specific pocket disk or manually present one during early tests;
2. place body in S04 three-tail nest;
3. present two additional tails;
4. dispense a validated small adhesive dose only at inactive interfaces;
5. form the biodegradable tip with a compliant/non-stick working mold derived from S07/S08;
6. allow the tip/adhesive to cure under the validated seed-safe process.

Do not heat live seed unless seed viability testing has explicitly validated the exposure.

Acceptance gate:
- one seed present;
- three tails present and retained;
- active coils remain free of adhesive;
- tip survives handling and release;
- seed viability testing remains acceptable.

## Phase 6 - Vision QA

Use fixed camera position and fixed illumination. The RealSense or USB camera should not be handheld during calibration.

Inspect at minimum:
- turn count;
- body length;
- gap/overlap;
- missing/broken tail;
- missing tip;
- gross deformation;
- occupied seed location if the tip process permits verification.

Vision should report events to the controller; the controller owns the machine state.

Acceptance gate:
- validate on a manually labelled set of good and bad parts;
- document false accept and false reject rates;
- require a heartbeat timeout so loss of the vision process cannot silently continue production.

## Phase 7 - XY transfer automation

Only now add M8. Use a donor 3D-printer gantry if available. Pick parts only from sacrificial handling tabs, nests, or rigid fixtures. Do not pinch the active wet coil.

Acceptance gate:
- 50 transfers with no dropped part;
- no station collision after homing;
- loss of power cannot allow a Z axis or gripper to fall into a hazardous state.

## Phase 8 - Drone cassette

Prove the carrier first, then the aircraft payload.

Use one carrier per isolated cassette cell. Bench-test door retention and release hundreds of times before flight. The payload controller should be separate from the flight controller. The companion computer may recommend acceptable release sites, but the flight controller remains responsible for stabilization, geofence, and failsafe behavior.

Acceptance gate before flight:
- actual loaded mass measured;
- CG measured;
- thrust margin verified with the selected aircraft;
- door stays closed on power loss;
- no servo EMI/reset problems;
- release confirmed on the bench;
- applicable flight and land-use permissions are satisfied.

## Stop conditions

Stop the machine immediately for:
- open E-stop loop;
- hard-limit activation in the wrong direction;
- tension above the validated high limit;
- repeated skipped-step evidence;
- camera fault or heartbeat timeout during a quality-critical state;
- cutter guard/open-access condition if added;
- communication state that cannot be unambiguously recovered.

The machine should require a deliberate RESET after any safety stop.
