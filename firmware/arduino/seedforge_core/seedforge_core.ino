/*
  SeedForge core controller - Arduino Uno (ATmega328P)

  Deterministic synchronized winding (Timer1 Bresenham step generator),
  homing, limits, E-stop feedback, HX711 tension trip, PCA9685 servos for
  clamp/cut/demold, optional ICM-20948 vibration RMS, and the line protocol in
  docs/protocol.md on USB serial (115200) and on the ESP32-C3 link
  (SoftwareSerial A1 RX / A2 TX, 38400, A2 through a 1k/2k divider).

  STATUS: Compile-tested; hardware testing pending.
  This is research-prototype firmware, not safety-rated software. The
  physical E-stop must remove actuator power independently of this code.

  SPDX-License-Identifier: MIT
*/
#include <EEPROM.h>
#include <SoftwareSerial.h>
#include <Wire.h>

#include "src/sf_config.h"
#include "src/sf_controller.h"
#include "src/sf_drivers_avr.h"

using namespace sf;

// Declared before any function so Arduino's generated prototypes can see it.
struct LineBuf {
  char buf[64];
  uint8_t len = 0;
  bool overflow = false;   // line longer than buf: discarded whole, reported as BAD_COMMAND
};

// Set to true only when a cutter-guard NC switch is wired to A3.
static const bool GUARD_FITTED = false;

SoftwareSerial Link(PIN_LINK_RX, PIN_LINK_TX);
Hx711 hx;
Pca9685 pca;
Icm20948 imu;

struct Cal {
  uint16_t magic;
  int32_t offset;
  int32_t counts_per_N;   // HX711 counts per newton
};
static Cal cal;
static const uint16_t CAL_MAGIC = 0x5346;   // "SF"
static int32_t last_raw = 0;
static uint16_t dancer = 0;
static uint32_t t_dancer = 0;

class UnoHal : public Hal {
 public:
  void enableDrivers(bool on) override { digitalWrite(PIN_ENABLE, on ? LOW : HIGH); }
  void setDirections(bool rot_level, bool lin_level) override {
    digitalWrite(PIN_ROT_DIR, rot_level ? HIGH : LOW);
    digitalWrite(PIN_LIN_DIR, lin_level ? HIGH : LOW);
    delayMicroseconds(2);   // A4988 DIR setup time before the next STEP edge
  }
  void servo(uint8_t ch, uint16_t us) override { pca.writeMicros(ch, us); }
  void servosOff() override { pca.allOff(); }
  void emit(const char* line) override {
    Serial.println(line);
    Link.println(line);
  }
  void tare() override {
    cal.offset = averageRaw();
    if (cal.magic != CAL_MAGIC) cal.counts_per_N = 0;   // tare alone does not make the cell valid: CAL_TENSION does
    cal.magic = CAL_MAGIC;
    EEPROM.put(0, cal);
  }
  bool calibrate(int32_t known_mN) override {
    int32_t raw = averageRaw();
    int64_t counts = (int64_t)(raw - cal.offset) * 1000 / known_mN;
    if (counts == 0 || cal.magic != CAL_MAGIC) return false;   // TARE first
    cal.counts_per_N = (int32_t)counts;
    EEPROM.put(0, cal);
    return true;
  }
 private:
  int32_t averageRaw() {
    int64_t sum = 0;
    uint8_t n = 0;
    uint32_t t0 = millis();
    while (n < 8 && millis() - t0 < 2000) {
      int32_t r;
      if (hx.poll(r)) { sum += r; ++n; }
    }
    return n ? (int32_t)(sum / n) : last_raw;
  }
};

UnoHal hal;
Controller ctrl(hal);

// ------------------------------------------------------------------ step ISR
ISR(TIMER1_COMPA_vect) {
  uint8_t bits = ctrl.motion().tick();
  if (bits) {
    uint8_t mask = ((bits & STEP_ROT) ? _BV(2) : 0) | ((bits & STEP_LIN) ? _BV(4) : 0);   // D2, D4
    PORTD |= mask;
    __builtin_avr_delay_cycles(32);   // 2 us high (A4988 minimum 1 us)
    PORTD &= (uint8_t)~mask;
  }
  uint32_t iv = ctrl.motion().intervalUs();
  OCR1A = (uint16_t)(iv * 2 - 1);     // prescaler 8 -> 0.5 us per count
}

static void timerBegin() {
  noInterrupts();
  TCCR1A = 0;
  TCCR1B = _BV(WGM12) | _BV(CS11);    // CTC, clk/8
  OCR1A = 1999;
  TCNT1 = 0;
  TIMSK1 = _BV(OCIE1A);
  interrupts();
}

