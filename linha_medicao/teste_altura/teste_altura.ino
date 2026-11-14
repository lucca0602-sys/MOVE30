// ============================================================
// MOVE30 - TESTE ISOLADO DO SENSOR DE ALTURA (VL53L0X)
// Ligacoes: VIN->3V3 | GND->GND | SDA->GPIO 9 | SCL->GPIO 8
// Placa: ESP32-S3 (USB CDC On Boot: Enabled) | Serial 115200
//
// 1) Varre o I2C e lista os enderecos achados.
//    VL53L0X = 0x29 | MAX30102 (batimento) = 0x57
// 2) Le a distancia a cada 300 ms e mostra a altura calculada
//    com o sensor a ALTURA_SENSOR_MM do chao.
// Depois do teste, grave de novo o firmware linha_medicao.
// ============================================================
#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_VL53L0X.h>

#define PIN_SDA 9
#define PIN_SCL 8
#define ALTURA_SENSOR_MM 2300.0f   // mesma constante do firmware principal

Adafruit_VL53L0X lox;
bool sensorOk = false;

void varrerI2C() {
  Serial.println("\n[I2C] Procurando dispositivos (SDA=9, SCL=8)...");
  int achados = 0;
  for (uint8_t end = 1; end < 127; end++) {
    Wire.beginTransmission(end);
    if (Wire.endTransmission() == 0) {
      Serial.printf("  achado: 0x%02X", end);
      if (end == 0x29) Serial.print("  <- VL53L0X (altura)");
      if (end == 0x57) Serial.print("  <- MAX30102 (batimento)");
      Serial.println();
      achados++;
    }
  }
  if (achados == 0) Serial.println("  nenhum dispositivo: confira VIN, GND, SDA e SCL.");
}

void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial.println("\n=== TESTE SENSOR DE ALTURA ===");
  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.setClock(100000);
  varrerI2C();

  sensorOk = lox.begin();
  if (sensorOk) {
    Serial.println("[VL53L0X] OK, iniciado.");
  } else {
    Serial.println("[VL53L0X] NAO encontrado. Se 0x29 nao apareceu acima, e fiacao/solda.");
  }
}

void loop() {
  if (!sensorOk) {
    // Tenta de novo a cada 3 s (util enquanto mexe nos fios).
    delay(3000);
    varrerI2C();
    sensorOk = lox.begin();
    if (sensorOk) Serial.println("[VL53L0X] OK, iniciado.");
    return;
  }

  VL53L0X_RangingMeasurementData_t m;
  lox.rangingTest(&m, false);
  if (m.RangeStatus == 4) {
    Serial.println("Distancia: fora de alcance (nada embaixo ou longe demais)");
  } else {
    int mm = m.RangeMilliMeter;
    float altura = (ALTURA_SENSOR_MM - mm) / 1000.0f;
    Serial.printf("Distancia: %4d mm  ->  altura estimada: %.2f m\n", mm, altura);
  }
  delay(300);
}
