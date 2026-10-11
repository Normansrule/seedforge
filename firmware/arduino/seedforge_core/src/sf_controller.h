// SeedForge core finite-state machine (Uno).  Pure C++: hardware access goes
// through the Hal interface so the identical logic runs in tests/firmware.
//
//   BOOT -> HOME -> READY -> PRETENSION -> WIND -> VERIFY -> [CLAMP -> CUT -> DEMOLD] -> COMPLETE
//   any unsafe condition -> SAFE_STOP (latched; leave only with RESET, which returns to BOOT)
//
// Software stops SUPPLEMENT the physical E-stop, which must remove actuator
// power on its own (see docs/safety.md).  This is research-prototype firmware,
// not safety-rated software.
#pragma once
#include <stdint.h>

#include "sf_motion.h"
#include "sf_protocol.h"

namespace sf {

enum class State : uint8_t { BOOT, HOME, READY, PRETENSION, WIND, VERIFY, CLAMP, CUT, DEMOLD, COMPLETE, SAFE_STOP, COUNT_ };

enum class Fault : uint8_t {
  NONE, ESTOP_OPEN, END_LIMIT, HOME_LIMIT, LIMIT_WIRING, SOFT_LIMIT, TENSION_HIGH, LOADCELL,
  PRETENSION_TIMEOUT, HOME_TIMEOUT, SKIPPED_STEPS, HEARTBEAT_TIMEOUT, VISION_TIMEOUT, VISION_GAP,
  VISION_OVERLAP, VISION_LENGTH, VISION_TAIL, VISION_CAMERA, COMM_ERRORS, GUARD_OPEN, VIBRATION,
  REMOTE_STOP, LOCAL_STOP, COUNT_
};

// Recipe values are fixed point integers; defaults are DEVELOPMENT STARTING
// VALUES ONLY.  None of them has been validated on wet veneer.
struct Recipe {
  int32_t pitch_um = 4084;          // axial pitch per mandrel revolution (R3 dev value: pi*(0.8+0.5) mm)
  int32_t active_turns = 7;
  int32_t sacrificial_turns = 1;
  int32_t rate_rpm_x10 = 300;       // 30.0 mandrel rev/min
  int32_t accel_rpm_s_x10 = 300;    // 30.0 rev/min per second
  int32_t start_um = 5000;          // carriage start, mm from home x1000 (carriage x = 50 mm)
  int32_t tension_set_mN = 0;       // 0 = not configured (load cell not calibrated)
  int32_t tension_max_mN = 0;       // hard trip; 0 = disabled
  int32_t tension_min_mN = 0;       // pretension acceptance
  int32_t require_tension = 0;
  int32_t require_vision = 1;
  int32_t m3_enabled = 0;           // clamp/cut/demold hardware installed (Phase 2)
  int32_t demold_um = 20000;        // signed relative linear move during DEMOLD
  int32_t heartbeat_ms = 3000;
  int32_t dir_bits = 0;             // bit0 invert rotation, bit1 invert linear
};

struct Inputs {
  uint32_t now_ms = 0;
  bool estop_ok = false;            // E-stop auxiliary NC loop closed
  bool home_active = false;         // NC switch open = actuated (or broken wire)
  bool end_active = false;
  bool start_pressed = false;       // debounced falling edge this loop
  bool guard_ok = true;             // cutter guard closed (true if no guard switch fitted)
  bool tension_valid = false;       // HX711 present and calibrated
  bool tension_new = false;         // a new sample arrived this loop
  int32_t tension_mN = 0;           // latest unfiltered sample
  uint16_t vibration_mg = 0;        // IMU acceleration RMS (0 if not fitted)
  uint16_t dancer_raw = 0;          // A0 dancer potentiometer, 0-1023 (reported, not used for control)
};

class Hal {
 public:
  virtual void enableDrivers(bool on) = 0;
  virtual void setDirections(bool rot_positive, bool lin_positive) = 0;
  virtual void servo(uint8_t channel, uint16_t pulse_us) = 0;
  virtual void servosOff() = 0;                     // stop all PWM outputs (servos go limp, no pulses)
  virtual void emit(const char* line) = 0;          // one protocol line, no terminator
  virtual void tare() = 0;
  virtual bool calibrate(int32_t known_mN) = 0;
  virtual ~Hal() {}
};

// Servo pulse widths (us). STARTING VALUES: tune for your linkage before use.
constexpr uint16_t SERVO_CLAMP_OPEN = 1100, SERVO_CLAMP_CLOSED = 1600;
constexpr uint16_t SERVO_CUT_REST = 1000, SERVO_CUT_STROKE = 1800;
constexpr uint16_t SERVO_SUPPORT_OPEN = 1100, SERVO_SUPPORT_CLOSED = 1500;
constexpr uint32_t SERVO_DWELL_MS = 700;
constexpr uint32_t VISION_VERIFY_TIMEOUT_MS = 15000;
constexpr uint32_t PRETENSION_TIMEOUT_MS = 15000;
constexpr uint32_t PRETENSION_HOLD_MS = 300;
constexpr uint32_t LOADCELL_STALE_MS = 500;
constexpr int32_t HOME_BACKOFF_UM = 2000;
constexpr int32_t HOME_CLEAR_UM = 3000;
constexpr int32_t SKIP_TOLERANCE_UM = 300;       // home re-check tolerance
constexpr uint8_t SKIP_FAULT_COUNT = 2;           // consecutive re-check failures -> SAFE_STOP
constexpr uint8_t COMM_ERROR_LIMIT = 5;           // malformed lines in COMM_WINDOW_MS while moving
constexpr uint32_t COMM_WINDOW_MS = 2000;
constexpr uint16_t VIB_DERATE_MG = 0;             // 0 = disabled until characterised
constexpr uint16_t VIB_TRIP_MG = 0;

class Controller {
 public:
  explicit Controller(Hal& hal) : hal_(hal) {}
  void begin(uint32_t now_ms);
  void handleLine(char* line, uint32_t now_ms);
  void handle(const Command& c, uint32_t now_ms);
  void step(const Inputs& in);

