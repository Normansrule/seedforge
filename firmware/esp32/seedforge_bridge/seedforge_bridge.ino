/*
  SeedForge ESP32-C3 communications / UI bridge  (Seeed XIAO ESP32-C3 pinout)

  Role (docs/controls.md):
    * forwards complete protocol lines between the Uno core controller and
      hosts on USB-CDC, BLE (Nordic UART Service) and, optionally, Wi-Fi TCP;
    * shows machine state on a 2.2" ILI9341 display;
    * is NOT part of the safety chain.  It never generates HEARTBEAT, VISION_OK
      or any command on its own, so if the host disappears the Uno's
      heartbeat watchdog still trips.  If this board disappears, the Uno stops
      receiving heartbeats and stops the machine.

  Wiring (3.3 V logic):
    D6/GPIO21 TX -> Uno A1 (SoftwareSerial RX)          direct
    D7/GPIO20 RX <- Uno A2 via 1 kOhm series, 2 kOhm to GND (5 V -> 3.3 V divider)
    GND <-> Uno GND
    ILI9341: SCK D8/GPIO8, MISO D9/GPIO9, MOSI D10/GPIO10, CS D1/GPIO3,
             DC D2/GPIO4, RST D3/GPIO5, VCC 3V3, LED 3V3 (through the module's resistor)

  Wi-Fi is off unless you create secrets.h (see secrets.example.h; never commit it).

  STATUS: Compile-tested; hardware testing pending.
  SPDX-License-Identifier: MIT
*/
#include <Adafruit_GFX.h>
#include <Adafruit_ILI9341.h>
#include <BLE2902.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <SPI.h>
#include <WiFi.h>

#if __has_include("secrets.h")
#include "secrets.h"
#define SF_WIFI 1
#else
#define SF_WIFI 0
#endif

static const uint32_t LINK_BAUD = 38400;   // must match firmware/arduino sf_config.h
static const int PIN_LINK_TX = 21, PIN_LINK_RX = 20;
static const int PIN_TFT_CS = 3, PIN_TFT_DC = 4, PIN_TFT_RST = 5;
static const uint16_t TCP_PORT = 3333;
static const char* BLE_NAME = "SEEDFORGE";
// Nordic UART Service UUIDs (same as the original EECS 149 relay, so its BLE script still connects)
static const char* NUS_SERVICE = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E";
static const char* NUS_RX = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E";   // host writes
static const char* NUS_TX = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E";   // we notify

HardwareSerial Link(1);
Adafruit_ILI9341 tft(PIN_TFT_CS, PIN_TFT_DC, PIN_TFT_RST);
BLECharacteristic* bleTx = nullptr;
volatile bool bleConnected = false;
#if SF_WIFI
WiFiServer server(TCP_PORT);
WiFiClient client;
#endif

// ---------------------------------------------------------------- line assembly
struct LineAsm {
  char buf[96];
  size_t len = 0;
  bool overflow = false;
  // Returns true when a complete non-empty line is ready in buf. Only a newline (or CR) ends a
  // line, so a command split across BLE packets or TCP segments is never forwarded in pieces.
  // An overlong line is discarded whole (never its tail).
  bool feed(char c) {
    if (c == '\n' || c == '\r') {
      bool ok = len && !overflow;
      if (ok) buf[len] = '\0';
      len = 0;
      overflow = false;
      return ok;
    }
    if (c >= 32 && c <= 126 && !overflow) {
      if (len < sizeof(buf) - 1) buf[len++] = c;
      else overflow = true;
    }
    return false;
  }
};
LineAsm fromUno, fromUsb, fromTcp;

// BLE writes arrive in a callback (other task): queue them for loop()
static QueueHandle_t bleQueue;
struct BleLine { char s[96]; };

