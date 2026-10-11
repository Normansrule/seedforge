// Scenario runner for the C++ controller core on the virtual plant.
// Reads a scenario script (software/seedforge/simulator/scenarios/*.txt) and prints every emitted
// protocol line as "<ms> <line>".  Used to cross-check the pure-Python
// simulator (software/seedforge/simulator) against the real firmware logic.
//
//   step <ms>                 advance time
//   until <STATE> <ms>        advance until state reached (or timeout)
//   send <protocol line>      host -> controller
//   press                     START button falling edge
//   set <key> <int>           plant: estop, home_dead, home_stuck, end_forced, guard,
//                             tension_valid, tension_mN, hb_period_ms, auto_vision_ok,
//                             drift_per_cycle, phys_steps
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

#include "plant.h"

using namespace sf;

static bool stateFromName(const std::string& n, State& out) {
  for (uint8_t i = 0; i < (uint8_t)State::COUNT_; ++i) {
    char b[16];
    Controller::stateName((State)i, b, sizeof b);
    if (n == b) { out = (State)i; return true; }
  }
  return false;
}

int main(int argc, char** argv) {
  std::istream* in = &std::cin;
  std::ifstream f;
  if (argc > 1) { f.open(argv[1]); if (!f) { fprintf(stderr, "cannot open %s\n", argv[1]); return 2; } in = &f; }
  Plant p;
  size_t printed = 0;
  auto flush = [&]() {
    for (; printed < p.hal.lines.size(); ++printed) printf("%u %s\n", p.now_ms, p.hal.lines[printed].c_str());
  };
  p.begin();
  flush();
  std::string line;
  while (std::getline(*in, line)) {
    if (line.empty() || line[0] == '#') continue;
    std::istringstream ss(line);
    std::string op;
    ss >> op;
    if (op == "step") {
      uint32_t ms; ss >> ms;
      for (uint32_t i = 0; i < ms; ++i) { p.stepMs(1); flush(); }
    } else if (op == "until") {
      std::string s; uint32_t ms; ss >> s >> ms;
      State target;
      if (!stateFromName(s, target)) { fprintf(stderr, "bad state %s\n", s.c_str()); return 2; }
      for (uint32_t i = 0; i < ms && p.ctrl.state() != target; ++i) { p.stepMs(1); flush(); }
    } else if (op == "send") {
      std::string rest; std::getline(ss, rest);
      size_t a = rest.find_first_not_of(' ');
      p.send(a == std::string::npos ? "" : rest.substr(a));
      flush();
    } else if (op == "press") {
      p.start_press = true;
    } else if (op == "set") {
      std::string k; long v; ss >> k >> v;
      if (k == "estop") p.estop_ok = v;
      else if (k == "home_dead") p.home_dead = v;
      else if (k == "home_stuck") p.home_stuck = v;
      else if (k == "end_forced") p.end_forced = v;
      else if (k == "guard") p.guard_ok = v;
      else if (k == "tension_valid") p.tension_valid = v;
      else if (k == "tension_mN") p.tension_mN = (int32_t)v;
      else if (k == "hb_period_ms") p.hb_period_ms = (uint32_t)v;
      else if (k == "auto_vision_ok") p.auto_vision_ok = v;
      else if (k == "drift_per_cycle") p.drift_per_cycle = v;
      else if (k == "phys_steps") p.phys_steps = v;
      else { fprintf(stderr, "bad key %s\n", k.c_str()); return 2; }
    } else {
      fprintf(stderr, "bad op %s\n", op.c_str());
      return 2;
    }
  }
  flush();
  return 0;
}
