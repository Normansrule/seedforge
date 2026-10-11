# Firmware

| folder | board | role | status |
|---|---|---|---|
| [`arduino/seedforge_core`](arduino/seedforge_core/) | Arduino Uno (ATmega328P) | real-time core: stepping, sync, homing, limits, tension trip, E-stop feedback, state machine, M3 servos | Compile-tested; hardware testing pending |
| [`esp32/seedforge_bridge`](esp32/seedforge_bridge/) | Seeed XIAO ESP32-C3 | USB / BLE / Wi-Fi bridge and ILI9341 status display; not safety-relevant | Compile-tested; hardware testing pending |

Licence: MIT. Design and behaviour: [docs/controls.md](../docs/controls.md),
[docs/protocol.md](../docs/protocol.md). Wiring: [docs/electronics.md](../docs/electronics.md).

## Uno core

```bash
arduino-cli core install arduino:avr
arduino-cli compile --fqbn arduino:avr:uno firmware/arduino/seedforge_core
arduino-cli upload  --fqbn arduino:avr:uno -p <port> firmware/arduino/seedforge_core
```

or open `seedforge_core.ino` in the Arduino IDE. Only built-in libraries are used (Wire, EEPROM,
SoftwareSerial). Last build: 28,292 bytes flash (87 %), 1,029 bytes RAM (50 %), no warnings.

Things to edit before flashing:

* `seedforge_core.ino`: `GUARD_FITTED = true` once a cutter-guard switch is wired to A3.
* `src/sf_config.h`: pins, microstepping, lead, travel limit (100 mm for the R3.1 core cell),
  PCA9685 channels.
* `src/sf_controller.h`: servo pulse widths (starting values; tune for your linkage), timeouts.

Host tests (no Arduino needed):

```bash
make -C tests/firmware          # builds the core with g++ -Wall -Wextra -Werror + ASan/UBSan, runs 22 tests
```

The core (`src/sf_protocol.*`, `src/sf_motion.*`, `src/sf_controller.*`) is plain C++17 with no
Arduino dependency; `seedforge_core.ino` and `src/sf_drivers_avr.*` are the only AVR-specific code.

## ESP32-C3 bridge

```bash
arduino-cli core install esp32:esp32
arduino-cli lib install "Adafruit GFX Library" "Adafruit ILI9341"
arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32C3 firmware/esp32/seedforge_bridge
```

Compiled against Espressif Arduino core 3.3.2 (compile-tested only); last build 1,227,634 bytes (93 % of the
default partition). BLE advertises as `SEEDFORGE` (Nordic UART Service). Wi-Fi TCP on port 3333 is
compiled in only if `secrets.h` exists:

```bash
cp firmware/esp32/seedforge_bridge/secrets.example.h firmware/esp32/seedforge_bridge/secrets.h
# edit SSID/password; secrets.h is git-ignored
```

The bridge answers `BRIDGE?` itself and forwards every other complete line. It never generates
`HEARTBEAT`, `VISION_OK` or commands of its own.

## Archived firmware

The original EECS 149 sketches and the R3 controller are in `archive/`. They are kept for
provenance and are superseded; do not flash them on the R3.1 machine (different pin map, no homing,
no tension trip, and one has a default access-point password).
