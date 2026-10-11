// Host unit tests for the SeedForge Uno controller core.
// Build & run: make -C tests/firmware   (or: g++ -std=c++17 ... see Makefile)
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <random>
#include <string>

#include "plant.h"

using namespace sf;

static int g_fail = 0, g_pass = 0;
#define CHECK(cond)                                                              \
  do {                                                                           \
    if (cond) { ++g_pass; }                                                      \
    else { ++g_fail; fprintf(stderr, "FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond); } \
  } while (0)
#define TEST(name) static void name()

static std::string st(const Plant& p) { char b[16]; Controller::stateName(p.ctrl.state(), b, sizeof b); return b; }
static std::string ft(const Plant& p) { char b[24]; Controller::faultName(p.ctrl.fault(), b, sizeof b); return b; }

// ------------------------------------------------------------------ protocol
TEST(protocol_parse) {
  Command c;
  char a[] = "  start ";
  CHECK(parseLine(a, c) && c.cmd == Cmd::START && !c.has_value);
  char b[] = "SET_PITCH=4.084";
  CHECK(parseLine(b, c) && c.cmd == Cmd::SET_PITCH && c.value == 4084);
  char b2[] = "set_pitch = 19.85";
  CHECK(parseLine(b2, c) && c.value == 19850);
  char d[] = "PITCH=5";                       // R3 alias
  CHECK(parseLine(d, c) && c.cmd == Cmd::SET_PITCH && c.value == 5000);
  char e[] = "STEP_US=1500";                  // R3 alias -> 12.5 rpm
  CHECK(parseLine(e, c) && c.cmd == Cmd::SET_RATE && c.value == 125);
  char f[] = "LENGTH_MM=35.25";
  CHECK(parseLine(f, c) && c.cmd == Cmd::LENGTH_MM && c.value == 3525);
  char g[] = "SET_DEMOLD=-40";
  CHECK(parseLine(g, c) && c.value == -4000);
  char h[] = "EMERGENCY_STOP";
  CHECK(parseLine(h, c) && c.cmd == Cmd::STOP);
  char i1[] = "START=1";                      // value not allowed
  CHECK(!parseLine(i1, c));
  char i2[] = "SET_PITCH";                    // value required
  CHECK(!parseLine(i2, c));
  char i3[] = "SET_PITCH=4.0.1";
  CHECK(!parseLine(i3, c));
  char i4[] = "SET_PITCH=abc";
  CHECK(!parseLine(i4, c));
  char i5[] = "WIBBLE";
  CHECK(!parseLine(i5, c));
  char i6[] = "";
  CHECK(!parseLine(i6, c));
  char i7[] = "SET_PITCH=99999999999";
  CHECK(!parseLine(i7, c));
  char j[] = "SET_PITCH=4.08449";             // extra decimals truncated
  CHECK(parseLine(j, c) && c.value == 4084);
}

TEST(protocol_format) {
  char buf[16];
  CHECK(std::string(formatFixed(4084, 3, buf, sizeof buf)) == "4.084");
  CHECK(std::string(formatFixed(-50, 2, buf, sizeof buf)) == "-0.50");
  CHECK(std::string(formatFixed(7, 0, buf, sizeof buf)) == "7");
  CHECK(std::string(formatFixed(5, 3, buf, sizeof buf)) == "0.005");
  CHECK(std::string(formatFixed(0, 2, buf, sizeof buf)) == "0.00");
  for (int32_t v : {0, 1, -1, 999, 1000, 123456, -98765}) {
    char s[20]; formatFixed(v, 3, s, sizeof s);
    int32_t back; CHECK(parseFixed(s, 3, back) && back == v);
  }
}

// ------------------------------------------------------------------ motion
static void runMotion(uint32_t rot, uint32_t lin) {
  Motion m;
  m.startSync(rot, lin, true, 4000, 20000);
  uint32_t ticks = 0, rs = 0, ls = 0;
  double max_err = 0;
  uint32_t master = rot >= lin ? rot : lin, slave = rot >= lin ? lin : rot;
  while (m.running()) {
    uint8_t b = m.tick();
    ++ticks;
    bool ms = rot >= lin ? (b & STEP_ROT) : (b & STEP_LIN);
    CHECK(ms);                                   // master steps every tick
    if (b & STEP_ROT) ++rs;
    if (b & STEP_LIN) ++ls;
    double ideal = (double)ticks * slave / master;
    double got = rot >= lin ? ls : rs;
    if (fabs(got - ideal) > max_err) max_err = fabs(got - ideal);
  }
  CHECK(rs == rot);
  CHECK(ls == lin);
  CHECK(m.rotDone() == rot && m.linDone() == lin);
  CHECK(max_err <= 1.0 + 1e-9);                  // slave never more than one step from the ideal line
  CHECK(m.finished());
}

TEST(motion_exact_totals) {
  runMotion(8 * 3200, 13069);      // 4.084 mm pitch, 8 turns
  runMotion(8 * 3200, 63520);      // 19.85 mm pitch: linear axis is master
  runMotion(3200, 0);
  runMotion(0, 800);
  runMotion(1, 1);
  std::mt19937 rng(149);
  for (int k = 0; k < 200; ++k) runMotion(rng() % 50000, rng() % 50000);
}

TEST(motion_ramp) {
  Motion m;
  m.startSync(32000, 13069, true, 3200, 6400);
  // simulate 1 ms updates and ISR ticks
  double acc = 0; uint32_t peak = 0; int t = 0;
  while (m.running() && t < 60000) {
    m.update(1000);
    acc += 1000;
    while (m.running() && acc >= m.intervalUs()) { acc -= m.intervalUs(); m.tick(); }
    if (m.rateHz() > peak) peak = m.rateHz();
    ++t;
  }
  CHECK(!m.running() && m.rotDone() == 32000 && m.linDone() == 13069);
  CHECK(peak == 3200);                           // reached but never exceeded cruise
  CHECK(t > 32000 * 1000 / 3200);                // took longer than the ideal no-ramp time
}

// ------------------------------------------------------------------ controller scenarios
static void homeAndReady(Plant& p) {
  p.begin();
  CHECK(st(p) == "BOOT");
  p.send("HOME");
  CHECK(p.runUntil(State::READY, 60000));
  CHECK(p.ctrl.homed());
  CHECK(!p.hal.enabled);                          // drivers off while idle
}

TEST(normal_cycle_phase1) {
  Plant p;
  p.hb_period_ms = 500;
  p.auto_vision_ok = true;
  homeAndReady(p);
  p.send("SET_PITCH=4.084");
  p.send("SET_TURNS=7");
  p.send("SET_SACRIFICIAL=1");
  CHECK(p.hal.saw("OK=SET_PITCH"));
  int64_t rot0 = p.phys_rot;
  p.send("START");
  CHECK(p.runUntil(State::PRETENSION));
  CHECK(p.runUntil(State::WIND));
  CHECK(p.runUntil(State::COMPLETE, 200000));
  p.stepMs(2);
  CHECK(p.hal.saw("TURN=8"));
  CHECK(p.phys_rot - rot0 == 8 * 3200);           // exact commanded turns
  CHECK(p.hal.sawPrefix("COMPLETE turns=8 lin_steps=13069"));
  CHECK(!p.hal.enabled);
  // second cycle performs the home re-check
  p.send("START");
  CHECK(p.runUntil(State::COMPLETE, 200000));
  CHECK(p.hal.sawPrefix("HOME_ERROR_MM=0.00"));
}

TEST(estop_during_wind) {
  Plant p; p.hb_period_ms = 500;
  homeAndReady(p);
  p.send("START");
  CHECK(p.runUntil(State::WIND));
  p.stepMs(300);
  p.estop_ok = false;
  p.stepMs(1);
  CHECK(st(p) == "SAFE_STOP" && ft(p) == "ESTOP_OPEN");
  CHECK(!p.hal.enabled && !p.ctrl.motion().running());
  p.send("RESET");                                // refused while loop open
  CHECK(st(p) == "SAFE_STOP" && p.hal.saw("ERROR=ESTOP_STILL_OPEN"));
  p.stepMs(10);
  p.estop_ok = true;
  p.stepMs(1);
  p.send("START");                                // START is not a reset
  CHECK(st(p) == "SAFE_STOP");
  p.send("RESET");
  CHECK(st(p) == "BOOT" && !p.ctrl.homed());       // must re-home
}

TEST(tension_high_trip) {
  Plant p; p.hb_period_ms = 500;
  p.tension_valid = true; p.tension_mN = 200;
  homeAndReady(p);
  p.send("SET_TENSION_MAX=0.500");
  p.send("SET_TENSION_MIN=0.100");
  p.send("SET_REQUIRE_TENSION=1");
  p.send("START");
  CHECK(p.runUntil(State::WIND));
  p.stepMs(200);
  CHECK(st(p) == "WIND");
  p.tension_mN = 650;
  p.stepMs(40);
  CHECK(st(p) == "SAFE_STOP" && ft(p) == "TENSION_HIGH");
  p.send("RESET");
  CHECK(p.hal.saw("ERROR=TENSION_STILL_HIGH"));
}

TEST(tension_single_glitch_ignored) {
  Plant p; p.hb_period_ms = 500; p.tension_valid = true; p.tension_mN = 200;
  homeAndReady(p);
  p.send("SET_TENSION_MAX=0.500");
  p.send("START");
  CHECK(p.runUntil(State::WIND));
  // one sample above the limit followed by normal samples: no trip
  p.tension_mN = 900; p.stepMs(12); p.tension_mN = 200; p.stepMs(100);
  CHECK(st(p) == "WIND");
}

TEST(pretension_timeout_and_loadcell) {
  Plant p; p.hb_period_ms = 500; p.tension_valid = true; p.tension_mN = 10;
  homeAndReady(p);
  p.send("SET_TENSION_MAX=0.5"); p.send("SET_TENSION_MIN=0.1"); p.send("SET_REQUIRE_TENSION=1");
  p.send("START");
  CHECK(p.runUntil(State::SAFE_STOP, 40000));
  CHECK(ft(p) == "PRETENSION_TIMEOUT");
  Plant q; q.hb_period_ms = 500;
  homeAndReady(q);
  q.send("SET_TENSION_MAX=0.5"); q.send("SET_REQUIRE_TENSION=1");
  q.send("START");                                 // no calibrated load cell
  CHECK(q.hal.saw("ERROR=TENSION_NOT_CONFIGURED") && st(q) == "READY");
}

TEST(vision_faults) {
  const char* faults[] = {"FAULT_GAP", "FAULT_OVERLAP", "FAULT_LENGTH", "FAULT_TAIL", "FAULT_CAMERA"};
  const char* names[] = {"VISION_GAP", "VISION_OVERLAP", "VISION_LENGTH", "VISION_TAIL", "VISION_CAMERA"};
  for (int k = 0; k < 5; ++k) {
    Plant p; p.hb_period_ms = 500;
    homeAndReady(p);
    p.send("START");
    CHECK(p.runUntil(State::VERIFY, 200000));
    p.send(faults[k]);
    CHECK(st(p) == "SAFE_STOP" && ft(p) == names[k]);
  }
  Plant p; p.hb_period_ms = 500;                  // faults are honoured even while idle
  homeAndReady(p);
  p.send("fault_gap");
  CHECK(st(p) == "SAFE_STOP");
}

TEST(heartbeat_timeout) {
  Plant p; p.hb_period_ms = 500;
  homeAndReady(p);
  p.send("START");
  CHECK(p.runUntil(State::WIND));
  p.hb_period_ms = 0;                             // host vision process dies
  CHECK(p.runUntil(State::SAFE_STOP, 5000));
  CHECK(ft(p) == "HEARTBEAT_TIMEOUT");
  Plant q; q.hb_period_ms = 500;                  // VERIFY is also vision-critical
  homeAndReady(q);
  q.send("START");
  CHECK(q.runUntil(State::VERIFY, 200000));
  q.hb_period_ms = 0;
  CHECK(q.runUntil(State::SAFE_STOP, 5000) && ft(q) == "HEARTBEAT_TIMEOUT");
}

TEST(vision_bypass_and_timeout) {
  Plant p;                                        // no host at all
  homeAndReady(p);
  p.send("SET_REQUIRE_VISION=0");
  p.send("START");
  CHECK(p.runUntil(State::COMPLETE, 200000));
  CHECK(p.hal.saw("EVENT=VISION_BYPASSED"));
  Plant q; q.hb_period_ms = 500;
  homeAndReady(q);
  q.send("START");
  CHECK(q.runUntil(State::VERIFY, 200000));
  CHECK(q.runUntil(State::SAFE_STOP, 20000) && ft(q) == "VISION_TIMEOUT");
}

TEST(home_faults) {
  Plant p; p.home_dead = true;                    // switch never trips
  p.begin(); p.send("HOME");
  CHECK(p.runUntil(State::SAFE_STOP, 200000) && ft(p) == "HOME_TIMEOUT");
  Plant q; q.home_stuck = true; q.phys_steps = 4000;  // switch stuck active
  q.begin(); q.send("HOME");
  CHECK(q.runUntil(State::SAFE_STOP, 60000) && ft(q) == "HOME_LIMIT");
  Plant r; r.begin(); r.end_forced = true; r.phys_steps = 0;  // both NC loops open
  r.stepMs(2);
  CHECK(st(r) == "SAFE_STOP" && ft(r) == "LIMIT_WIRING");
}

TEST(end_limit_unexpected) {
  Plant p; p.hb_period_ms = 500;
  homeAndReady(p);
  p.send("START");
  CHECK(p.runUntil(State::WIND));
  p.end_forced = true;
  p.stepMs(2);
  CHECK(st(p) == "SAFE_STOP" && ft(p) == "END_LIMIT");
}

TEST(skipped_steps_detected) {
  Plant p; p.hb_period_ms = 500; p.auto_vision_ok = true;
  p.drift_per_cycle = 800;                        // 2 mm lost per cycle
  homeAndReady(p);
  p.send("START"); CHECK(p.runUntil(State::COMPLETE, 200000));
  p.send("START"); CHECK(p.runUntil(State::COMPLETE, 200000) || st(p) == "SAFE_STOP");
  CHECK(p.hal.saw("ERROR=HOME_DRIFT"));
  p.send("START");
  CHECK(p.runUntil(State::SAFE_STOP, 200000) && ft(p) == "SKIPPED_STEPS");
}

TEST(m3_sequence) {
  Plant p; p.hb_period_ms = 500; p.auto_vision_ok = true;
  homeAndReady(p);
  p.send("SET_M3=1");
  p.send("SET_DEMOLD=20");
  p.send("START");
  CHECK(p.runUntil(State::CLAMP, 200000));
  CHECK(p.runUntil(State::CUT));
  CHECK(p.runUntil(State::DEMOLD));
  int64_t before = p.phys_steps;
  CHECK(p.runUntil(State::COMPLETE, 60000));
  CHECK(p.phys_steps - before == 8000);           // 20 mm relative retraction
  p.stepMs(2);
  CHECK(p.hal.sawPrefix("COMPLETE turns=8 lin_steps=13069"));   // demold move must not clobber the report
  // clamp close, cut stroke, cut rest, support close, support open, clamp open
  std::vector<std::pair<int, int>> want = {{CH_CLAMP, SERVO_CLAMP_CLOSED}, {CH_CUTTER, SERVO_CUT_STROKE},
                                           {CH_CUTTER, SERVO_CUT_REST}, {CH_DEMOLD_SUPPORT, SERVO_SUPPORT_CLOSED},
                                           {CH_DEMOLD_SUPPORT, SERVO_SUPPORT_OPEN}, {CH_CLAMP, SERVO_CLAMP_OPEN}};
  CHECK(p.hal.servos == want);
}

TEST(guard_open_during_cut) {
  Plant p; p.hb_period_ms = 500; p.auto_vision_ok = true;
  homeAndReady(p);
  p.send("SET_M3=1");
  p.send("START");
  CHECK(p.runUntil(State::CUT, 200000));
  p.guard_ok = false; p.stepMs(1);
  CHECK(st(p) == "SAFE_STOP" && ft(p) == "GUARD_OPEN");
  // SAFE_STOP switches every servo output off, so the cutter is not held at its stroke and
  // nothing moves when power returns after the E-stop is released.
  CHECK(!p.hal.servos.empty() && p.hal.servos.back().first == -1);
}

TEST(setters_and_guards) {
  Plant p; p.hb_period_ms = 500;
  homeAndReady(p);
  p.send("SET_PITCH=0.1");  CHECK(p.hal.saw("ERROR=OUT_OF_RANGE"));
  p.send("SET_TURNS=0");
  p.send("SET_RATE=500");
  CHECK(p.ctrl.recipe().pitch_um == 4084 && p.ctrl.recipe().active_turns == 7);
  p.send("SET_START=140");  CHECK(p.hal.saw("ERROR=OUT_OF_RANGE"));
  p.send("SET_START=60");  p.send("SET_PITCH=10");     // 60 + 80 > 100
  p.send("START");
  CHECK(p.hal.saw("ERROR=RECIPE_TRAVEL") && st(p) == "READY");
  p.send("SET_START=5");
  p.send("SET_PITCH=8");                          // 5 + 8 x 8 = 69 mm: inside the 75 mm soft limit
  p.send("START");
  CHECK(p.runUntil(State::WIND));
  p.hal.lines.clear();
  p.send("SET_PITCH=5");                          // refused while winding
  CHECK(p.hal.saw("ERROR=BUSY") && p.ctrl.recipe().pitch_um == 8000);
  p.send("VISION_OK");                            // not verifying
  CHECK(p.hal.saw("ERROR=UNEXPECTED_VISION_OK") && st(p) == "WIND");
}

TEST(comm_errors_while_moving) {
  Plant p; p.hb_period_ms = 500;
  homeAndReady(p);
  p.send("START");
  CHECK(p.runUntil(State::WIND));
  for (int i = 0; i < 5; ++i) p.send("GARBAGE#");
  CHECK(st(p) == "SAFE_STOP" && ft(p) == "COMM_ERRORS");
}

TEST(button_behaviour) {
  Plant p; p.hb_period_ms = 500;
  p.begin();
  p.start_press = true; p.stepMs(1);              // BOOT: button = HOME
  CHECK(st(p) == "HOME");
  CHECK(p.runUntil(State::READY, 60000));
  p.start_press = true; p.stepMs(1);              // READY: button = START
  CHECK(p.runUntil(State::WIND));
  p.start_press = true; p.stepMs(1);              // moving: button = stop
  CHECK(st(p) == "SAFE_STOP" && ft(p) == "LOCAL_STOP");
  p.start_press = true; p.stepMs(1);              // SAFE_STOP: button = RESET (no motion)
  CHECK(st(p) == "BOOT" && !p.hal.enabled);
}

TEST(jog_and_stop) {
  Plant p;
  homeAndReady(p);
  p.send("JOG=10");
  p.stepMs(5000);
  CHECK(p.hal.saw("POSITION=12.00"));
  p.send("JOG=-50");
  CHECK(p.hal.saw("ERROR=JOG_RANGE"));
  p.send("STOP");
  CHECK(st(p) == "SAFE_STOP" && ft(p) == "REMOTE_STOP");
}

TEST(direction_inversion) {
  Plant p; p.hb_period_ms = 500; p.auto_vision_ok = true;
  p.begin();
  p.send("SET_DIR=2");                            // linear motor wired reversed
  p.send("HOME");
  CHECK(p.runUntil(State::READY, 60000));         // homing still finds the switch
  p.send("START");
  CHECK(p.runUntil(State::COMPLETE, 200000));
}

int main() {
  protocol_parse();
  protocol_format();
  motion_exact_totals();
  motion_ramp();
  normal_cycle_phase1();
  estop_during_wind();
  tension_high_trip();
  tension_single_glitch_ignored();
  pretension_timeout_and_loadcell();
  vision_faults();
  heartbeat_timeout();
  vision_bypass_and_timeout();
  home_faults();
  end_limit_unexpected();
  skipped_steps_detected();
  m3_sequence();
  guard_open_during_cut();
  setters_and_guards();
  comm_errors_while_moving();
  button_behaviour();
  jog_and_stop();
  direction_inversion();
  printf("%d checks passed, %d failed\n", g_pass, g_fail);
  return g_fail ? 1 : 0;
}
