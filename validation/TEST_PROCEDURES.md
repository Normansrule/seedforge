# Test procedures

Record each run with the commit hash, firmware banner, recipe file, operator and date. Use
`python -m seedforge.host ... --log runs/<date>/` so `carriers.csv` and `trace.csv` are written
automatically. Safety: [docs/safety.md](../docs/safety.md). Hand on the E-stop for every motion test.

## TP-0 Phase 0 material

**TP-0.1 dimensions.** Measure width (calipers) and thickness (micrometer) of 10 wet strips per lot
at three points each; dry five of them flat and re-measure. Record in the worksheet.

**TP-0.2 damage and break tension.** Clamp a strip end, hang it over a roller of the same diameter as
the M1 sensing roller, add mass in small steps (or pull through a calibrated force gauge). Record the
tension at the first visible crack, split or permanent set (damage) and at break. Five pulls per lot.

**TP-0.3 hand-wound reference.** Wind one coil by hand on a 0.8 mm rod at the intended pitch, dry it,
measure dry geometry. This is the comparison for machine coils.

## TP-1 Phase 1 winder

**TP-1.1 commissioning (dry, no strip).** Calibrations C2-C6 and C14 in
[docs/calibration.md](../docs/calibration.md). 20 dry cycles with `SET_REQUIRE_VISION=0`; all must
end COMPLETE with exact turns.

**TP-1.2 limits and homing.** With the switch unplugged, `STATUS` must show it actuated; `HOME` must
not move toward an unplugged switch forever (`HOME_TIMEOUT`). Press home and end levers by hand
during jogs: `HOME_LIMIT` / `END_LIMIT`.

**TP-1.3 stops.** During WIND: (a) E-stop: motors limp, `FAULT=ESTOP_OPEN`, `RESET` refused until
released; (b) START button: `LOCAL_STOP`; (c) kill the host program: `HEARTBEAT_TIMEOUT` within
`SET_HEARTBEAT_MS`; (d) host sends `FAULT_GAP`: `VISION_GAP`. Record each in a stop-test sheet.

**TP-1.4 tension.** With the load cell calibrated and the band set, enable `SET_REQUIRE_TENSION=1`;
pinch the strip gently by hand during WIND to exceed the trip: `TENSION_HIGH` within two samples.

**TP-1.5 material cycles.** Run cycles on real strip at a low rate first (10 rev/min). Count
consecutive successes; any jam, break or fault resets the count to zero and is logged with a cause.
Gate: 20 consecutive.

**TP-1.6 vision fault.** Wind (or prepare) a coil with a visible gap or overlap; the vision verdict
must reject it with the matching code.

## TP-2 Phase 2 cut / demold

**TP-2.1 servo travel.** Before installing linkages, sweep each servo channel and set pulse widths
in `sf_controller.h` so nothing hits an end stop.

**TP-2.2 guard.** With `GUARD_FITTED = true`, open the guard during CUT: `GUARD_OPEN`.

**TP-2.3 cut/release cycles.** `SET_M3=1`. 20 consecutive cycles; inspect every coil for dragging,
delamination or uncoiling; record `demold_result`.

## TP-6 vision

**TP-6.1 capture and label.** Capture every Phase-1/2 coil; label from measurement, not from the
verdict. **TP-6.2 evaluate.** `python -m seedforge.vision evaluate datasets/test/` after tuning only
on train/validation. Report the confusion matrix.

## TP-3, 4, 5, 7, 8

Defined at the start of each phase from the module docs (`docs/modules/`) and the acceptance table.
They must be written and reviewed **before** the phase's hardware is built.
