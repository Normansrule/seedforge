/*
  SeedForge R3 - core winder controller example

  Purpose:
    - deterministic synchronized rotation + linear stepping
    - hard stop on E-stop/limit/fault/heartbeat loss
    - compact event protocol to ESP32/vision host
    - exact turn-count stop followed by vision verification

  This is a development starting point, not safety-rated firmware.
  The physical E-stop must interrupt actuator power independently of software.
*/

#include <SoftwareSerial.h>

// -------------------- PIN MAP --------------------
const uint8_t PIN_ROT_STEP = 2;
const uint8_t PIN_ROT_DIR  = 3;
const uint8_t PIN_LIN_STEP = 4;
const uint8_t PIN_LIN_DIR  = 5;
const uint8_t PIN_ENABLE   = 6;   // A4988 ENABLE, active LOW
const uint8_t PIN_START    = 7;   // momentary to GND
const uint8_t PIN_ESTOP_FB = 8;   // NC feedback to GND; open = unsafe
const uint8_t PIN_HOME     = 9;   // NC switch to GND
const uint8_t PIN_END      = 10;  // NC switch to GND
const uint8_t PIN_HX_DOUT  = 11;  // reserved for HX711 integration
const uint8_t PIN_HX_SCK   = 12;  // reserved for HX711 integration
const uint8_t PIN_LED      = 13;
const uint8_t PIN_DANCER   = A0;

// ESP32 link. Uno TX is 5 V: use the documented resistor divider before ESP32 RX.
SoftwareSerial Link(A1, A2); // Uno RX, TX
const uint32_t LINK_BAUD = 19200;

// -------------------- RECIPE --------------------
// A4988 at 1/16 microstepping: 200 full steps/rev * 16 = 3200.
const uint32_t ROT_USTEPS_PER_REV = 3200UL;
// T8x8 screw at 1/16: 200*16/8 = 400 microsteps/mm.
const uint32_t LIN_USTEPS_PER_MM  = 400UL;

// STARTING development value only. Replace with your measured accepted recipe.
float pitchMmPerRev = 4.084f;
const uint8_t ACTIVE_TURNS = 7;
const uint8_t SACRIFICIAL_TURNS = 1;

// Slow by design for first real hardware tests.
uint32_t rotStepIntervalUs = 1500UL;
const uint8_t STEP_PULSE_US = 3;

// Communications watchdog.
const uint32_t HEARTBEAT_TIMEOUT_MS = 3000UL;
uint32_t lastHeartbeatMs = 0;

// -------------------- STATE --------------------
enum State : uint8_t {
  IDLE,
  PRETENSION,
  WINDING,
  VERIFY,
  COMPLETE,
  SAFE_STOP
};

State state = IDLE;
char stopReason[40] = "NONE";

uint32_t rotStepsDone = 0;
uint32_t linStepsDone = 0;
uint32_t targetRotSteps = 0;
uint32_t linNumeratorPerRev = 0; // rounded linear usteps/rev
uint32_t ddaAccumulator = 0;
uint32_t lastRotStepUs = 0;
uint32_t lastStatusMs = 0;

bool lastStart = HIGH;
uint32_t lastStartEdgeMs = 0;

char usbBuf[80];
uint8_t usbLen = 0;
char linkBuf[80];
uint8_t linkLen = 0;

// -------------------- HELPERS --------------------
const char* stateName(State s) {
  switch (s) {
    case IDLE:       return "IDLE";
    case PRETENSION: return "PRETENSION";
    case WINDING:    return "WINDING";
    case VERIFY:     return "VERIFY";
    case COMPLETE:   return "COMPLETE";
    case SAFE_STOP:  return "SAFE_STOP";
    default:         return "UNKNOWN";
  }
}

void pulsePin(uint8_t pin) {
  digitalWrite(pin, HIGH);
  delayMicroseconds(STEP_PULSE_US);
  digitalWrite(pin, LOW);
}

void driversEnable(bool enable) {
  digitalWrite(PIN_ENABLE, enable ? LOW : HIGH);
}

bool estopHealthy() {
  // NC loop: healthy contact pulls input LOW; open wire/contact reads HIGH.
  return digitalRead(PIN_ESTOP_FB) == LOW;
}

bool homeHealthy() {
  // NC switch convention: normal = LOW, actuated/open = HIGH.
  return digitalRead(PIN_HOME) == LOW;
}