// ---------------------------------------------------------------- display model
struct View {
  char state[16] = "NO LINK";
  char fault[24] = "NONE";
  char turn[8] = "-";
  char tension[12] = "-";
  char pos[12] = "-";
  char last[48] = "";
  uint32_t t_uno = 0;
  bool dirty = true;
} view;

static void copyField(char* dst, size_t n, const char* src) {
  strncpy(dst, src, n - 1);
  dst[n - 1] = '\0';
  view.dirty = true;
}

static void parseForView(const char* line) {
  view.t_uno = millis();
  if (!strncmp(line, "STATE=", 6)) copyField(view.state, sizeof view.state, line + 6);
  else if (!strncmp(line, "FAULT=", 6)) copyField(view.fault, sizeof view.fault, line + 6);
  else if (!strncmp(line, "TURN=", 5)) copyField(view.turn, sizeof view.turn, line + 5);
  else if (!strncmp(line, "TENSION=", 8)) copyField(view.tension, sizeof view.tension, line + 8);
  else if (!strncmp(line, "POSITION=", 9)) copyField(view.pos, sizeof view.pos, line + 9);
  else if (!strncmp(line, "STATUS ", 7)) {
    const char* f = strstr(line, "fault=");
    if (f) { char tmp[24]; sscanf(f + 6, "%23s", tmp); if (strcmp(tmp, view.fault)) copyField(view.fault, sizeof view.fault, tmp); }
    const char* s = strstr(line, "state=");
    if (s) { char tmp[16]; sscanf(s + 6, "%15s", tmp); if (strcmp(tmp, view.state)) copyField(view.state, sizeof view.state, tmp); }
  }
  if (!strncmp(line, "ERROR=", 6) || !strncmp(line, "EVENT=", 6) || !strncmp(line, "COMPLETE", 8)) copyField(view.last, sizeof view.last, line);
}

static uint16_t stateColor(const char* s) {
  if (!strcmp(s, "SAFE_STOP") || !strcmp(s, "NO LINK")) return 0xC8A2;   // muted red
  if (!strcmp(s, "WIND") || !strcmp(s, "PRETENSION") || !strcmp(s, "HOME")) return 0x2B49;   // forest green
  return 0x1A49;                                                       // navy
}

static void drawView() {
  tft.fillScreen(ILI9341_WHITE);
  tft.fillRect(0, 0, 320, 34, 0x10A6);
  tft.setTextColor(ILI9341_WHITE);
  tft.setTextSize(2);
  tft.setCursor(10, 10);
  tft.print("SeedForge core");
  tft.fillRect(10, 46, 300, 46, stateColor(view.state));
  tft.setTextSize(3);
  tft.setCursor(20, 58);
  tft.print(view.state);
  tft.setTextColor(0x10A6);
  tft.setTextSize(2);
  const char* labels[] = {"fault", "turn", "tension N", "pos mm"};
  const char* vals[] = {view.fault, view.turn, view.tension, view.pos};
  for (int i = 0; i < 4; ++i) {
    tft.setCursor(10, 104 + i * 26);
    tft.print(labels[i]);
    tft.setCursor(150, 104 + i * 26);
    tft.print(vals[i]);
  }
  tft.setTextSize(1);
  tft.setCursor(10, 212);
  tft.print(view.last);
  tft.setCursor(10, 226);
  tft.printf("BLE %s  WiFi %s", bleConnected ? "on" : "off", SF_WIFI ? (WiFi.status() == WL_CONNECTED ? "on" : "...") : "disabled");
  view.dirty = false;
}

// ---------------------------------------------------------------- outputs
static void toHosts(const char* line) {
  Serial.println(line);
  if (bleConnected && bleTx) {
    // Notify in 20-byte chunks (default ATT MTU) and end with a newline so the host can
    // reassemble complete lines.
    char out[100];
    size_t n = snprintf(out, sizeof out, "%s\n", line);
    if (n >= sizeof out) n = sizeof out - 1;
    for (size_t i = 0; i < n; i += 20) {
      size_t k = n - i < 20 ? n - i : 20;
      bleTx->setValue((uint8_t*)out + i, k);
      bleTx->notify();
      delay(3);
    }
  }
#if SF_WIFI
  if (client && client.connected()) client.println(line);
#endif
}

