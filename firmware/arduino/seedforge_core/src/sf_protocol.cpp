#include "sf_protocol.h"

#include <string.h>

#if defined(__AVR__)
#include <avr/pgmspace.h>
#define SF_PROGMEM PROGMEM
#define SF_MEMCPY_P memcpy_P
#else
#define SF_PROGMEM
#define SF_MEMCPY_P memcpy
#endif

namespace sf {

namespace {

struct Entry {
  char name[20];        // stored in flash on AVR (saves ~600 bytes of RAM)
  Cmd cmd;
  int8_t needs_value;   // 1 = required, 0 = forbidden
  uint8_t scale;
};

// Keep names <= 19 characters. Aliases (PITCH=, STEP_US=) from R3 are mapped
// below for backwards compatibility with archive/seedforge-r3-package tools.
const Entry kTable[] SF_PROGMEM = {
    {"START", Cmd::START, 0, 0},
    {"STOP", Cmd::STOP, 0, 0},
    {"EMERGENCY_STOP", Cmd::STOP, 0, 0},
    {"RESET", Cmd::RESET, 0, 0},
    {"HOME", Cmd::HOME, 0, 0},
    {"STATUS", Cmd::STATUS, 0, 0},
    {"GET_RECIPE", Cmd::GET_RECIPE, 0, 0},
    {"TARE", Cmd::TARE, 0, 0},
    {"CAL_TENSION", Cmd::CAL_TENSION, 1, 3},      // known load in newtons
    {"HEARTBEAT", Cmd::HEARTBEAT, 0, 0},
    {"VISION_OK", Cmd::VISION_OK, 0, 0},
    {"FAULT_GAP", Cmd::FAULT_GAP, 0, 0},
    {"FAULT_OVERLAP", Cmd::FAULT_OVERLAP, 0, 0},
    {"FAULT_LENGTH", Cmd::FAULT_LENGTH, 0, 0},
    {"FAULT_TAIL", Cmd::FAULT_TAIL, 0, 0},
    {"FAULT_CAMERA", Cmd::FAULT_CAMERA, 0, 0},
    {"LENGTH_MM", Cmd::LENGTH_MM, 1, 2},
    {"SET_PITCH", Cmd::SET_PITCH, 1, 3},          // mm per mandrel revolution
    {"PITCH", Cmd::SET_PITCH, 1, 3},              // R3 alias
    {"SET_TURNS", Cmd::SET_TURNS, 1, 0},          // active turns
    {"SET_SACRIFICIAL", Cmd::SET_SACRIFICIAL, 1, 0},
    {"SET_RATE", Cmd::SET_RATE, 1, 1},            // mandrel rev/min
    {"SET_ACCEL", Cmd::SET_ACCEL, 1, 1},          // mandrel rev/min per second
    {"SET_START", Cmd::SET_START, 1, 2},          // carriage start position, mm from home
    {"SET_TENSION", Cmd::SET_TENSION, 1, 3},      // setpoint, N
    {"SET_TENSION_MAX", Cmd::SET_TENSION_MAX, 1, 3},  // hard trip, N
    {"SET_TENSION_MIN", Cmd::SET_TENSION_MIN, 1, 3},  // pretension acceptance, N
    {"SET_REQUIRE_TENSION", Cmd::SET_REQUIRE_TENSION, 1, 0},
    {"SET_REQUIRE_VISION", Cmd::SET_REQUIRE_VISION, 1, 0},
    {"SET_M3", Cmd::SET_M3, 1, 0},                // 1 = clamp/cut/demold hardware installed
    {"SET_DEMOLD", Cmd::SET_DEMOLD, 1, 2},        // relative retraction distance, mm (signed)
    {"SET_HEARTBEAT_MS", Cmd::SET_HEARTBEAT_MS, 1, 0},
    {"SET_DIR", Cmd::SET_DIR, 1, 0},              // bit0 invert rotation, bit1 invert linear
    {"JOG", Cmd::JOG, 1, 2},                      // signed mm, READY only
};
constexpr uint8_t kTableLen = sizeof(kTable) / sizeof(kTable[0]);

char upper(char c) { return (c >= 'a' && c <= 'z') ? (char)(c - 32) : c; }

Entry entry(uint8_t i) {
  Entry e;
  SF_MEMCPY_P(&e, &kTable[i], sizeof(Entry));
  return e;
}

}  // namespace

uint8_t valueScale(Cmd c) {
  for (uint8_t i = 0; i < kTableLen; ++i) {
    Entry e = entry(i);
    if (e.cmd == c) return e.scale;
  }
  return 0;
}

char* cmdName(Cmd c, char* buf, uint8_t len) {
  buf[0] = '\0';
  for (uint8_t i = 0; i < kTableLen; ++i) {
    Entry e = entry(i);
    if (e.cmd == c) {
      strncpy(buf, e.name, len - 1);
      buf[len - 1] = '\0';
      return buf;
    }
  }
  strncpy(buf, "INVALID", len - 1);
  buf[len - 1] = '\0';
  return buf;
}

bool parseFixed(const char* s, uint8_t scale, int32_t& out) {
  bool neg = false;
  if (*s == '+' || *s == '-') {
    neg = (*s == '-');
    ++s;
  }
  int64_t v = 0;
  uint8_t digits = 0, frac = 0;
  bool dot = false;
  for (; *s; ++s) {
    if (*s == '.') {
      if (dot) return false;
      dot = true;
      continue;
    }
    if (*s < '0' || *s > '9') return false;
    if (dot) {
      if (frac >= scale) continue;   // extra decimals are truncated
      ++frac;
    }
    v = v * 10 + (*s - '0');
    if (++digits > 12) return false;
  }
  if (digits == 0) return false;
  while (frac < scale) {
    v *= 10;
    ++frac;
  }
  if (v > 2000000000LL) return false;
  out = (int32_t)(neg ? -v : v);
  return true;
}

char* formatFixed(int32_t value, uint8_t scale, char* buf, uint8_t buflen) {
  char tmp[16];
  uint8_t n = 0;
  bool neg = value < 0;
  uint32_t v = neg ? (uint32_t)(-(int64_t)value) : (uint32_t)value;
  // emit digits in reverse, inserting the decimal point
  uint8_t produced = 0;
  do {
    if (scale && produced == scale) tmp[n++] = '.';
    tmp[n++] = (char)('0' + v % 10);
    v /= 10;
    ++produced;
  } while ((v || produced <= scale) && n < sizeof(tmp) - 2);
  if (neg) tmp[n++] = '-';
  uint8_t j = 0;
  while (n && j < buflen - 1) buf[j++] = tmp[--n];
  buf[j] = '\0';
  return buf;
}

bool parseLine(char* line, Command& out) {
  out = Command();
  // trim
  while (*line == ' ' || *line == '\t') ++line;
  char* end = line + strlen(line);
  while (end > line && (end[-1] == ' ' || end[-1] == '\t' || end[-1] == '\r' || end[-1] == '\n')) *--end = '\0';
  if (!*line) return false;
  char* eq = strchr(line, '=');
  char* value = nullptr;
  if (eq) {
    *eq = '\0';
    value = eq + 1;
    // trim around '='
    char* ke = eq;
    while (ke > line && (ke[-1] == ' ' || ke[-1] == '\t')) *--ke = '\0';
    while (*value == ' ' || *value == '\t') ++value;
  }
  for (char* p = line; *p; ++p) *p = upper(*p);
  for (uint8_t i = 0; i < kTableLen; ++i) {
    Entry e = entry(i);
    if (strcmp(line, e.name) != 0) continue;
    if (e.needs_value && !value) return false;
    if (!e.needs_value && value) return false;
    out.cmd = e.cmd;
    if (value) {
      if (!parseFixed(value, e.scale, out.value)) {
        out.cmd = Cmd::INVALID;
        return false;
      }
      out.has_value = true;
    }
    return true;
  }
  // Legacy R3 alias with different units: STEP_US=<master interval us> -> SET_RATE
  if (strcmp(line, "STEP_US") == 0 && value) {
    int32_t us;
    if (!parseFixed(value, 0, us) || us <= 0) return false;
    // R3 used a 3200 usteps/rev rotation master: rpm = 60e6 / (us * 3200)
    out.cmd = Cmd::SET_RATE;
    out.has_value = true;
    out.value = (int32_t)((6000000000LL / ((int64_t)us * 3200) + 5) / 10);  // rpm x10
    return true;
  }
  return false;
}

}  // namespace sf