  Motion& motion() { return motion_; }
  State state() const { return state_; }
  Fault fault() const { return fault_; }
  bool homed() const { return homed_; }
  const Recipe& recipe() const { return recipe_; }
  uint16_t turnsDone() const;
  uint32_t linTargetSteps() const;
  void emitStatus();

  static void stateName(State s, char* buf, uint8_t len);
  static void faultName(Fault f, char* buf, uint8_t len);

 private:
  enum class Phase : uint8_t { NONE, CLEAR, SEEK, BACKOFF, POSITION, WAIT, RUN, DWELL1, DWELL2, DWELL3, RETRACT, RELEASE };
  void enter(State s);
  void safeStop(Fault f);
  void emitKV(const char* key_P, int32_t v, uint8_t scale);
  void emitText(const char* key_P, const char* text);
  void error(const char* code_P);
  bool settable() const;
  bool applySetter(const Command& c);
  void beginCycle();
  void startPositionMove(int32_t target_um, uint32_t hz);
  uint32_t masterHz() const;
  void checkSafety(const Inputs& in);
  void runState(const Inputs& in);

  Hal& hal_;
  Motion motion_;
  Recipe recipe_;
  State state_ = State::BOOT;
  Fault fault_ = Fault::NONE;
  Phase phase_ = Phase::NONE;
  bool homed_ = false;
  bool cycle_pending_ = false;
  bool home_check_ = false;
  uint8_t skip_strikes_ = 0;
  uint32_t t_enter_ = 0, t_phase_ = 0, t_hb_ = 0, t_last_ = 0, t_tension_ok_ = 0, t_tension_seen_ = 0;
  uint32_t t_report_ = 0;
  uint16_t last_turn_ = 0;
  uint16_t wound_turns_ = 0;         // captured at the end of WIND (later moves reset counters)
  uint32_t wound_lin_steps_ = 0;
  uint8_t tension_strikes_ = 0;
  uint8_t comm_errors_ = 0;
  uint32_t t_comm_window_ = 0;
  int32_t last_length_mm_x100_ = -1;
  int32_t tension_mN_ = 0;
  bool tension_valid_ = false;
  Inputs last_in_;
};

}  // namespace sf
