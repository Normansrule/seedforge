// Small dependency-free drivers for the Uno build (no third-party libraries,
// so CI can compile with only the Arduino AVR core).
#pragma once
#if defined(ARDUINO)
#include <Arduino.h>

namespace sf {

// HX711 24-bit load-cell ADC, channel A gain 128, bit-banged.
class Hx711 {
 public:
  void begin(uint8_t dout, uint8_t sck);
  bool present() const { return present_; }
  // Non-blocking: returns true and fills raw when a conversion is ready.
  bool poll(int32_t& raw);
 private:
  uint8_t dout_ = 0, sck_ = 0;
  bool present_ = false;
  uint32_t t_last_ready_ = 0;
};

// PCA9685 16-channel PWM at 50 Hz for hobby servos (I2C 0x40).
class Pca9685 {
 public:
  bool begin(uint8_t addr = 0x40);
  void writeMicros(uint8_t ch, uint16_t us);
  void allOff();                      // ALL_LED_OFF full-off bit: outputs low, servos receive no pulses
  bool present() const { return present_; }
 private:
  void write8(uint8_t reg, uint8_t v);
  uint8_t addr_ = 0x40;
  bool present_ = false;
};

// ICM-20948 accelerometer only (I2C 0x69 SparkFun default; 0x68 if AD0 low).
// Used as a machine-health signal: RMS of |a| deviation over a window.
class Icm20948 {
 public:
  bool begin(uint8_t addr = 0x69);
  bool present() const { return present_; }
  // Sample at ~200 Hz from loop(); returns true when a new RMS window (64 samples) completes.
  bool poll(uint16_t& rms_mg);
 private:
  bool readAccel(int16_t& x, int16_t& y, int16_t& z);
  uint8_t addr_ = 0x69;
  bool present_ = false;
  uint32_t t_last_ = 0;
  uint8_t n_ = 0;
  int32_t sum_ = 0;
  int32_t sumsq_ = 0;
};

}  // namespace sf
#endif
