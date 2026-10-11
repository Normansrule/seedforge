#include "sf_motion.h"

#include "sf_config.h"
#include "sf_platform.h"

namespace sf {

void Motion::begin(uint32_t master_total, uint32_t cruise_hz, uint32_t accel) {
  if (cruise_hz > MAX_MASTER_HZ) cruise_hz = MAX_MASTER_HZ;
  if (cruise_hz < MIN_MASTER_HZ) cruise_hz = MIN_MASTER_HZ;
  if (accel == 0) accel = 1;
  master_total_ = master_total;
  master_done_ = 0;
  rot_done_ = 0;
  lin_done_ = 0;
  acc_ = master_total / 2;            // centre the error term (symmetric rounding)
  cruise_hz_ = base_cruise_hz_ = cruise_hz;
  accel_ = accel;
  rate_hz_ = MIN_MASTER_HZ;
  rate_frac_ = 0;
  interval_us_ = 1000000UL / rate_hz_;
  finished_ = false;
  running_ = master_total > 0;
  if (!running_) finished_ = true;
}

void Motion::startSync(uint32_t rot_total, uint32_t lin_total, bool lin_positive,
                       uint32_t cruise_hz, uint32_t accel_hz_per_s) {
  SF_ATOMIC_BEGIN
  running_ = false;
  rot_total_ = rot_total;
  lin_total_ = lin_total;
  lin_positive_ = lin_positive;
  rot_is_master_ = rot_total >= lin_total;
  slave_total_ = rot_is_master_ ? lin_total : rot_total;
  begin(rot_is_master_ ? rot_total : lin_total, cruise_hz, accel_hz_per_s);
  SF_ATOMIC_END
}

void Motion::startLinear(uint32_t lin_total, bool lin_positive, uint32_t cruise_hz, uint32_t accel_hz_per_s) {
  SF_ATOMIC_BEGIN
  running_ = false;
  rot_total_ = 0;
  lin_total_ = lin_total;
  lin_positive_ = lin_positive;
  rot_is_master_ = false;
  slave_total_ = 0;
  begin(lin_total, cruise_hz, accel_hz_per_s);
  SF_ATOMIC_END
}

void Motion::stop() {
  SF_ATOMIC_BEGIN
  running_ = false;
  SF_ATOMIC_END
}

uint8_t Motion::tick() {
  if (!running_) return STEP_NONE;
  uint8_t bits = rot_is_master_ ? STEP_ROT : STEP_LIN;
  master_done_++;
  if (slave_total_) {
    acc_ += slave_total_;
    if (acc_ >= master_total_) {
      acc_ -= master_total_;
      bits |= rot_is_master_ ? STEP_LIN : STEP_ROT;
    }
  }
  if (bits & STEP_ROT) rot_done_++;
  if (bits & STEP_LIN) {
    lin_done_++;
    lin_pos_ += lin_positive_ ? 1 : -1;
  }
  if (master_done_ >= master_total_) {
    running_ = false;
    finished_ = true;
  }
  return bits;
}

void Motion::scaleCruise(uint16_t permille) {
  if (permille > 1000) permille = 1000;
  if (permille < 200) permille = 200;
  uint32_t c = (uint32_t)((uint64_t)base_cruise_hz_ * permille / 1000);
  if (c < MIN_MASTER_HZ) c = MIN_MASTER_HZ;
  cruise_hz_ = c;
}

void Motion::update(uint32_t dt_us) {
  uint32_t done, total;
  bool run;
  SF_ATOMIC_BEGIN
  done = master_done_;
  total = master_total_;
  run = running_;
  SF_ATOMIC_END
  if (!run) return;
  uint32_t remaining = total > done ? total - done : 0;
  // steps needed to decelerate from the current rate: v^2 / (2a)
  uint32_t stop_steps = (uint32_t)(((uint64_t)rate_hz_ * rate_hz_) / (2ULL * accel_)) + 1;
  // rate change this update, in Hz*1e6 units to keep sub-Hz resolution
  rate_frac_ += (uint64_t)accel_ * dt_us;
  uint32_t dv = rate_frac_ / 1000000UL;
  rate_frac_ %= 1000000UL;
  if (remaining <= stop_steps) {
    rate_hz_ = rate_hz_ > MIN_MASTER_HZ + dv ? rate_hz_ - dv : MIN_MASTER_HZ;
  } else if (rate_hz_ < cruise_hz_) {
    rate_hz_ = rate_hz_ + dv > cruise_hz_ ? cruise_hz_ : rate_hz_ + dv;
  } else if (rate_hz_ > cruise_hz_) {
    rate_hz_ = rate_hz_ > cruise_hz_ + dv ? rate_hz_ - dv : cruise_hz_;
  }
  uint32_t iv = 1000000UL / rate_hz_;
  SF_ATOMIC_BEGIN
  interval_us_ = iv;
  SF_ATOMIC_END
}

uint32_t Motion::rotDone() const {
  uint32_t v;
  SF_ATOMIC_BEGIN
  v = rot_done_;
  SF_ATOMIC_END
  return v;
}

uint32_t Motion::linDone() const {
  uint32_t v;
  SF_ATOMIC_BEGIN
  v = lin_done_;
  SF_ATOMIC_END
  return v;
}

int32_t Motion::linPos() const {
  int32_t v;
  SF_ATOMIC_BEGIN
  v = lin_pos_;
  SF_ATOMIC_END
  return v;
}

void Motion::setLinPos(int32_t p) {
  SF_ATOMIC_BEGIN
  lin_pos_ = p;
  SF_ATOMIC_END
}

}  // namespace sf
