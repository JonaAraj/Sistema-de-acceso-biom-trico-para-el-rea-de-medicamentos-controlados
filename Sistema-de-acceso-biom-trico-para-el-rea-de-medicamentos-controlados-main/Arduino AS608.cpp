#include <Adafruit_Fingerprint.h>
#include <SoftwareSerial.h>

SoftwareSerial mySerial(2, 3);  // RX, TX
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&mySerial);

void setup() {
  Serial.begin(9600);
  finger.begin(57600);
  if (finger.verifyPassword()) {
    Serial.println("Sensor conectado");
  } else {
    Serial.println("Sensor no detectado");
    while (1);
  }
}

void loop() {
  getFingerprintID();
  delay(50);
}

uint8_t getFingerprintID() {
  uint8_t p = finger.getImage();
  if (p != FINGERPRINT_OK) return p;

  p = finger.image2Tz();
  if (p != FINGERPRINT_OK) return p;

  p = finger.fingerSearch();
  if (p == FINGERPRINT_OK) {
    Serial.print("HuellaID:");
    Serial.println(finger.fingerID);
    while (finger.getImage() != FINGERPRINT_NOFINGER) {
      delay(100);
    }
  }
  return p;
}
