#include "sf_controller.h"

#include <stdio.h>
#include <string.h>

#include "sf_config.h"
#include "sf_platform.h"

#if defined(__AVR__)
#include <avr/pgmspace.h>
#define SF_PROGMEM PROGMEM
#else
#define SF_PROGMEM
#endif

namespace sf {

#ifndef SF_FW_VERSION
#define SF_FW_VERSION "0.3.0-alpha"
#endif

namespace {
const char kStateNames[][12] SF_PROGMEM = {"BOOT", "HOME", "READY", "PRETENSION", "WIND", "VERIFY",
                                           "CLAMP", "CUT", "DEMOLD", "COMPLETE", "SAFE_STOP"};
const char kFaultNames[][20] SF_PROGMEM = {
    "NONE", "ESTOP_OPEN", "END_LIMIT", "HOME_LIMIT", "LIMIT_WIRING", "SOFT_LIMIT", "TENSION_HIGH",
    "LOADCELL", "PRETENSION_TIMEOUT", "HOME_TIMEOUT", "SKIPPED_STEPS", "HEARTBEAT_TIMEOUT",
    "VISION_TIMEOUT", "VISION_GAP", "VISION_OVERLAP", "VISION_LENGTH", "VISION_TAIL", "VISION_CAMERA",
    "COMM_ERRORS", "GUARD_OPEN", "VIBRATION", "REMOTE_STOP", "LOCAL_STOP"};

constexpr uint32_t POSITION_HZ = 2400;      // 6 mm/s positioning
constexpr uint32_t POSITION_ACCEL = 8000;
constexpr uint32_t DEMOLD_HZ = 800;         // 2 mm/s relative retraction
// Proportional speed trim on tension above setpoint (permille of cruise per newton).
// 0 = disabled. Do not enable before the wet-veneer tension window is measured.
constexpr int32_t TENSION_TRIM_PERMILLE_PER_N = 0;

int32_t umToSteps(int32_t um) { return (int32_t)(((int64_t)um * (int64_t)LIN_USTEPS_PER_MM + (um >= 0 ? 500 : -500)) / 1000); }
int32_t stepsToUm(int32_t st) { return (int32_t)(((int64_t)st * 1000) / (int64_t)LIN_USTEPS_PER_MM); }

bool movingState(State s) {
  return s == State::HOME || s == State::PRETENSION || s == State::WIND || s == State::VERIFY ||
         s == State::CLAMP || s == State::CUT || s == State::DEMOLD;
}
}  // namespace

void Controller::stateName(State s, char* buf, uint8_t len) {
  uint8_t i = (uint8_t)s < (uint8_t)State::COUNT_ ? (uint8_t)s : 0;
  sf_strncpy_P(buf, kStateNames[i], len - 1);
  buf[len - 1] = '\0';
}

void Controller::faultName(Fault f, char* buf, uint8_t len) {
  uint8_t i = (uint8_t)f < (uint8_t)Fault::COUNT_ ? (uint8_t)f : 0;
  sf_strncpy_P(buf, kFaultNames[i], len - 1);
  buf[len - 1] = '\0';
}

void Controller::emitKV(const char* key_P, int32_t v, uint8_t scale) {
  char line[48];
  char num[16];
  sf_strcpy_P(line, key_P);
  strcat(line, "=");
  strcat(line, formatFixed(v, scale, num, sizeof(num)));
  hal_.emit(line);
}

void Controller::emitText(const char* key_P, const char* text) {
  char line[48];
  sf_strcpy_P(line, key_P);
  strcat(line, "=");
  strncat(line, text, sizeof(line) - strlen(line) - 1);
  hal_.emit(line);
}

void Controller::error(const char* code_P) {
  char code[24];
  sf_strncpy_P(code, code_P, sizeof(code) - 1);
  code[sizeof(code) - 1] = '\0';
  emitText(SF_P("ERROR"), code);
}

void Controller::begin(uint32_t now_ms) {
  hal_.enableDrivers(false);
  t_last_ = t_hb_ = t_enter_ = t_report_ = now_ms;
  char banner[40];
  sf_strcpy_P(banner, SF_P("SEEDFORGE_CORE fw=" SF_FW_VERSION));
  hal_.emit(banner);
  enter(State::BOOT);
}

void Controller::enter(State s) {
  state_ = s;
  phase_ = Phase::NONE;
  t_enter_ = t_phase_ = last_in_.now_ms;
  char name[12];
  stateName(s, name, sizeof(name));
  emitText(SF_P("STATE"), name);
}

void Controller::safeStop(Fault f) {
  motion_.stop();
  hal_.enableDrivers(false);
  hal_.servosOff();               // no servo pulses until a sequence commands them again
  fault_ = f;
  cycle_pending_ = false;
  homed_ = false;                 // position is re-established by homing after RESET
  char name[20];
  faultName(f, name, sizeof(name));
  emitText(SF_P("FAULT"), name);
  if (state_ != State::SAFE_STOP) enter(State::SAFE_STOP);
}

uint16_t Controller::turnsDone() const { return (uint16_t)(motion_.rotDone() / ROT_USTEPS_PER_REV); }

uint32_t Controller::linTargetSteps() const {
  int64_t turns = recipe_.active_turns + recipe_.sacrificial_turns;
  return (uint32_t)(((int64_t)recipe_.pitch_um * LIN_USTEPS_PER_MM * turns + 500) / 1000);
}

uint32_t Controller::masterHz() const {
  uint32_t rot_total = (uint32_t)(recipe_.active_turns + recipe_.sacrificial_turns) * ROT_USTEPS_PER_REV;
  uint32_t lin_total = linTargetSteps();
  uint32_t rot_hz = (uint32_t)((int64_t)recipe_.rate_rpm_x10 * ROT_USTEPS_PER_REV / 600);
  if (lin_total > rot_total && rot_total) return (uint32_t)((uint64_t)rot_hz * lin_total / rot_total);
  return rot_hz;
}

void Controller::emitStatus() {
  char line[192];
  char a[12], b[20], p[16], t[16];
  stateName(state_, a, sizeof(a));
  faultName(fault_, b, sizeof(b));
  formatFixed(stepsToUm(motion_.linPos()) / 10, 2, p, sizeof(p));
  formatFixed(tension_mN_, 3, t, sizeof(t));
  SF_SNPRINTF(line, sizeof(line), "STATUS state=%s fault=%s homed=%u pos_mm=%s turn=%u tension_N=%s estop=%u home=%u end=%u dancer=%u vib_mg=%u",
           a, b, homed_ ? 1u : 0u, p, (unsigned)turnsDone(), tension_valid_ ? t : "nan",
           last_in_.estop_ok ? 1u : 0u, last_in_.home_active ? 1u : 0u, last_in_.end_active ? 1u : 0u,
           (unsigned)last_in_.dancer_raw, (unsigned)last_in_.vibration_mg);
  hal_.emit(line);
}

bool Controller::settable() const {
  return state_ == State::BOOT || state_ == State::READY || state_ == State::COMPLETE || state_ == State::SAFE_STOP;
}

bool Controller::applySetter(const Command& c) {
  int32_t v = c.value;
  auto in = [&](int32_t lo, int32_t hi) { return v >= lo && v <= hi; };
  switch (c.cmd) {
    case Cmd::SET_PITCH: if (!in(200, 30000)) return false; recipe_.pitch_um = v; break;
    case Cmd::SET_TURNS: if (!in(1, 40)) return false; recipe_.active_turns = v; break;
    case Cmd::SET_SACRIFICIAL: if (!in(0, 5)) return false; recipe_.sacrificial_turns = v; break;
    case Cmd::SET_RATE: if (!in(10, 3000)) return false; recipe_.rate_rpm_x10 = v; break;
    case Cmd::SET_ACCEL: if (!in(10, 30000)) return false; recipe_.accel_rpm_s_x10 = v; break;
    case Cmd::SET_START: if (!in(0, (int32_t)MAX_TRAVEL_UM / 10)) return false; recipe_.start_um = v * 10; break;
    case Cmd::SET_TENSION: if (!in(0, 9800)) return false; recipe_.tension_set_mN = v; break;
    case Cmd::SET_TENSION_MAX: if (!in(0, 9800)) return false; recipe_.tension_max_mN = v; break;
    case Cmd::SET_TENSION_MIN: if (!in(0, 9800)) return false; recipe_.tension_min_mN = v; break;
    case Cmd::SET_REQUIRE_TENSION: if (!in(0, 1)) return false; recipe_.require_tension = v; break;
    case Cmd::SET_REQUIRE_VISION: if (!in(0, 1)) return false; recipe_.require_vision = v; break;
    case Cmd::SET_M3: if (!in(0, 1)) return false; recipe_.m3_enabled = v; break;
    case Cmd::SET_DEMOLD: if (!in(-(int32_t)MAX_TRAVEL_UM / 10, (int32_t)MAX_TRAVEL_UM / 10)) return false; recipe_.demold_um = v * 10; break;
    case Cmd::SET_HEARTBEAT_MS: if (!in(200, 60000)) return false; recipe_.heartbeat_ms = v; break;
    case Cmd::SET_DIR: if (!in(0, 3)) return false; recipe_.dir_bits = v; break;
    default: return false;
  }
  return true;
}

void Controller::beginCycle() {
  // Travel pre-check: whole cycle must stay inside the soft limits.
  int64_t end_um = (int64_t)recipe_.start_um + (int64_t)recipe_.pitch_um * (recipe_.active_turns + recipe_.sacrificial_turns);
  int64_t demold_end = end_um + (recipe_.m3_enabled ? recipe_.demold_um : 0);
  if (end_um > (int64_t)MAX_TRAVEL_UM || demold_end > (int64_t)MAX_TRAVEL_UM || demold_end < 0) {
    error(SF_P("RECIPE_TRAVEL"));
    return;
  }
  if (recipe_.require_tension && (!tension_valid_ || recipe_.tension_max_mN <= 0)) {
    error(SF_P("TENSION_NOT_CONFIGURED"));
    return;
  }
  fault_ = Fault::NONE;
  cycle_pending_ = true;
  home_check_ = homed_;            // re-home every cycle; compare to expected zero
  hal_.enableDrivers(true);
  enter(State::HOME);
}

void Controller::startPositionMove(int32_t target_um, uint32_t hz) {
  int32_t delta = umToSteps(target_um) - motion_.linPos();
  bool pos = delta >= 0;
  hal_.setDirections(!(recipe_.dir_bits & 1), pos != ((recipe_.dir_bits & 2) != 0));
  motion_.startLinear((uint32_t)(pos ? delta : -delta), pos, hz, POSITION_ACCEL);
}

void Controller::handleLine(char* line, uint32_t now_ms) {
  Command c;
  if (!parseLine(line, c)) {
    if (now_ms - t_comm_window_ > COMM_WINDOW_MS) {
      t_comm_window_ = now_ms;
      comm_errors_ = 0;
    }
    ++comm_errors_;
    error(SF_P("BAD_COMMAND"));
    if (movingState(state_) && comm_errors_ >= COMM_ERROR_LIMIT) safeStop(Fault::COMM_ERRORS);
    return;
  }
  handle(c, now_ms);
}

void Controller::handle(const Command& c, uint32_t now_ms) {
  last_in_.now_ms = now_ms;
  char name[20];
  switch (c.cmd) {
    // Safety and fault events are honoured in every state (the original
    // EECS 149 sketch ignored EMERGENCY_STOP while paused; this does not).
    case Cmd::STOP: safeStop(Fault::REMOTE_STOP); return;
    case Cmd::FAULT_GAP: safeStop(Fault::VISION_GAP); return;
    case Cmd::FAULT_OVERLAP: safeStop(Fault::VISION_OVERLAP); return;
    case Cmd::FAULT_LENGTH: safeStop(Fault::VISION_LENGTH); return;
    case Cmd::FAULT_TAIL: safeStop(Fault::VISION_TAIL); return;
    case Cmd::FAULT_CAMERA: safeStop(Fault::VISION_CAMERA); return;
    case Cmd::HEARTBEAT: t_hb_ = now_ms; return;
    case Cmd::STATUS: emitStatus(); return;
    case Cmd::LENGTH_MM:
      last_length_mm_x100_ = c.value;
      emitKV(SF_P("LENGTH_MM"), c.value, 2);
      return;
    case Cmd::GET_RECIPE: {
      char line[176], a[16], b[16], d[16], e[16];
      SF_SNPRINTF(line, sizeof(line), "RECIPE pitch_mm=%s turns=%ld sacrificial=%ld rate_rpm=%s start_mm=%s tension_max_N=%s m3=%ld vision=%ld",
               formatFixed(recipe_.pitch_um, 3, a, sizeof(a)), (long)recipe_.active_turns, (long)recipe_.sacrificial_turns,
               formatFixed(recipe_.rate_rpm_x10, 1, b, sizeof(b)), formatFixed(recipe_.start_um / 10, 2, d, sizeof(d)),
               formatFixed(recipe_.tension_max_mN, 3, e, sizeof(e)), (long)recipe_.m3_enabled, (long)recipe_.require_vision);
      hal_.emit(line);
      return;
    }
    case Cmd::RESET:
      if (state_ != State::SAFE_STOP && state_ != State::COMPLETE && state_ != State::BOOT) { error(SF_P("BUSY")); return; }
      if (!last_in_.estop_ok) { error(SF_P("ESTOP_STILL_OPEN")); return; }
      if (recipe_.tension_max_mN > 0 && tension_valid_ && tension_mN_ > recipe_.tension_max_mN) { error(SF_P("TENSION_STILL_HIGH")); return; }
      fault_ = Fault::NONE;
      hal_.enableDrivers(false);
      enter(State::BOOT);
      return;
    case Cmd::HOME:
      if (state_ != State::BOOT && state_ != State::READY && state_ != State::COMPLETE) { error(SF_P("BUSY")); return; }
      if (!last_in_.estop_ok) { error(SF_P("ESTOP_OPEN")); return; }
      cycle_pending_ = false;
      home_check_ = false;
      hal_.enableDrivers(true);
      enter(State::HOME);
      return;
    case Cmd::START:
      if (state_ != State::READY && state_ != State::COMPLETE) { error(homed_ ? SF_P("BUSY") : SF_P("NOT_HOMED")); return; }
      if (!last_in_.estop_ok) { error(SF_P("ESTOP_OPEN")); return; }
      beginCycle();
      return;
    case Cmd::VISION_OK:
      if (state_ != State::VERIFY) { error(SF_P("UNEXPECTED_VISION_OK")); return; }
      enter(recipe_.m3_enabled ? State::CLAMP : State::COMPLETE);
      return;
    case Cmd::TARE:
      if (!settable()) { error(SF_P("BUSY")); return; }
      hal_.tare();
      emitText(SF_P("OK"), "TARE");
      return;
    case Cmd::CAL_TENSION:
      if (!settable()) { error(SF_P("BUSY")); return; }
      if (c.value <= 0 || !hal_.calibrate(c.value)) { error(SF_P("CAL_FAILED")); return; }
      emitText(SF_P("OK"), "CAL_TENSION");
      return;
    case Cmd::JOG: {
      if (state_ != State::READY || motion_.running()) { error(SF_P("NOT_READY")); return; }
      int32_t target = stepsToUm(motion_.linPos()) + c.value * 10;
      if (target < 0 || target > (int32_t)MAX_TRAVEL_UM) { error(SF_P("JOG_RANGE")); return; }
      hal_.enableDrivers(true);
      startPositionMove(target, POSITION_HZ);
      phase_ = Phase::RUN;
      return;
    }
    default:
      break;
  }
  // recipe setters
  if (!settable()) { error(SF_P("BUSY")); return; }
  if (!applySetter(c)) { error(SF_P("OUT_OF_RANGE")); return; }
  emitText(SF_P("OK"), cmdName(c.cmd, name, sizeof(name)));
}

void Controller::checkSafety(const Inputs& in) {
  if (state_ == State::SAFE_STOP) return;
  if (!in.estop_ok) { safeStop(Fault::ESTOP_OPEN); return; }
  if (in.home_active && in.end_active) { safeStop(Fault::LIMIT_WIRING); return; }
  if (motion_.running()) {
    bool pos = motion_.linPositive();
    bool lin_moving = motion_.linTotal() > 0;
    if (lin_moving && pos && in.end_active) { safeStop(Fault::END_LIMIT); return; }
    if (lin_moving && !pos && in.home_active && state_ != State::HOME) { safeStop(Fault::HOME_LIMIT); return; }
    if (stepsToUm(motion_.linPos()) > (int32_t)MAX_TRAVEL_UM && state_ != State::HOME) { safeStop(Fault::SOFT_LIMIT); return; }
  }
  // Tension: immediate trip on two consecutive raw samples above the limit,
  // independent of any filtering or speed trim.
  bool tension_state = state_ == State::PRETENSION || state_ == State::WIND || state_ == State::VERIFY ||
                       state_ == State::CLAMP || state_ == State::CUT || state_ == State::DEMOLD;
  if (recipe_.tension_max_mN > 0 && in.tension_valid && in.tension_new) {
    if (in.tension_mN > recipe_.tension_max_mN) {
      if (++tension_strikes_ >= 2 && tension_state) { safeStop(Fault::TENSION_HIGH); return; }
    } else {
      tension_strikes_ = 0;
    }
  }
  if (recipe_.require_tension && (state_ == State::PRETENSION || state_ == State::WIND)) {
    if (!in.tension_valid || (in.now_ms - t_tension_seen_) > LOADCELL_STALE_MS) { safeStop(Fault::LOADCELL); return; }
  }
  if (recipe_.require_vision && (state_ == State::WIND || state_ == State::VERIFY) &&
      (in.now_ms - t_hb_) > (uint32_t)recipe_.heartbeat_ms) {
    safeStop(Fault::HEARTBEAT_TIMEOUT);
    return;
  }
  if (VIB_TRIP_MG && in.vibration_mg > VIB_TRIP_MG && movingState(state_)) { safeStop(Fault::VIBRATION); return; }
  if (state_ == State::CUT && !in.guard_ok) { safeStop(Fault::GUARD_OPEN); return; }
}

void Controller::step(const Inputs& in) {
  uint32_t dt_ms = in.now_ms - t_last_;
  t_last_ = in.now_ms;
  last_in_ = in;
  if (in.tension_new) {
    t_tension_seen_ = in.now_ms;
    tension_mN_ = in.tension_mN;
  }
  tension_valid_ = in.tension_valid;
  motion_.update(dt_ms * 1000UL);

  if (in.start_pressed) {
    if (state_ == State::BOOT) {
      Command c; c.cmd = Cmd::HOME; handle(c, in.now_ms);
    } else if (state_ == State::READY || state_ == State::COMPLETE) {
      Command c; c.cmd = Cmd::START; handle(c, in.now_ms);
    } else if (state_ == State::SAFE_STOP) {
      Command c; c.cmd = Cmd::RESET; handle(c, in.now_ms);   // RESET never moves anything
    } else {
      safeStop(Fault::LOCAL_STOP);
    }
  }
  checkSafety(in);
  runState(in);
}

void Controller::runState(const Inputs& in) {
  uint32_t now = in.now_ms;
  switch (state_) {
    case State::BOOT:
    case State::SAFE_STOP:
      hal_.enableDrivers(false);
      if (now - t_report_ >= 1000) { t_report_ = now; emitStatus(); }
      break;

    case State::READY:
      if (phase_ == Phase::RUN && motion_.finished()) {          // jog complete
        motion_.clearFinished();
        phase_ = Phase::NONE;
        hal_.enableDrivers(false);
        emitKV(SF_P("POSITION"), stepsToUm(motion_.linPos()) / 10, 2);
      }
      if (now - t_report_ >= 1000 && !motion_.running()) { t_report_ = now; emitStatus(); }
      break;

    case State::HOME: {
      const int32_t max_steps = umToSteps((int32_t)MAX_TRAVEL_UM + 20000);
      if (phase_ == Phase::NONE) {
        if (in.home_active) {                                     // already on the switch: clear it first
          hal_.setDirections(true, !(recipe_.dir_bits & 2));
          motion_.startLinear((uint32_t)umToSteps(HOME_CLEAR_UM), true, HOMING_HZ / 2, POSITION_ACCEL);
          phase_ = Phase::CLEAR;
        } else {
          hal_.setDirections(true, (recipe_.dir_bits & 2) != 0);
          motion_.startLinear((uint32_t)max_steps, false, HOMING_HZ, POSITION_ACCEL);
          phase_ = Phase::SEEK;
        }
      } else if (phase_ == Phase::CLEAR && motion_.finished()) {
        motion_.clearFinished();
        if (in.home_active) { safeStop(Fault::HOME_LIMIT); break; }   // switch stuck
        phase_ = Phase::NONE;
      } else if (phase_ == Phase::SEEK) {
        if (in.home_active) {
          motion_.stop();
          int32_t err_um = stepsToUm(motion_.linPos());
          if (home_check_) {
            emitKV(SF_P("HOME_ERROR_MM"), err_um / 10, 2);
            if (err_um > SKIP_TOLERANCE_UM || err_um < -SKIP_TOLERANCE_UM) {
              if (++skip_strikes_ >= SKIP_FAULT_COUNT) { safeStop(Fault::SKIPPED_STEPS); break; }
              error(SF_P("HOME_DRIFT"));
            } else {
              skip_strikes_ = 0;
            }
          }
          motion_.setLinPos(0);
          hal_.setDirections(true, !(recipe_.dir_bits & 2));
          motion_.startLinear((uint32_t)umToSteps(HOME_BACKOFF_UM), true, HOMING_HZ / 2, POSITION_ACCEL);
          phase_ = Phase::BACKOFF;
        } else if (motion_.finished()) {
          motion_.clearFinished();
          safeStop(Fault::HOME_TIMEOUT);
        }
      } else if (phase_ == Phase::BACKOFF && motion_.finished()) {
        motion_.clearFinished();
        if (in.home_active) { safeStop(Fault::HOME_LIMIT); break; }
        homed_ = true;
        emitKV(SF_P("POSITION"), stepsToUm(motion_.linPos()) / 10, 2);
        if (cycle_pending_) {
          enter(State::PRETENSION);
        } else {
          hal_.enableDrivers(false);
          enter(State::READY);
        }
      }
      break;
    }

    case State::PRETENSION:
      if (phase_ == Phase::NONE) {
        hal_.enableDrivers(true);
        startPositionMove(recipe_.start_um, POSITION_HZ);
        phase_ = Phase::POSITION;
      } else if (phase_ == Phase::POSITION && motion_.finished()) {
        motion_.clearFinished();
        emitKV(SF_P("POSITION"), stepsToUm(motion_.linPos()) / 10, 2);
        phase_ = Phase::WAIT;
        t_phase_ = now;
        t_tension_ok_ = 0;
        if (!recipe_.require_tension) emitText(SF_P("EVENT"), "PRETENSION_SKIPPED");
      } else if (phase_ == Phase::WAIT) {
        bool ok = !recipe_.require_tension || (tension_valid_ && tension_mN_ >= recipe_.tension_min_mN);
        if (ok) {
          if (!t_tension_ok_) t_tension_ok_ = now ? now : 1;
          if (!recipe_.require_tension || now - t_tension_ok_ >= PRETENSION_HOLD_MS) {
            enter(State::WIND);
          }
        } else {
          t_tension_ok_ = 0;
          if (now - t_phase_ > PRETENSION_TIMEOUT_MS) safeStop(Fault::PRETENSION_TIMEOUT);
        }
      }
      break;

    case State::WIND:
      if (phase_ == Phase::NONE) {
        uint32_t rot_total = (uint32_t)(recipe_.active_turns + recipe_.sacrificial_turns) * ROT_USTEPS_PER_REV;
        uint32_t lin_total = linTargetSteps();
        uint32_t hz = masterHz();
        uint32_t rot_accel = (uint32_t)((int64_t)recipe_.accel_rpm_s_x10 * ROT_USTEPS_PER_REV / 600);
        uint32_t accel = lin_total > rot_total ? (uint32_t)((uint64_t)rot_accel * lin_total / rot_total) : rot_accel;
        wound_turns_ = 0;
        wound_lin_steps_ = 0;
        if (hz > MAX_MASTER_HZ) error(SF_P("RATE_CLAMPED"));
        hal_.setDirections(!(recipe_.dir_bits & 1), !(recipe_.dir_bits & 2));
        motion_.startSync(rot_total, lin_total, true, hz, accel);
        last_turn_ = 0;
        phase_ = Phase::RUN;
      } else if (phase_ == Phase::RUN) {
        uint16_t t = turnsDone();
        if (t != last_turn_) { last_turn_ = t; emitKV(SF_P("TURN"), t, 0); }
        if (recipe_.require_tension && now - t_report_ >= 500) { t_report_ = now; emitKV(SF_P("TENSION"), tension_mN_, 3); }
        if (TENSION_TRIM_PERMILLE_PER_N > 0 && recipe_.tension_set_mN > 0 && tension_valid_) {
          int32_t over = tension_mN_ - recipe_.tension_set_mN;
          int32_t pm = 1000 - (over > 0 ? over * TENSION_TRIM_PERMILLE_PER_N / 1000 : 0);
          motion_.scaleCruise((uint16_t)(pm < 500 ? 500 : pm));
        }
        if (VIB_DERATE_MG && in.vibration_mg > VIB_DERATE_MG) motion_.scaleCruise(600);
        if (motion_.finished()) {
          motion_.clearFinished();
          wound_turns_ = turnsDone();
          wound_lin_steps_ = motion_.linDone();
          emitKV(SF_P("POSITION"), stepsToUm(motion_.linPos()) / 10, 2);
          emitText(SF_P("EVENT"), "WIND_DONE");
          enter(State::VERIFY);
          if (!recipe_.require_vision) {
            emitText(SF_P("EVENT"), "VISION_BYPASSED");
            enter(recipe_.m3_enabled ? State::CLAMP : State::COMPLETE);
          }
        }
      }
      break;

    case State::VERIFY:
      if (now - t_enter_ > VISION_VERIFY_TIMEOUT_MS) safeStop(Fault::VISION_TIMEOUT);
      break;

    case State::CLAMP:
      if (phase_ == Phase::NONE) { hal_.servo(CH_CLAMP, SERVO_CLAMP_CLOSED); phase_ = Phase::DWELL1; t_phase_ = now; }
      else if (now - t_phase_ >= SERVO_DWELL_MS) enter(State::CUT);
      break;

    case State::CUT:
      if (phase_ == Phase::NONE) { hal_.servo(CH_CUTTER, SERVO_CUT_STROKE); phase_ = Phase::DWELL1; t_phase_ = now; }
      else if (phase_ == Phase::DWELL1 && now - t_phase_ >= SERVO_DWELL_MS) { hal_.servo(CH_CUTTER, SERVO_CUT_REST); phase_ = Phase::DWELL2; t_phase_ = now; }
      else if (phase_ == Phase::DWELL2 && now - t_phase_ >= SERVO_DWELL_MS) enter(State::DEMOLD);
      break;

    case State::DEMOLD:
      // 1 close compliant split support, 2 relative axial retraction, 3 open support, 4 release clamp
      if (phase_ == Phase::NONE) { hal_.servo(CH_DEMOLD_SUPPORT, SERVO_SUPPORT_CLOSED); phase_ = Phase::DWELL1; t_phase_ = now; }
      else if (phase_ == Phase::DWELL1 && now - t_phase_ >= SERVO_DWELL_MS) {
        startPositionMove(stepsToUm(motion_.linPos()) + recipe_.demold_um, DEMOLD_HZ);
        phase_ = Phase::RETRACT;
      } else if (phase_ == Phase::RETRACT && motion_.finished()) {
        motion_.clearFinished();
        hal_.servo(CH_DEMOLD_SUPPORT, SERVO_SUPPORT_OPEN);
        phase_ = Phase::DWELL2; t_phase_ = now;
      } else if (phase_ == Phase::DWELL2 && now - t_phase_ >= SERVO_DWELL_MS) {
        hal_.servo(CH_CLAMP, SERVO_CLAMP_OPEN);
        phase_ = Phase::DWELL3; t_phase_ = now;
      } else if (phase_ == Phase::DWELL3 && now - t_phase_ >= SERVO_DWELL_MS) {
        enter(State::COMPLETE);
      }
      break;

    case State::COMPLETE:
      if (phase_ == Phase::NONE) {
        hal_.enableDrivers(false);
        char line[96], p[12], l[12];
        SF_SNPRINTF(line, sizeof(line), "COMPLETE turns=%u lin_steps=%lu pitch_mm=%s length_mm=%s",
                 (unsigned)wound_turns_, (unsigned long)wound_lin_steps_, formatFixed(recipe_.pitch_um, 3, p, sizeof(p)),
                 last_length_mm_x100_ >= 0 ? formatFixed(last_length_mm_x100_, 2, l, sizeof(l)) : "nan");
        hal_.emit(line);
        phase_ = Phase::WAIT;
        last_length_mm_x100_ = -1;
      }
      if (now - t_report_ >= 1000) { t_report_ = now; emitStatus(); }
      break;

    default:
      break;
  }
}

}  // namespace sf
