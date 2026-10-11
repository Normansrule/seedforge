// Synchronized two-axis step generator (integer Bresenham / DDA).
//
// The axis with more microsteps in a move is the master.  Every master tick
// advances the slave accumulator by slave_total; whenever it reaches
// master_total the slave steps once.  Therefore:
//   * the slave never steps more than once per master tick,
//   * after N master ticks the slave has stepped floor(N * slave/master) times,
//   * at the end both axes have produced exactly their commanded totals.
// Timing jitter (late interrupts, serial blocking) changes speed, never the
// ratio between the axes: the commanded helix pitch is preserved.
//
// Pure C++ (no Arduino headers) so it can be unit-tested on a PC.
#pragma once
#include <stdint.h>

namespace sf {

enum StepBits : uint8_t { STEP_NONE = 0, STEP_ROT = 1, STEP_LIN = 2 };

class Motion {
 public:
  // Synchronized move. rot_total/lin_total in microsteps. Rates in master-axis Hz.
  void startSync(uint32_t rot_total, uint32_t lin_total, bool lin_positive,
                 uint32_t cruise_hz, uint32_t accel_hz_per_s);
  // Linear-only move (homing, positioning, demold retraction).
  void startLinear(uint32_t lin_total, bool lin_positive, uint32_t cruise_hz, uint32_t accel_hz_per_s);
  void stop();                       // immediate stop (safety path)

  // Called from the timer ISR at the current interval. Returns StepBits to pulse.
  uint8_t tick();
  // Called from the main loop roughly every millisecond: updates the ramped rate.
  void update(uint32_t dt_us);

  bool running() const { return running_; }
  bool finished() const { return finished_; }
  void clearFinished() { finished_ = false; }
  uint32_t intervalUs() const { return interval_us_; }
  uint32_t rateHz() const { return rate_hz_; }
  uint32_t rotDone() const;          // atomic reads (32-bit values shared with the ISR)
  uint32_t linDone() const;
  uint32_t rotTotal() const { return rot_total_; }
  uint32_t linTotal() const { return lin_total_; }
  int32_t linPos() const;           // signed microsteps from home
  void setLinPos(int32_t p);
  bool linPositive() const { return lin_positive_; }
  void scaleCruise(uint16_t permille);              // tension/vibration trim (500..1000)

 private:
  void begin(uint32_t master_total, uint32_t cruise_hz, uint32_t accel);
  volatile bool running_ = false;
  volatile bool finished_ = false;
  bool rot_is_master_ = true;
  bool lin_positive_ = true;
  uint32_t rot_total_ = 0, lin_total_ = 0;
  uint32_t master_total_ = 0, slave_total_ = 0;
  volatile uint32_t master_done_ = 0;
  volatile uint32_t rot_done_ = 0, lin_done_ = 0;
  uint32_t acc_ = 0;
  volatile int32_t lin_pos_ = 0;
  uint32_t cruise_hz_ = 0, base_cruise_hz_ = 0, accel_ = 0;
  uint32_t rate_hz_ = 0;            // current master rate
  uint32_t rate_frac_ = 0;          // sub-Hz accumulator (Hz * 1e6)
  volatile uint32_t interval_us_ = 1000;
};

}  // namespace sf
