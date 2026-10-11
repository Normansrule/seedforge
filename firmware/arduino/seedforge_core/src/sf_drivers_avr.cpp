#if defined(ARDUINO)
#include "sf_drivers_avr.h"

#include <Wire.h>

namespace sf {

namespace {
uint16_t isqrt32(uint32_t v) {        // integer square root (avoids the float library)
  uint32_t r = 0, bit = 1UL << 30;
  while (bit > v) bit >>= 2;
  while (bit) {
    if (v >= r + bit) { v -= r + bit; r = (r >> 1) + bit; }
    else r >>= 1;
    bit >>= 2;
  }
  return (uint16_t)r;
}
}  // namespace

// ------------------------------------------------------------------ HX711
void Hx711::begin(uint8_t dout, uint8_t sck) {
  dout_ = dout;
  sck_ = sck;
  pinMode(dout_, INPUT);
  pinMode(sck_, OUTPUT);
  digitalWrite(sck_, LOW);
  // A connected HX711 pulls DOUT low within ~100 ms of power-up (10 SPS mode: 100 ms period).
  uint32_t t0 = millis();
  while (millis() - t0 < 600) {
    if (digitalRead(dout_) == LOW) { present_ = true; break; }
  }
  t_last_ready_ = millis();
}

bool Hx711::poll(int32_t& raw) {
  if (digitalRead(dout_) != LOW) {
    if (millis() - t_last_ready_ > 1000) present_ = false;   // stale: unplugged or powered down
    return false;
  }
  uint32_t v = 0;
  // 24 data bits MSB first + 1 pulse selects channel A / gain 128 for the next reading.
  // SCK high must stay < 60 us (else power-down); keep interrupts on for the step ISR,
  // whose worst case is a few microseconds.
  for (uint8_t i = 0; i < 25; ++i) {
    digitalWrite(sck_, HIGH);
    delayMicroseconds(1);
    if (i < 24) v = (v << 1) | (digitalRead(dout_) == HIGH ? 1u : 0u);
    digitalWrite(sck_, LOW);
    delayMicroseconds(1);
  }
  if (v & 0x800000UL) v |= 0xFF000000UL;   // sign-extend 24-bit two's complement
  raw = (int32_t)v;
  present_ = true;
  t_last_ready_ = millis();
  return true;
}

// ------------------------------------------------------------------ PCA9685
void Pca9685::write8(uint8_t reg, uint8_t v) {
  Wire.beginTransmission(addr_);
  Wire.write(reg);
  Wire.write(v);
  Wire.endTransmission();
}

bool Pca9685::begin(uint8_t addr) {
  addr_ = addr;
  Wire.beginTransmission(addr_);
  present_ = Wire.endTransmission() == 0;
  if (!present_) return false;
  write8(0x00, 0x10);                 // MODE1: sleep (required to set prescale)
  write8(0xFE, 121);                  // prescale = round(25 MHz / (4096 * 50 Hz)) - 1 = 121
  write8(0x00, 0x20);                 // wake, auto-increment
  delay(1);
  write8(0x01, 0x04);                 // MODE2: totem-pole outputs
  return true;
}

void Pca9685::writeMicros(uint8_t ch, uint16_t us) {
  if (!present_ || ch > 15) return;
  // 50 Hz -> 20000 us per 4096 counts
  uint16_t off = (uint16_t)(((uint32_t)us * 4096UL) / 20000UL);
  Wire.beginTransmission(addr_);
  Wire.write((uint8_t)(0x06 + 4 * ch));
  Wire.write(0);
  Wire.write(0);
  Wire.write((uint8_t)(off & 0xFF));
  Wire.write((uint8_t)(off >> 8));
  Wire.endTransmission();
}

void Pca9685::allOff() {
  if (!present_) return;
  write8(0xFC, 0);                    // ALL_LED_OFF_L
  write8(0xFD, 0x10);                 // ALL_LED_OFF_H: full off on every channel
}

// ------------------------------------------------------------------ ICM-20948 (accelerometer only)
bool Icm20948::begin(uint8_t addr) {
  addr_ = addr;
  Wire.beginTransmission(addr_);
  Wire.write(0x7F); Wire.write(0x00);           // REG_BANK_SEL = bank 0
  if (Wire.endTransmission() != 0) { present_ = false; return false; }
  Wire.beginTransmission(addr_); Wire.write(0x00); Wire.endTransmission(false);   // WHO_AM_I
  Wire.requestFrom(addr_, (uint8_t)1);
  present_ = Wire.available() && Wire.read() == 0xEA;
  if (!present_) return false;
  Wire.beginTransmission(addr_); Wire.write(0x06); Wire.write(0x01); Wire.endTransmission();   // PWR_MGMT_1: wake, auto clock
  delay(20);
  // Accelerometer full scale left at power-on default (+-2 g, 16384 LSB/g).
  return true;
}

bool Icm20948::readAccel(int16_t& x, int16_t& y, int16_t& z) {
  Wire.beginTransmission(addr_);
  Wire.write(0x2D);                             // ACCEL_XOUT_H (bank 0)
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(addr_, (uint8_t)6) != 6) return false;
  x = (int16_t)((Wire.read() << 8) | Wire.read());
  y = (int16_t)((Wire.read() << 8) | Wire.read());
  z = (int16_t)((Wire.read() << 8) | Wire.read());
  return true;
}

bool Icm20948::poll(uint16_t& rms_mg) {
  if (!present_ || millis() - t_last_ < 5) return false;
  t_last_ = millis();
  int16_t x, y, z;
  if (!readAccel(x, y, z)) return false;
  // magnitude in mg (16384 LSB/g); deviation statistics over 64 samples:
  // rms = sqrt( sum((a_i - mean)^2) / N )
  uint32_t sq = (uint32_t)((int32_t)x * x) + (uint32_t)((int32_t)y * y) + (uint32_t)((int32_t)z * z);
  int32_t m = (int32_t)(((uint32_t)isqrt32(sq) * 1000UL) >> 14) - 1000;   // mg deviation from 1 g
  sum_ += m;
  sumsq_ += m * m;
  if (++n_ < 64) return false;
  // rms = sqrt( sum((a_i - mean)^2) / N ) = sqrt( E[a^2] - mean^2 )
  int32_t mean = sum_ / n_;
  int32_t var = sumsq_ / n_ - mean * mean;
  rms_mg = var > 0 ? isqrt32((uint32_t)var) : 0;
  n_ = 0; sum_ = 0; sumsq_ = 0;
  return true;
}

}  // namespace sf
#endif
