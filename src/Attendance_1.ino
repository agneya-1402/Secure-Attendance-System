#include <Servo.h>

Servo doorServo;
const int servoPin = 9;

void setup() {
  Serial.begin(9600);
  doorServo.attach(servoPin);
  doorServo.write(0);  // Initialize door closed
}

void loop() {
  if (Serial.available() > 0) {
    char command = Serial.read();
    if (command == '1') {
      doorServo.write(90);  // Open door
    } else if (command == '0') {
      doorServo.write(0);   // Close door
    }
  }
}