bool endHealthy() {
  return digitalRead(PIN_END) == LOW;
}

void sendLine(const char* s) {
  Link.println(s);
  Serial.println(s);
}

void sendStatus() {
  char msg[100];
  snprintf(msg, sizeof(msg),
           "STATUS,state=%s,rot=%lu,lin=%lu,estop=%u,home=%u,end=%u,reason=%s",
           stateName(state),
           (unsigned long)rotStepsDone,
           (unsigned long)linStepsDone,
           estopHealthy() ? 1 : 0,
           homeHealthy() ? 1 : 0,
           endHealthy() ? 1 : 0,
           stopReason);
  sendLine(msg);
}

void safeStop(const char* reason) {
  driversEnable(false);
  state = SAFE_STOP;
  strncpy(stopReason, reason, sizeof(stopReason) - 1);
  stopReason[sizeof(stopReason) - 1] = '\0';
  digitalWrite(PIN_LED, HIGH);
  sendStatus();
}

void resetJobCounters() {
  rotStepsDone = 0;
  linStepsDone = 0;
  ddaAccumulator = 0;
  targetRotSteps = ROT_USTEPS_PER_REV * (uint32_t)(ACTIVE_TURNS + SACRIFICIAL_TURNS);
  linNumeratorPerRev = (uint32_t)(pitchMmPerRev * (float)LIN_USTEPS_PER_MM + 0.5f);
}

void beginWinding() {
  if (!estopHealthy()) {
    safeStop("ESTOP_OPEN");
    return;
  }
  if (!endHealthy()) {
    safeStop("END_LIMIT_ACTIVE");
    return;
  }

  resetJobCounters();
  strncpy(stopReason, "NONE", sizeof(stopReason));
  digitalWrite(PIN_ROT_DIR, HIGH);
  digitalWrite(PIN_LIN_DIR, HIGH);
  driversEnable(true);
  lastRotStepUs = micros();
  lastHeartbeatMs = millis();
  digitalWrite(PIN_LED, LOW);
  state = WINDING;
  sendStatus();
}

void doSynchronizedStep() {
  // One rotation microstep is the master tick.
  pulsePin(PIN_ROT_STEP);
  rotStepsDone++;

  // Linear microsteps per rotation revolution = pitch * linear usteps/mm.
  // Accumulate against ROT_USTEPS_PER_REV using integer DDA/Bresenham logic.
  ddaAccumulator += linNumeratorPerRev;
  while (ddaAccumulator >= ROT_USTEPS_PER_REV) {
    pulsePin(PIN_LIN_STEP);
    linStepsDone++;
    ddaAccumulator -= ROT_USTEPS_PER_REV;
  }
}

void serviceStepper() {
  if (state != WINDING) return;

  uint32_t now = micros();
  // One step per loop pass avoids large catch-up bursts after a blocking event.
  if ((uint32_t)(now - lastRotStepUs) >= rotStepIntervalUs) {
    lastRotStepUs += rotStepIntervalUs;
    doSynchronizedStep();

    if (rotStepsDone >= targetRotSteps) {
      driversEnable(false);
      state = VERIFY;
      sendLine("EVENT:WIND_COMPLETE_WAITING_FOR_VISION");
      sendStatus();
    }
  }
}

