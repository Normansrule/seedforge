// SeedForge line protocol (ASCII, one message per line, '\n' or '\r' terminated).
// Specification: docs/protocol.md.  Shared grammar with software/seedforge/protocol.py.
#pragma once
#include <stdint.h>

namespace sf {

enum class Cmd : uint8_t {
  INVALID = 0,
  // motion / state
  START, STOP, RESET, HOME, STATUS, GET_RECIPE, TARE, CAL_TENSION,
  // vision / host events
  HEARTBEAT, VISION_OK, FAULT_GAP, FAULT_OVERLAP, FAULT_LENGTH, FAULT_TAIL, FAULT_CAMERA, LENGTH_MM,
  // recipe setters
  SET_PITCH, SET_TURNS, SET_SACRIFICIAL, SET_RATE, SET_ACCEL, SET_START, SET_TENSION, SET_TENSION_MAX,
  SET_TENSION_MIN, SET_REQUIRE_TENSION, SET_REQUIRE_VISION, SET_M3, SET_DEMOLD, SET_HEARTBEAT_MS,
  SET_DIR,
  // manual jog (READY only)
  JOG,
  COUNT_
};

struct Command {
  Cmd cmd = Cmd::INVALID;
  bool has_value = false;
  int32_t value = 0;     // fixed point: scale given by valueScale(cmd)
};

// Number of decimal places carried in Command::value for this command
// (e.g. SET_PITCH=4.084 -> value 4084 with scale 3).
uint8_t valueScale(Cmd c);
char* cmdName(Cmd c, char* buf, uint8_t len);   // copies the canonical name

// Parse one line in place (line may be modified). Leading/trailing blanks and
// case are ignored. Returns false for unknown keywords, malformed or
// out-of-format numbers (range checks happen in the controller).
bool parseLine(char* line, Command& out);

// Parse a signed decimal string into fixed point with `scale` decimals.
// Accepts optional sign, digits, optional '.', digits. Rejects anything else
// and values beyond +-2e9 in fixed point.
bool parseFixed(const char* s, uint8_t scale, int32_t& out);

// Format fixed point (value / 10^scale) into buf. Returns buf.
char* formatFixed(int32_t value, uint8_t scale, char* buf, uint8_t buflen);

}  // namespace sf
