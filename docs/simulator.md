# Simulator (digital twin of the controller logic)

```bash
python -m seedforge.simulator --list
python -m seedforge.simulator normal            # home, wind 7 + 1 turns, vision accepts
python -m seedforge.simulator estop --log runs/  # also writes carriers.csv and trace.csv
python -m seedforge.simulator my_scenario.txt
```

No hardware needed. The simulator runs the **same state machine** as the Uno: `seedforge/simulator/core.py`
is a line-by-line Python port of `sf_controller.cpp` and `sf_motion.cpp`, and
`tests/host/test_sim_parity.py` compiles the C++ core (`tests/firmware/sim_core.cpp`) and checks
that both produce byte-identical message traces for every scenario.

**What it simulates:** state transitions, the Bresenham step generator at microstep resolution,
commanded turns, a lead-screw carriage with NC home/end switches and virtual limits, the E-stop
loop, a virtual load cell, host heartbeats and vision verdicts, injected faults, and run logs.

**What it does not simulate:** veneer mechanics, real tension dynamics, mandrel deflection, motor
torque or missed steps from overload, camera images. It says nothing about whether real veneer will
wind well. Logged rows are marked `data_source = SIMULATION`.

## Built-in scenarios

| name | what happens | expected end |
|---|---|---|
| `normal` | home, 7 active + 1 sacrificial turns at 4.084 mm/rev, vision accepts | COMPLETE, 8 turns, 13069 linear steps |
| `estop` | E-stop loop opens during WIND; RESET refused until it closes | SAFE_STOP (`ESTOP_OPEN`), then BOOT after reset |
| `tension-high` | calibrated load cell exceeds `SET_TENSION_MAX` while winding | SAFE_STOP (`TENSION_HIGH`) |
| `vision-gap` | host reports `FAULT_GAP` in VERIFY | SAFE_STOP (`VISION_GAP`) |
| `heartbeat-timeout` | host stops sending `HEARTBEAT` during WIND | SAFE_STOP (`HEARTBEAT_TIMEOUT`) |
| `home-switch-fault` | home switch never trips | SAFE_STOP (`HOME_TIMEOUT`) |
| `m3` | Phase-2 cycle with clamp, cut, demold | COMPLETE after DEMOLD |

## Scenario files

Plain text, one operation per line, `#` for comments:

| line | meaning |
|---|---|
| `send <protocol line>` | host sends a command |
| `step <ms>` | advance simulated time |
| `until <STATE> <ms>` | advance until the controller is in STATE (or the time runs out) |
| `press` | press the START button once |
| `set <key> <int>` | change the virtual plant |

`set` keys: `estop` (1 = loop closed), `home_dead`, `home_stuck`, `end_forced`, `guard`,
`tension_valid`, `tension_mN`, `hb_period_ms` (0 = host sends no heartbeats), `auto_vision_ok`
(host answers `VISION_OK` automatically), `drift_per_cycle` (lose N linear steps per cycle, to
test skipped-step detection), `phys_steps` (carriage start position, 400 per mm).

Example:

```text
# Wind the paper-reference body and report a measured length
set hb_period_ms 500
send SET_PITCH=5.0
send SET_TURNS=7
send HOME
until READY 60000
send START
until VERIFY 200000
send LENGTH_MM=40.38
send VISION_OK
until COMPLETE 20000
step 50
```

## Host runner against the simulator

The host program can drive the simulator instead of a serial port, including vision on synthetic
images:

```bash
python -m seedforge.host --port sim --recipe paper_reference --vision synthetic --log runs/
```

`--speed` runs simulated time faster than real time (default 20).