void processCommand(char* cmd) {
  while (*cmd == ' ' || *cmd == '\t') cmd++;
  for (char* p = cmd; *p; ++p) {
    if (*p >= 'a' && *p <= 'z') *p -= 32;
  }

  // Safety and fault commands are always honored, regardless of current state.
  if (!strcmp(cmd, "STOP") || !strcmp(cmd, "EMERGENCY_STOP")) {
    safeStop("REMOTE_STOP");
    return;
  }
  if (!strncmp(cmd, "FAULT_", 6)) {
    safeStop(cmd);
    return;
  }
  if (!strcmp(cmd, "HEARTBEAT")) {
    lastHeartbeatMs = millis();
    return;
  }

  if (!strcmp(cmd, "RESET")) {
    if (!estopHealthy()) {
      sendLine("ERROR:ESTOP_STILL_OPEN");
      return;
    }
    driversEnable(false);
    state = IDLE;
    strncpy(stopReason, "NONE", sizeof(stopReason));
    digitalWrite(PIN_LED, LOW);
    sendStatus();
    return;
  }

  if (!strcmp(cmd, "START")) {
    if (state == IDLE || state == COMPLETE) beginWinding();
    return;
  }

  if (!strcmp(cmd, "VISION_OK")) {
    if (state == VERIFY) {
      state = COMPLETE;
      sendLine("EVENT:PART_ACCEPTED");
      sendStatus();
    }
    return;
  }

  if (!strncmp(cmd, "PITCH=", 6)) {
    float p = atof(cmd + 6);
    if (p > 0.2f && p < 20.0f && state != WINDING) {
      pitchMmPerRev = p;
      sendLine("OK:PITCH_UPDATED");
    } else {
      sendLine("ERROR:BAD_PITCH_OR_BUSY");
    }
    return;
  }

  if (!strncmp(cmd, "STEP_US=", 8)) {
    long v = atol(cmd + 8);
    if (v >= 500 && v <= 10000 && state != WINDING) {
      rotStepIntervalUs = (uint32_t)v;
      sendLine("OK:SPEED_UPDATED");
    } else {
      sendLine("ERROR:BAD_SPEED_OR_BUSY");
    }
    return;
  }

  if (!strcmp(cmd, "STATUS")) {
    sendStatus();
    return;
  }
}

void serviceSerial(Stream& s, char* buf, uint8_t& len, size_t cap) {
  while (s.available()) {
    char c = (char)s.read();
    if (c == '\r' || c == '\n') {
      if (len) {
        buf[len] = '\0';
        processCommand(buf);
        len = 0;
      }
    } else if (c >= 32 && c <= 126 && len < cap - 1) {
      buf[len++] = c;
    }
  }
}

void serviceStartButton() {
  bool now = digitalRead(PIN_START);
  uint32_t ms = millis();
  if (lastStart == HIGH && now == LOW && ms - lastStartEdgeMs > 200) {
    lastStartEdgeMs = ms;
    if (state == IDLE || state == COMPLETE) beginWinding();
    else safeStop("LOCAL_STOP_BUTTON");
  }
  lastStart = now;
}

void serviceSafety() {
  // Software check supplements, but never replaces, physical actuator-power interruption.
  if (!estopHealthy() && state != SAFE_STOP) {
    safeStop("ESTOP_OPEN");
    return;
  }

  if (state == WINDING) {
    if (!endHealthy()) {
      safeStop("END_LIMIT_ACTIVE");
      return;
    }
    if ((uint32_t)(millis() - lastHeartbeatMs) > HEARTBEAT_TIMEOUT_MS) {
      safeStop("HEARTBEAT_TIMEOUT");
      return;
    }
  }
}

void setup() {
  pinMode(PIN_ROT_STEP, OUTPUT);
  pinMode(PIN_ROT_DIR, OUTPUT);
  pinMode(PIN_LIN_STEP, OUTPUT);
  pinMode(PIN_LIN_DIR, OUTPUT);
  pinMode(PIN_ENABLE, OUTPUT);
  pinMode(PIN_START, INPUT_PULLUP);
  pinMode(PIN_ESTOP_FB, INPUT_PULLUP);
  pinMode(PIN_HOME, INPUT_PULLUP);
  pinMode(PIN_END, INPUT_PULLUP);
  pinMode(PIN_HX_DOUT, INPUT);
  pinMode(PIN_HX_SCK, OUTPUT);
  pinMode(PIN_LED, OUTPUT);

  digitalWrite(PIN_ROT_STEP, LOW);
  digitalWrite(PIN_LIN_STEP, LOW);
  digitalWrite(PIN_HX_SCK, LOW);
  driversEnable(false);
  digitalWrite(PIN_LED, LOW);

  Serial.begin(115200);
  Link.begin(LINK_BAUD);
  delay(100);

  lastHeartbeatMs = millis();
  sendLine("SEEDFORGE_R3_READY");
  sendStatus();
}

void loop() {
  // Order matters: safety is serviced before motion.
  serviceSafety();
  serviceSerial(Serial, usbBuf, usbLen, sizeof(usbBuf));
  serviceSerial(Link, linkBuf, linkLen, sizeof(linkBuf));
  serviceStartButton();
  serviceStepper();

  if (millis() - lastStatusMs >= 500) {
    lastStatusMs = millis();
    sendStatus();
  }
}
