// SeedForge core controller - compile-time configuration.
// Pin map follows docs/electronics.md and hardware/wiring/pin_map.csv (R3 core map).
#pragma once
#include <stdint.h>

namespace sf {

// ---------------------------------------------------------------- pins (Arduino Uno)
constexpr uint8_t PIN_ROT_STEP = 2;    // PORTD2
constexpr uint8_t PIN_ROT_DIR  = 3;
constexpr uint8_t PIN_LIN_STEP = 4;    // PORTD4
constexpr uint8_t PIN_LIN_DIR  = 5;
constexpr uint8_t PIN_ENABLE   = 6;    // both A4988 ENABLE, active LOW; 10k pull-up to 5 V on the board
constexpr uint8_t PIN_START    = 7;    // momentary to GND, INPUT_PULLUP
constexpr uint8_t PIN_ESTOP_FB = 8;    // E-stop feedback, see ESTOP_SENSE_RAIL
// true  (budget default): D8 senses the E-stop-SWITCHED 12 V actuator rail through a 10 k / 4.7 k
//       divider (about 3.8 V). HIGH = rail present = safe to move; LOW = E-stop pressed, fuse blown,
//       supply off or sense wire broken. No auxiliary E-stop contact needed.
// false (R3.1 wiring): an auxiliary NC E-stop contact pulls D8 to GND; open (HIGH) = unsafe.
constexpr bool ESTOP_SENSE_RAIL = true;
constexpr uint8_t PIN_HOME     = 9;    // NC microswitch to GND; HIGH = actuated or broken wire
constexpr uint8_t PIN_END      = 10;   // NC microswitch to GND; HIGH = actuated or broken wire
constexpr uint8_t PIN_HX_DOUT  = 11;
constexpr uint8_t PIN_HX_SCK   = 12;
constexpr uint8_t PIN_LED      = 13;
// A0 dancer pot, A1 link RX (from ESP32 TX), A2 link TX (to ESP32 RX via 1k/2k divider),
// A3 optional cutter-guard NC switch, A4/A5 I2C (PCA9685 0x40, ICM-20948 0x69, MCP23017 0x20).
constexpr uint8_t PIN_DANCER   = 14;   // A0
constexpr uint8_t PIN_LINK_RX  = 15;   // A1
constexpr uint8_t PIN_LINK_TX  = 16;   // A2
constexpr uint8_t PIN_GUARD    = 17;   // A3

constexpr uint32_t USB_BAUD  = 115200;
constexpr uint32_t LINK_BAUD = 38400;  // SoftwareSerial; keep identical in firmware/esp32

// ---------------------------------------------------------------- kinematics
constexpr uint32_t FULL_STEPS_PER_REV = 200;
constexpr uint32_t MICROSTEPS         = 16;      // A4988 MS1..MS3 all HIGH
constexpr uint32_t ROT_USTEPS_PER_REV = FULL_STEPS_PER_REV * MICROSTEPS;          // 3200
constexpr uint32_t LEAD_MM            = 8;       // T8x8: 8 mm per screw revolution
constexpr uint32_t LIN_USTEPS_PER_MM  = FULL_STEPS_PER_REV * MICROSTEPS / LEAD_MM; // 400

// Hard ceilings independent of the recipe (protect the hardware and the ISR budget).
constexpr uint32_t MAX_MASTER_HZ   = 8000;   // master-axis microsteps per second
constexpr uint32_t MIN_MASTER_HZ   = 40;
constexpr uint32_t HOMING_HZ       = 1600;   // 4 mm/s
constexpr uint32_t MAX_TRAVEL_UM   = 100000; // soft travel limit from home. R3.1 core cell: home trips at
                                             // carriage x = 45 mm, end switch at x = 149 mm; collision-free
                                             // windows per guide angle: hardware/cad/source/core_cell_layout.json

// ---------------------------------------------------------------- PCA9685 servo channels
constexpr uint8_t CH_CLAMP          = 0;
constexpr uint8_t CH_CUTTER         = 1;
constexpr uint8_t CH_TAIL_SWEEP     = 2;
constexpr uint8_t CH_TAIL_CLAMP     = 3;
constexpr uint8_t CH_TRANSFER_GRIP  = 4;
constexpr uint8_t CH_TRANSFER_Z     = 5;
constexpr uint8_t CH_DEMOLD_SUPPORT = 6;   // R3.1 addition (split support W07/W08)

}  // namespace sf
