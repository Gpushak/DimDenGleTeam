void setup() {
  pinMode(13, OUTPUT);
  Serial.begin(9600);
}

void loop() {
  int value = analogRead(A0);

  if (value > 500) {
    digitalWrite(13, HIGH);
  } else {
    digitalWrite(13, LOW);
  }

  Serial.println(value);
  delay(1000);
}