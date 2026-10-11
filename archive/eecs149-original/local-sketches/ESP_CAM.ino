#include "esp_camera.h"
#include <WiFi.h>

// ---------- Camera pins (AI-Thinker) ----------
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22
#define LED_GPIO_NUM 4      // white flash LED

// ---------- Globals ----------
WiFiServer server(80);
String colorName = "Detecting...";
int rVal = 0, gVal = 0, bVal = 0;

// ---------- Simple color-bank ----------
String nearestColorName(int r, int g, int b) {
  struct C { const char* name; int r, g, b; };
  const C colors[] = {
    {"Black",0,0,0},{"White",255,255,255},{"Red",255,0,0},
    {"Lime",0,255,0},{"Blue",0,0,255},{"Yellow",255,255,0},
    {"Cyan",0,255,255},{"Magenta",255,0,255},{"Silver",192,192,192},
    {"Gray",128,128,128},{"Maroon",128,0,0},{"Olive",128,128,0},
    {"Green",0,128,0},{"Purple",128,0,128},{"Teal",0,128,128},
    {"Navy",0,0,128},{"Orange",255,165,0},{"Pink",255,192,203},
    {"Brown",139,69,19},{"DeepSkyBlue",0,191,255},{"Violet",238,130,238}
  };
  int best = 999999, idx = 0;
  for (int i = 0; i < sizeof(colors)/sizeof(colors[0]); i++) {
    int dr = r - colors[i].r, dg = g - colors[i].g, db = b - colors[i].b;
    int d = dr*dr + dg*dg + db*db;
    if (d < best) { best = d; idx = i; }
  }
  return String(colors[idx].name);
}

// ---------- HTML root ----------
void handleRoot(WiFiClient &client) {
  String html =
  "HTTP/1.1 200 OK\r\nContent-Type:text/html\r\n\r\n"
  "<html><head><meta name='viewport' content='width=device-width,initial-scale=1'>"
  "<title>ESP32-CAM SVGA Color Detector</title>"
  "<style>"
  "body{margin:0;background:#000;text-align:center;color:#fff;font-family:sans-serif}"
  "#overlay{position:absolute;top:10px;left:0;right:0;font-size:1.5em;font-weight:bold}"
  "</style></head><body>"
  "<div id='overlay'>Detecting...</div>"
  "<img src='/stream' width='100%'>"
  "<script>"
  "async function poll(){"
  " try{let r=await fetch('/color');let j=await r.json();"
  " let t='Detected Color: '+j.name+' (R:'+j.r+' G:'+j.g+' B:'+j.b+')';"
  " document.getElementById('overlay').innerText=t;"
  " document.getElementById('overlay').style.color='rgb('+j.r+','+j.g+','+j.b+')';"
  " }catch(e){} setTimeout(poll,1000);} poll();"
  "</script></body></html>";
  client.print(html);
}

// ---------- JSON color endpoint ----------
void handleColor(WiFiClient &client) {
  client.println("HTTP/1.1 200 OK\r\nContent-Type:application/json\r\nConnection:close\r\n");
  client.printf("{\"name\":\"%s\",\"r\":%d,\"g\":%d,\"b\":%d}", 
                colorName.c_str(), rVal, gVal, bVal);
}

// ---------- Stream ----------
void handleStream(WiFiClient &client) {
  client.println("HTTP/1.1 200 OK\r\nContent-Type:multipart/x-mixed-replace; boundary=frame\r\n");
  while (client.connected()) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) continue;
    client.printf("--frame\r\nContent-Type:image/jpeg\r\nContent-Length:%u\r\n\r\n", fb->len);
    client.write(fb->buf, fb->len);
    client.print("\r\n");

    static unsigned long lastCheck = 0;
    if (millis() - lastCheck > 1000) {
      lastCheck = millis();
      long r=0,g=0,b=0; int count=0;
      uint16_t *pix=(uint16_t*)fb->buf;
      for (int i=0;i<fb->len/2;i+=120) {   // sample pixels
        uint16_t p=pix[i];
        r+=((p>>11)&0x1F)<<3;
        g+=((p>>5)&0x3F)<<2;
        b+=(p&0x1F)<<3;
        count++;
      }
      r/=count; g/=count; b/=count;
      rVal=r; gVal=g; bVal=b;
      colorName = nearestColorName(r,g,b);
      Serial.printf("[RESULT] %-12s  RGB(%3ld,%3ld,%3ld)\n", colorName.c_str(), r,g,b);
    }
    esp_camera_fb_return(fb);
    delay(60);
  }
}

// ---------- Router ----------
void route(WiFiClient &c,String req){
  if(req.indexOf("GET / ")>=0) handleRoot(c);
  else if(req.indexOf("GET /color")>=0) handleColor(c);
  else if(req.indexOf("GET /stream")>=0) handleStream(c);
  else c.println("HTTP/1.1 404 Not Found\r\n\r\n");
}

// ---------- Setup ----------
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n===== ESP32-CAM SVGA Color Detector =====");

  pinMode(LED_GPIO_NUM, OUTPUT);
  digitalWrite(LED_GPIO_NUM, HIGH); delay(1000); digitalWrite(LED_GPIO_NUM, LOW);

  // Access-point setup
  WiFi.mode(WIFI_AP);
  IPAddress ip(192,168,4,1);
  WiFi.softAPConfig(ip, ip, IPAddress(255,255,255,0));
  WiFi.softAP("CAM","12345678");
  Serial.println("[OK] Access Point 'CAM' ready — open http://192.168.4.1\n");

  // Camera config
  camera_config_t c;
  c.ledc_channel=LEDC_CHANNEL_0;
  c.ledc_timer=LEDC_TIMER_0;
  c.pin_d0=Y2_GPIO_NUM;c.pin_d1=Y3_GPIO_NUM;c.pin_d2=Y4_GPIO_NUM;c.pin_d3=Y5_GPIO_NUM;
  c.pin_d4=Y6_GPIO_NUM;c.pin_d5=Y7_GPIO_NUM;c.pin_d6=Y8_GPIO_NUM;c.pin_d7=Y9_GPIO_NUM;
  c.pin_xclk=XCLK_GPIO_NUM;c.pin_pclk=PCLK_GPIO_NUM;c.pin_vsync=VSYNC_GPIO_NUM;
  c.pin_href=HREF_GPIO_NUM;c.pin_sscb_sda=SIOD_GPIO_NUM;c.pin_sscb_scl=SIOC_GPIO_NUM;
  c.pin_pwdn=PWDN_GPIO_NUM;c.pin_reset=RESET_GPIO_NUM;
  c.xclk_freq_hz=20000000;
  c.pixel_format=PIXFORMAT_JPEG;

  if (psramFound()) {
    c.frame_size = FRAMESIZE_SVGA;   // 800×600
    c.jpeg_quality = 12;             // 10–12 = good quality
    c.fb_count = 2;
  } else {
    c.frame_size = FRAMESIZE_QVGA;
    c.jpeg_quality = 20;
    c.fb_count = 1;
  }

  if (esp_camera_init(&c) != ESP_OK) {
    Serial.println("[ERROR] Camera init failed!");
    return;
  }
  server.begin();
  Serial.println("[OK] Camera ready.\n");
}

// ---------- Main loop ----------
void loop() {
  WiFiClient client = server.available();
  if (!client) return;
  String req = client.readStringUntil('\r');
  client.readStringUntil('\n');
  route(client, req);
  delay(10);
}
