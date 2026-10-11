# Controller protocol

Line-delimited ASCII, one message per line, terminated by `\n` or `\r` (so CRLF works; empty
lines are ignored). The same protocol
runs on the Uno USB port (115200 baud), on the Uno-ESP32 link (38400 baud) and, through the bridge,
on BLE (Nordic UART Service) and Wi-Fi TCP port 3333.

Implementations: `firmware/arduino/seedforge_core/src/sf_protocol.cpp` (C++) and
`software/seedforge/protocol.py` (Python). Parser unit tests: `tests/firmware/test_core.cpp` and
`tests/host/test_protocol.py`.

![protocol sequence](diagrams/F_protocol_sequence.svg)

## Syntax

```text
host -> controller   KEYWORD            or  KEYWORD=value
controller -> host   KEY=value          or  RECORD key=value key=value ...
```

* Keywords are case-insensitive on input; the controller always answers in upper case.
* Lines are limited to 63 characters on the Uno (95 on the bridge). A longer line is discarded
  **whole** and answered with `ERROR=BAD_COMMAND`; its tail is never executed.
* Numbers are **decimal fixed-point**: no exponents, optional sign, at most 12 digits. Each keyword
  has a fixed number of decimals (scale); extra decimals are truncated, not rounded. The firmware
  never uses floating point to parse.
* A keyword that needs a value without one, or a value given to a keyword that takes none, is an
  error (`ERROR=BAD_COMMAND`).

## Host -> controller

### Motion and state

| command | value | accepted in | effect |
|---|---|---|---|
| `HOME` | - | BOOT, READY, COMPLETE | home the traverse axis |
| `START` | - | READY, COMPLETE | run one cycle (re-homes first) |
| `STOP`, `EMERGENCY_STOP` | - | any | `SAFE_STOP` with `REMOTE_STOP` (software stop only; the E-stop is the real stop) |
| `RESET` | - | SAFE_STOP, COMPLETE, BOOT | back to BOOT; refused while the E-stop is pressed (rail absent) or tension is above the trip |
| `JOG` | mm, 2 decimals, signed | READY | relative traverse move, kept inside 0-100 mm |
| `STATUS` | - | any | one `STATUS` line |
| `GET_RECIPE` | - | any | one `RECIPE` line |

### Vision and supervision

| command | effect |
|---|---|
| `HEARTBEAT` | resets the heartbeat watchdog (send at least every `SET_HEARTBEAT_MS / 3`) |
| `VISION_OK` | accept the coil in VERIFY |
| `FAULT_GAP`, `FAULT_OVERLAP`, `FAULT_LENGTH`, `FAULT_TAIL`, `FAULT_CAMERA` | `SAFE_STOP` with the matching `VISION_*` fault, in any state |
| `LENGTH_MM=<mm>` | measured coil length (2 decimals), echoed and included in `COMPLETE` |

### Calibration

| command | value | effect |
|---|---|---|
| `TARE` | - | zero the load cell (stored in EEPROM) |
| `CAL_TENSION` | N, 3 decimals | set the scale from a known load (stored in EEPROM) |

### Recipe setters

Accepted only in BOOT, READY, COMPLETE and SAFE_STOP; answered `OK=<KEYWORD>` or
`ERROR=OUT_OF_RANGE` / `ERROR=BUSY`.

| command | scale | range | unit |
|---|---|---|---|
| `SET_PITCH` (alias `PITCH`) | 3 | 0.200-30.000 | mm per mandrel revolution |
| `SET_TURNS` | 0 | 1-40 | turns |
| `SET_SACRIFICIAL` | 0 | 0-5 | turns |
| `SET_RATE` | 1 | 1.0-300.0 | rev/min (accepted; the step generator caps the master axis at 8000 microsteps/s = 150 rev/min and reports `RATE_CLAMPED`) |
| `SET_ACCEL` | 1 | 1.0-3000.0 | rev/min per s |
| `SET_START` | 2 | 0.00-100.00 | mm from home |
| `SET_TENSION`, `SET_TENSION_MAX`, `SET_TENSION_MIN` | 3 | 0.000-9.800 | N |
| `SET_REQUIRE_TENSION`, `SET_REQUIRE_VISION`, `SET_M3` | 0 | 0 or 1 | flag |
| `SET_DEMOLD` | 2 | -100.00-100.00 | mm, relative |
| `SET_HEARTBEAT_MS` | 0 | 200-60000 | ms |
| `SET_DIR` | 0 | 0-3 | bit 0 rotation, bit 1 linear |
| `STEP_US` | 0 | > 0 | **legacy R3** master step interval in us; converted to `SET_RATE` |

