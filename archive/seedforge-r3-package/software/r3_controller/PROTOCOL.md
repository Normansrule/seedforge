# SeedForge R3 core-controller protocol

ASCII lines terminated by newline.

## Commands to Uno

- `START` - start one winding job using the current pitch/speed recipe.
- `STOP` or `EMERGENCY_STOP` - immediate software safe stop and driver disable.
- `RESET` - return to IDLE only if the E-stop feedback loop is healthy.
- `HEARTBEAT` - must arrive at least once every 3 s while winding.
- `VISION_OK` - accept the wound body while controller is in VERIFY.
- `FAULT_GAP` - safe stop.
- `FAULT_OVERLAP` - safe stop.
- `FAULT_LENGTH` - safe stop.
- `FAULT_CAMERA` - safe stop.
- `PITCH=4.084` - set axial pitch in mm/rev while not winding.
- `STEP_US=1500` - set master rotation microstep interval while not winding.
- `STATUS` - request current status.

## Messages from Uno

- `SEEDFORGE_R3_READY`
- `EVENT:WIND_COMPLETE_WAITING_FOR_VISION`
- `EVENT:PART_ACCEPTED`
- `STATUS,state=...,rot=...,lin=...,estop=...,home=...,end=...,reason=...`

## Safety behavior

Fault commands are processed even if the system is otherwise paused or waiting. The original EECS149 sketch checked pause state before its emergency-stop command; R3 intentionally avoids that pattern.

The software disable is supplementary. The physical E-stop should interrupt motor/actuator power independently of firmware.

## Tension-loop integration

The example reserves Uno D11/D12 for HX711. Add the tension loop only after calibrating the actual load cell and measuring the wet veneer failure window. Required behavior:

1. sample tension at a stable rate;
2. low-pass filter modestly;
3. trip immediately above the validated high limit;
4. use a slower PI/PID correction to trim the winding speed or active dancer actuator;
5. log raw and calibrated tension for every run.

Do not invent a universal tension setpoint. It depends on veneer processing, grain, width, thickness, moisture, mandrel condition, and guide friction.