// ------------------------------------------------------------------ line input
static LineBuf usb_in, link_in;

static void pollStream(Stream& s, LineBuf& lb) {
  while (s.available()) {
    char c = (char)s.read();
    if (c == '\n' || c == '\r') {
      if (lb.overflow) {
        char bad[] = "!";             // never a valid command: counted as BAD_COMMAND / comm error
        ctrl.handleLine(bad, millis());
      } else if (lb.len) {
        lb.buf[lb.len] = '\0';
        ctrl.handleLine(lb.buf, millis());
      }
      lb.len = 0;
      lb.overflow = false;
    } else if (c >= 32 && c <= 126 && !lb.overflow) {
      if (lb.len < sizeof(lb.buf) - 1) lb.buf[lb.len++] = c;
      else lb.overflow = true;        // overlong line: the whole line is discarded, never its tail
    }
  }
}

void setup() {
  pinMode(PIN_ROT_STEP, OUTPUT);
  pinMode(PIN_LIN_STEP, OUTPUT);
  pinMode(PIN_ROT_DIR, OUTPUT);
  pinMode(PIN_LIN_DIR, OUTPUT);
  pinMode(PIN_ENABLE, OUTPUT);
  digitalWrite(PIN_ENABLE, HIGH);     // drivers disabled before anything else
  pinMode(PIN_START, INPUT_PULLUP);
  pinMode(PIN_ESTOP_FB, ESTOP_SENSE_RAIL ? INPUT : INPUT_PULLUP);   // rail sense: the divider pulls down
  pinMode(PIN_HOME, INPUT_PULLUP);
  pinMode(PIN_END, INPUT_PULLUP);
  pinMode(PIN_GUARD, INPUT_PULLUP);
  pinMode(PIN_LED, OUTPUT);

  Serial.begin(USB_BAUD);
  Link.begin(LINK_BAUD);
  Wire.begin();
  Wire.setClock(400000);
  Wire.setWireTimeout(3000, true);    // never hang the loop on a stuck I2C bus

  EEPROM.get(0, cal);
  if (cal.magic != CAL_MAGIC) { cal.magic = 0; cal.offset = 0; cal.counts_per_N = 0; }
  hx.begin(PIN_HX_DOUT, PIN_HX_SCK);
  pca.begin(0x40);
  if (!imu.begin(0x69)) imu.begin(0x68);

  ctrl.begin(millis());
  timerBegin();
}

void loop() {
  static uint32_t t_btn = 0;
  static bool btn_prev = HIGH;
  static uint16_t vib = 0;
  static uint32_t t_led = 0;

  // Sample inputs and run the state machine first, so that commands parsed
  // below are always judged against fresh E-stop/limit readings.
  Inputs in;
  in.now_ms = millis();
  in.estop_ok = ESTOP_SENSE_RAIL ? digitalRead(PIN_ESTOP_FB) == HIGH : digitalRead(PIN_ESTOP_FB) == LOW;
  in.home_active = digitalRead(PIN_HOME) == HIGH;
  in.end_active = digitalRead(PIN_END) == HIGH;
  in.guard_ok = GUARD_FITTED ? digitalRead(PIN_GUARD) == LOW : true;

  bool b = digitalRead(PIN_START);
  if (btn_prev == HIGH && b == LOW && in.now_ms - t_btn > 50) { in.start_pressed = true; t_btn = in.now_ms; }
  btn_prev = b;

  int32_t raw;
  if (hx.poll(raw)) {
    last_raw = raw;
    in.tension_new = true;
  }
  in.tension_valid = hx.present() && cal.magic == CAL_MAGIC && cal.counts_per_N != 0;
  in.tension_mN = in.tension_valid ? (int32_t)((int64_t)(last_raw - cal.offset) * 1000 / cal.counts_per_N) : 0;
  if (imu.present()) imu.poll(vib);
  in.vibration_mg = vib;
  if (in.now_ms - t_dancer >= 20) { t_dancer = in.now_ms; dancer = (uint16_t)analogRead(PIN_DANCER); }
  in.dancer_raw = dancer;

  ctrl.step(in);

  pollStream(Serial, usb_in);
  pollStream(Link, link_in);

  // Status LED: solid = SAFE_STOP, fast blink = moving, slow blink = waiting.
  State s = ctrl.state();
  uint16_t period = s == State::SAFE_STOP ? 0 : (ctrl.motion().running() ? 150 : 800);
  if (!period) digitalWrite(PIN_LED, HIGH);
  else if (in.now_ms - t_led >= period) { t_led = in.now_ms; digitalWrite(PIN_LED, !digitalRead(PIN_LED)); }
}
