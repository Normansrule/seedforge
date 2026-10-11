#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <SoftwareSerial.h>

// ---------- LCD ----------
LiquidCrystal_I2C lcd(0x27, 16, 2); // change to 0x3F if needed

// ---------- ESP32 link (UNO RX=12, UNO TX=11 but we only read) ----------
SoftwareSerial Link(12, 11);
static const unsigned long BAUD = 9600;

// ---------------- State Machine ----------------
enum State { STOP_FWD, RUN_FWD, STOP_BWD, RUN_BWD };
State state = STOP_FWD;

// Logic Pins:
const int dirPin = 2;
const int stepPin = 3;
const int dirPin2 = 6;
const int stepPin2 = 7;
const int buttonPin = 8;
#define TRIG_PIN 4
#define ECHO_PIN 5

// Ratio Logic
const int ratio_num = 5;
long ratio_acc = 0;

// Timing
unsigned long lastStepTime = 0;
const unsigned long stepRate = 400; // microseconds

const int ledPin = 13;

const unsigned long sensorInterval = 1000;
unsigned long previousSensorMillis = 0;

float distance = 100;
float dist = 0;

unsigned long lastBtn = 0;

// ---------------- Pause/Resume layer ----------------
// '1' = PAUSE (remember state)
// '0' = RESUME (return to remembered state)
bool paused = false;
State savedState = STOP_FWD;
char lastCmd = '\0'; // ignore repeats

// ---------------- LCD helpers ----------------
const char* stateLabel(State s) {
  switch (s) {
    case STOP_FWD: return "STOP_FWD";
    case RUN_FWD:  return "RUN_FWD";
    case STOP_BWD: return "STOP_BWD";
    case RUN_BWD:  return "RUN_BWD";
    default:       return "UNKNOWN";
  }
}

void lcdPrintLine(uint8_t row, String text) {
  if (text.length() > 16) text = text.substring(0, 16);
  while (text.length() < 16) text += ' ';
  lcd.setCursor(0, row);
  lcd.print(text);
}

void updateLCD(bool force=false) {
  static State lastShown = (State)255;
  static long lastMm = -1;
  static int lastP = -1;

  long mm = (long)(dist * 10.0f + 0.5f); // cm -> mm
  int p = paused ? 1 : 0;

  if (force || state != lastShown || p != lastP) {
    // ex: "RUN_FWD P:1"
    lcdPrintLine(0, String(stateLabel(state)) + " P:" + String(p));
    lastShown = state;
    lastP = p;
  }
  if (force || mm != lastMm) {
    lcdPrintLine(1, String("Dist:") + String(mm) + "mm");
    lastMm = mm;
  }
}

// Print only when state changes (prevents 9600 baud slowdown)
void setState(State s) {
  if (s == state) return;
  state = s;
  Serial.print("[STATE] ");
  Serial.println(stateLabel(state));
  updateLCD(true);
}

// ---------------- Your helpers ----------------
bool buttonPressed() {
  if (digitalRead(buttonPin) == LOW && millis() - lastBtn > 200) {
    lastBtn = millis();
    return true;
  }
  return false;
}

float getDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000UL);
  if (duration == 0) return distance;

  distance = duration * 0.034f / 2.0f;
  // distance print once per second is OK at 9600
  Serial.print("[DIST] ");
  Serial.print(distance);
  Serial.println(" cm");
  return distance;
}

inline void pulseStep(int pin) {
  digitalWrite(pin, HIGH);
  delayMicroseconds(2);   // helps many stepper drivers
  digitalWrite(pin, LOW);
}

void stepOnceAandRatio() {
  pulseStep(stepPin);

  ratio_acc += 1;
  while (ratio_acc >= ratio_num) {
    pulseStep(stepPin2);
    ratio_acc -= ratio_num;
  }
}

void stepOnceAandRatio_linear() {
  pulseStep(stepPin);
}

// ---------------- Command handling ----------------
// ONLY accepts '1' and '0'
void applyCmd(char c) {
  if (c == lastCmd) return;   // ignore repeats so it won’t spam
  lastCmd = c;

  if (c == '1') {             // PAUSE
    if (!paused) {
      savedState = state;
      paused = true;

      digitalWrite(ledPin, HIGH);     // UNO LED ON when paused (as requested)
      Serial.print("[CMD] PAUSE -> saved=");
      Serial.println(stateLabel(savedState));

      updateLCD(true);
    }
  } else if (c == '0') {      // RESUME
    if (paused) {
      paused = false;
      setState(savedState);           // restore previous state

      // Reset timers so it continues smoothly
      lastStepTime = micros();
      previousSensorMillis = millis();

      digitalWrite(ledPin, LOW);      // UNO LED OFF when running (as requested)
      Serial.println("[CMD] RESUME");

      updateLCD(true);
    }
  }
}

void pollESP32() {
  while (Link.available()) {
    char c = (char)Link.read();
    if (c == '1' || c == '0') applyCmd(c);
  }
}

void setup() {
  pinMode(dirPin, OUTPUT);
  pinMode(stepPin, OUTPUT);
  pinMode(dirPin2, OUTPUT);
  pinMode(stepPin2, OUTPUT);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  pinMode(buttonPin, INPUT_PULLUP);

  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);

  Serial.begin(BAUD);
  Link.begin(BAUD);

  lcd.init();
  lcd.backlight();

  digitalWrite(dirPin, HIGH);
  digitalWrite(dirPin2, HIGH);

  Serial.println("UNO @9600. ESP32 sends ONLY: 1=PAUSE, 0=RESUME.");
  Serial.println("LCD shows state + distance(mm) + P flag.");
  updateLCD(true);
}

void loop() {
  // Treat as “interrupt”: check commands ASAP each loop
  pollESP32();

  // If paused: freeze FSM + stepping completely (no transitions),
  // keep LCD showing the last-known distance/state.
  if (paused) {
    // still poll frequently
    pollESP32();
    delay(2);
    return;
  }

  // Sensor update
  unsigned long currentMillis = millis();
  if (currentMillis - previousSensorMillis >= sensorInterval) {
    previousSensorMillis = currentMillis;
    dist = getDistance();
    updateLCD(false);
  }

  // FSM (same logic, but with setState so prints don’t spam)
  switch (state) {
    case STOP_FWD:
      if (buttonPressed()) {
        digitalWrite(dirPin, HIGH);
        digitalWrite(dirPin2, HIGH);
        setState(RUN_FWD);
      }
      break;

    case RUN_FWD:
      if (dist >= 10.5) {
        setState(STOP_BWD);
      }
      break;

    case STOP_BWD:
      if (buttonPressed()) {
        digitalWrite(dirPin, LOW);
        setState(RUN_BWD);
      }
      break;

    case RUN_BWD:
      if (dist <= 4.0) {
        setState(STOP_FWD);
      }
      break;
  }

  // Stepping
  if (state == RUN_FWD || state == RUN_BWD) {
    unsigned long now = micros();
    if (now - lastStepTime >= stepRate) {
      lastStepTime = now;
      if (state == RUN_FWD) stepOnceAandRatio();
      else                  stepOnceAandRatio_linear();
    }
  }
}
