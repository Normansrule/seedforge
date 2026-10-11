# Safety and responsible use

SeedForge is research-prototype equipment. Nothing here is certified. The people building and
operating it are responsible for their own safety, for supervising others, and for getting the
approvals their institution and local law require.

## Before you power anything

* Read [electronics.md](electronics.md#safety-circuit-concept) and wire the **physical E-stop**
  first. It must remove actuator power by itself; a software stop is not an E-stop.
* Test the E-stop at the start of every session: press it during a jog; the motors must go limp and
  the controller must report `FAULT=ESTOP_OPEN`.
* Keep the E-stop within reach of the operator's hand while anything can move.
* Wear safety glasses. Tie back long hair, remove loose sleeves, lanyards and jewellery.

## Hazards

| hazard | where | controls |
|---|---|---|
| **Rotating machinery** | chuck and mandrel (up to 150 rev/min possible in firmware; 30 rev/min default), lead screw, coupler, spool | never touch while drivers are enabled; low default speeds; guard the chuck when unattended; E-stop |
| **Entanglement** | strip, thread and hair on the mandrel and spool | short sleeves, tie hair back; never hand-feed strip at speed |
| **Pinch points** | carriage between W09/W10, dancer arm, clamp jaws, servo linkages | hands out of the traverse path during motion; limit switches; low current |
| **Sharp points** | 0.8 mm mandrel ends, cut veneer, piano-wire offcuts | deburr mandrel ends; dispose of offcuts in a sharps container |
| **Cutters** (Phase 2) | M3 micro shear | purchased shear only (never print a blade); X04 guard; optional guard switch on A3 (`GUARD_FITTED`); power off before clearing jams |
| **Stepper-driver heat** | A4988 boards and heatsinks (can exceed 80 deg C) | set current with Vref; heatsinks; ventilated C03/C04 box; do not touch |
| **Electrical shorts** | 12 V rail from a 36 W adapter, 5 V servo buck | certified adapter; 3 A fuse directly after the jack; keyed motor connectors; check polarity and the buck's output before connecting; never plug motors with VMOT on |
| **Batteries** (Phase 8 only) | LiPo packs | follow the aircraft maker's charging and storage rules; fireproof bag; never charge unattended; no LiPo on the manufacturing bench |
| **Chemical wood processing** | veneer preparation | **not part of SeedForge**: see below |
| **Biological** | seeds, soil, mould on wet wood | gloves; clean and dry storage; species rules below |

## Chemical treatment: out of scope

The paper's veneer preparation involves chemical processing. SeedForge does **not** design,
document or automate any chemical treatment. Do not add dosing pumps, baths or reagent handling to
this machine. Wet veneer must come from a separate procedure that has an exact written protocol,
suitable facilities and fume extraction, PPE, waste disposal and **institutional approval**. Treat
prepared veneer as potentially contaminated until that protocol says otherwise.

## Seeds, ecosystems and permissions

* Use only species that are native and appropriate for the target site; never invasive or
  regulated species. Check with local forestry or conservation authorities.
* Do not release seeds or carriers on land without the **landowner's written permission**, and
  not in protected areas without the managing authority's approval.
* Carriers are wood plus a biodegradable tip, but the tip formulation and adhesives used in M6 must
  be checked for environmental safety before any outdoor test.
* Seed-viability and burial claims need controlled trials (Phase 5 and beyond). Nothing in this
  repository is biologically validated.

## Aerial deployment

Drone deployment is an **optional, downstream research concept** ([drone-concept.md](drone-concept.md)).
Flying a payload-dropping aircraft is regulated almost everywhere (in the United States, for example,
by the FAA; dropping objects and operating beyond visual line of sight need specific authorisation).
Do not fly SeedForge hardware without the required certification, waivers, airspace authorisation,
insurance and permission. The drone models in this repository are concept geometry, not
flight-validated.

## Software safety notes

* Safety trips in firmware (limits, tension, heartbeat, vision) are supplementary to the E-stop.
* The ESP32 bridge and the host are not safety devices. With vision required (the default) the Uno
  stops if they go silent during WIND/VERIFY; with `SET_REQUIRE_VISION=0` it does not, so use that
  only for supervised dry runs.
* `SAFE_STOP` needs a deliberate `RESET`, and the machine must home again afterwards. On SAFE_STOP the
  drivers are disabled and every servo output is switched off, so releasing the E-stop does not
  restart motion. (Servo outputs are switched off by firmware; the E-stop is what removes their
  power.)
* Do not raise the default speed, acceleration or tension trim gains without measured data.

## If something goes wrong

1. Press the E-stop.
2. Unplug the power supply before reaching into the machine.
3. Note what happened, keep the run log, and report safety defects privately
   ([SECURITY.md](../SECURITY.md)).
