// Virtual plant for host-testing the Uno controller core.
// Simulates the Timer1 ISR, a lead-screw carriage with NC home/end switches,
// an E-stop loop, a load cell and a vision host.  Time advances in 1 ms ticks.
#pragma once
#include <stdint.h>

#include <string>
#include <vector>

#include "../../firmware/arduino/seedforge_core/src/sf_config.h"
#include "../../firmware/arduino/seedforge_core/src/sf_controller.h"

struct FakeHal : sf::Hal {
  bool enabled = false;
  bool rot_level = true, lin_level = true;
  std::vector<std::string> lines;
  std::vector<std::pair<int, int>> servos;     // (channel, us) in order
  bool cal_ok = true;
  int tares = 0;
  void enableDrivers(bool on) override { enabled = on; }
  void setDirections(bool r, bool l) override { rot_level = r; lin_level = l; }
  void servo(uint8_t ch, uint16_t us) override { servos.push_back({ch, us}); }
  void servosOff() override { servos.push_back({-1, 0}); }
  void emit(const char* line) override { lines.push_back(line); }
  void tare() override { ++tares; }
  bool calibrate(int32_t) override { return cal_ok; }
  bool saw(const std::string& s) const {
    for (auto& l : lines) if (l == s) return true;
    return false;
  }
  bool sawPrefix(const std::string& s) const {
    for (auto& l : lines) if (l.compare(0, s.size(), s) == 0) return true;
    return false;
  }
};

struct Plant {
  FakeHal hal;
  sf::Controller ctrl{hal};
  uint32_t now_ms = 0;
  double isr_us = 0;               // time accumulated toward the next ISR
  // physical carriage position (microsteps from the home-switch trip point)
  int64_t phys_steps = 12000;      // start 30 mm out
  int64_t phys_rot = 0;
  int64_t end_steps = (int64_t)sf::LIN_USTEPS_PER_MM * 104;   // end switch 104 mm from home (x = 149)
  int64_t drift_per_cycle = 0;     // injected lost steps (skipped-step test)
  bool estop_ok = true;
  bool home_stuck = false, home_dead = false, end_forced = false;
  bool guard_ok = true;
  bool tension_valid = false;
  int32_t tension_mN = 0;
  uint32_t hb_period_ms = 0;       // auto heartbeat from "host"; 0 = none
  uint32_t t_hb = 0;
  bool auto_vision_ok = false;
  bool start_press = false;

  void begin() { ctrl.begin(now_ms); stepMs(1); }   // first loop() samples inputs

  bool homeActive() const { return home_stuck || (!home_dead && phys_steps <= 0); }
  bool endActive() const { return end_forced || phys_steps >= end_steps; }

  void send(const std::string& line) {
    std::string s = line;
    ctrl.handleLine(&s[0], now_ms);
  }

  void stepMs(uint32_t n = 1) {
    for (uint32_t k = 0; k < n; ++k) {
      // ISR activity during this millisecond
      isr_us += 1000.0;
      for (;;) {
        double iv = ctrl.motion().intervalUs();
        if (!ctrl.motion().running() || isr_us < iv) break;
        isr_us -= iv;
        uint8_t bits = ctrl.motion().tick();
        if (!hal.enabled) continue;  // disabled driver: pulses do nothing
        bool lin_pos_dir = hal.lin_level == !(ctrl.recipe().dir_bits & 2);
        if (bits & sf::STEP_LIN) phys_steps += lin_pos_dir ? 1 : -1;
        if (bits & sf::STEP_ROT) phys_rot += 1;
      }
      if (!ctrl.motion().running()) isr_us = 0;
      ++now_ms;
      if (hb_period_ms && now_ms - t_hb >= hb_period_ms) { t_hb = now_ms; send("HEARTBEAT"); }
      sf::Inputs in;
      in.now_ms = now_ms;
      in.estop_ok = estop_ok;
      in.home_active = homeActive();
      in.end_active = endActive();
      in.guard_ok = guard_ok;
      in.tension_valid = tension_valid;
      in.tension_new = tension_valid && (now_ms % 12 == 0);   // ~80 SPS HX711
      in.tension_mN = tension_mN;
      in.start_pressed = start_press;
      start_press = false;
      sf::State before = ctrl.state();
      ctrl.step(in);
      if (before == sf::State::WIND && ctrl.state() == sf::State::VERIFY && auto_vision_ok) send("VISION_OK");
      if (before != sf::State::COMPLETE && ctrl.state() == sf::State::COMPLETE) phys_steps -= drift_per_cycle;
    }
  }

  // Run until state equals s or timeout; returns true if reached.
  bool runUntil(sf::State s, uint32_t timeout_ms = 120000) {
    for (uint32_t t = 0; t < timeout_ms; ++t) {
      if (ctrl.state() == s) return true;
      stepMs(1);
    }
    return ctrl.state() == s;
  }
};
