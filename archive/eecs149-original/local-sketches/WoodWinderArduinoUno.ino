// Define pin connections & motor steps per revolution
const int dirPin = 2;
const int stepPin = 3;

// Ultrasonic sensor pins
#define TRIG_PIN 4
#define ECHO_PIN 5

// LED pin for blinking
const int ledPin = 13;

// Timing intervals
const unsigned long sensorInterval = 1000; // 1 second for ultrasonic sensor reading
const unsigned long ledInterval = 1000;    // 1 second for LED blink
unsigned long previousSensorMillis = 0;
unsigned long previousLedMillis = 0;

bool ledState = LOW;

void setup() {
  // Motor pins
  pinMode(dirPin, OUTPUT);
  pinMode(stepPin, OUTPUT);

  // Ultrasonic sensor pins
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // LED pin
  pinMode(ledPin, OUTPUT);

  // Serial at 115200 baud
  Serial.begin(115200);

  // Set motor direction clockwise
  digitalWrite(dirPin, HIGH);
}

void loop() {
  unsigned long currentMillis = millis();

  // Blink LED once every second
  if (currentMillis - previousLedMillis >= ledInterval) {
    previousLedMillis = currentMillis;
    ledState = !ledState; // toggle LED state
    digitalWrite(ledPin, ledState);
  }

  // Read ultrasonic sensor every second
  if (currentMillis - previousSensorMillis >= sensorInterval) {
    previousSensorMillis = currentMillis;

    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);

    long duration = pulseIn(ECHO_PIN, HIGH);
    float distance = duration * 0.034 / 2;

    Serial.print("Distance: ");
    Serial.print(distance);
    Serial.println(" cm");
  }

  // Stepper motor continuous smooth rotation
  digitalWrite(stepPin, HIGH);
  delayMicroseconds(1000);  // Adjust for speed; smaller is faster
  digitalWrite(stepPin, LOW);
  delayMicroseconds(1000);  // Adjust for speed; same as above
}