static void toUno(const char* line) {
  // Bridge-local queries are answered here and never forwarded.
  if (!strcmp(line, "BRIDGE?")) {
    char msg[64];
    snprintf(msg, sizeof msg, "BRIDGE ble=%d wifi=%d uno_age_ms=%lu", bleConnected ? 1 : 0, SF_WIFI,
             (unsigned long)(millis() - view.t_uno));
    toHosts(msg);
    return;
  }
  Link.print(line);
  Link.print('\n');
}

class ServerCb : public BLEServerCallbacks {
  void onConnect(BLEServer*) override { bleConnected = true; view.dirty = true; }
  void onDisconnect(BLEServer* s) override {
    bleConnected = false;
    view.dirty = true;
    s->getAdvertising()->start();
  }
};

class RxCb : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* c) override {
    String v = c->getValue();
    // a single write may carry several lines or a partial line
    static LineAsm bleAsm;
    for (size_t i = 0; i < v.length(); ++i) {
      if (bleAsm.feed(v[i])) {
        BleLine l;
        strncpy(l.s, bleAsm.buf, sizeof l.s);
        xQueueSend(bleQueue, &l, 0);
      }
    }
    // No newline yet: keep the partial line. Terminals must send a newline (most have a
    // "send with newline" option); a partial command is never forwarded.
  }
};

void setup() {
  Serial.begin(115200);
  Link.begin(LINK_BAUD, SERIAL_8N1, PIN_LINK_RX, PIN_LINK_TX);
  bleQueue = xQueueCreate(8, sizeof(BleLine));

  tft.begin();
  tft.setRotation(1);
  drawView();

  BLEDevice::init(BLE_NAME);
  BLEServer* srv = BLEDevice::createServer();
  srv->setCallbacks(new ServerCb());
  BLEService* svc = srv->createService(NUS_SERVICE);
  bleTx = svc->createCharacteristic(NUS_TX, BLECharacteristic::PROPERTY_NOTIFY);
  bleTx->addDescriptor(new BLE2902());
  BLECharacteristic* rx = svc->createCharacteristic(NUS_RX, BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
  rx->setCallbacks(new RxCb());
  svc->start();
  BLEAdvertising* adv = BLEDevice::getAdvertising();
  adv->addServiceUUID(NUS_SERVICE);
  adv->start();

#if SF_WIFI
  WiFi.mode(WIFI_STA);
  WiFi.begin(SF_WIFI_SSID, SF_WIFI_PASSWORD);
  server.begin();
#endif
  toHosts("BRIDGE seedforge_bridge fw=0.3.0-alpha");
}

void loop() {
  while (Link.available()) {
    if (fromUno.feed((char)Link.read())) {
      parseForView(fromUno.buf);
      toHosts(fromUno.buf);
    }
  }
  while (Serial.available()) {
    if (fromUsb.feed((char)Serial.read())) toUno(fromUsb.buf);
  }
  BleLine l;
  while (xQueueReceive(bleQueue, &l, 0) == pdTRUE) toUno(l.s);
#if SF_WIFI
  if (!client || !client.connected()) {
    WiFiClient c = server.accept();
    if (c) client = c;
  }
  while (client && client.available()) {
    if (fromTcp.feed((char)client.read())) toUno(fromTcp.buf);
  }
#endif
  static uint32_t t_draw = 0;
  if (millis() - view.t_uno > 3000 && strcmp(view.state, "NO LINK")) copyField(view.state, sizeof view.state, "NO LINK");
  if (view.dirty && millis() - t_draw > 200) {
    t_draw = millis();
    drawView();
  }
}