## Controller -> host

| line | meaning |
|---|---|
| `SEEDFORGE_CORE fw=0.3.0-alpha` | banner after reset |
| `STATE=<state>` | state entered: BOOT, HOME, READY, PRETENSION, WIND, VERIFY, CLAMP, CUT, DEMOLD, COMPLETE, SAFE_STOP |
| `FAULT=<fault>` | reason for SAFE_STOP (list in [controls.md](controls.md#safety-stop-conditions)) |
| `ERROR=<code>` | command rejected; the state does not change (except `COMM_ERRORS`) |
| `OK=<keyword>` | setter or calibration accepted |
| `EVENT=<name>` | `PRETENSION_SKIPPED`, `WIND_DONE`, `VISION_BYPASSED` |
| `TURN=<n>` | completed mandrel revolutions in WIND |
| `TENSION=<N>` | tension sample, every 0.5 s in WIND when tension is required |
| `POSITION=<mm>` | carriage position after each move |
| `HOME_ERROR_MM=<mm>` | home re-check result (cycle homing only) |
| `LENGTH_MM=<mm>` | echo of the host's measurement |
| `COMPLETE turns=<n> lin_steps=<n> pitch_mm=<mm> length_mm=<mm or nan>` | cycle finished |
| `STATUS state=... fault=... homed=0/1 pos_mm=... turn=... tension_N=<N or nan> estop=1/0 home=0/1 end=0/1 dancer=<0-1023> vib_mg=<mg>` | `estop=1` means the switched rail is present (**OK**); `home`/`end` 1 = actuated; `dancer` is the raw A0 reading; `vib_mg` the IMU RMS (0 if not fitted) |
| `RECIPE pitch_mm=... turns=... sacrificial=... rate_rpm=... start_mm=... tension_max_N=... m3=0/1 vision=0/1` | current recipe |
| `BRIDGE ...` | from the ESP32 bridge only (`BRIDGE?` query, start-up banner); never forwarded to the Uno |

`STATUS` is also sent once per second while idle (BOOT, READY, COMPLETE, SAFE_STOP); during WIND it
is sent only on request, to keep link traffic low while stepping.

### Error codes

`BAD_COMMAND`, `BUSY`, `OUT_OF_RANGE`, `NOT_HOMED`, `NOT_READY`, `ESTOP_OPEN`, `ESTOP_STILL_OPEN`,
`TENSION_STILL_HIGH`, `TENSION_NOT_CONFIGURED`, `RECIPE_TRAVEL`, `UNEXPECTED_VISION_OK`,
`CAL_FAILED`, `JOG_RANGE`, `RATE_CLAMPED` (warning: the cycle still runs at the maximum rate),
`HOME_DRIFT` (warning: first home re-check outside tolerance).

## Example session

```text
> SET_PITCH=5.0
< OK=SET_PITCH
> SET_TURNS=7
< OK=SET_TURNS
> HOME
< STATE=HOME
< POSITION=2.00
< STATE=READY
> START
< STATE=HOME
< HOME_ERROR_MM=0.00
< POSITION=2.00
< STATE=PRETENSION
< POSITION=5.00
< EVENT=PRETENSION_SKIPPED
< STATE=WIND
> HEARTBEAT                      (every second from the host)
< TURN=1
...
< TURN=8
< POSITION=45.00
< EVENT=WIND_DONE
< STATE=VERIFY
> LENGTH_MM=40.38
< LENGTH_MM=40.38
> VISION_OK
< STATE=COMPLETE
< COMPLETE turns=8 lin_steps=16000 pitch_mm=5.000 length_mm=40.38
```

## Design notes

* Human-readable on purpose: you can drive the machine from any serial monitor.
* Fixed-point everywhere so the C++ and Python sides agree to the last digit.
* The bridge forwards only **complete, newline-terminated** lines in both directions, so a command
  split across BLE packets is never forwarded in pieces. BLE notifications are sent in 20-byte
  chunks ending with a newline. BLE terminals must be set to send a newline.
* Stopping does not depend on a message arriving: with vision required (the default) the Uno stops
  on a missing heartbeat in WIND/VERIFY, and the E-stop is hardware. With `SET_REQUIRE_VISION=0`
  there is no heartbeat watchdog; use that only for supervised dry runs.
