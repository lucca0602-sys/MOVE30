#include <Arduino.h>
#include <Adafruit_VL53L0X.h>
#include "config.h"
#include "util.h"
#include "sensor_altura.h"

static Adafruit_VL53L0X lox;

bool alturaIniciar() { return lox.begin(); }

static bool lerDistanciaMM(int &mm) {
  VL53L0X_RangingMeasurementData_t m;
  lox.rangingTest(&m, false);
  if (m.RangeStatus == 4) return false;
  mm = m.RangeMilliMeter;
  return true;
}

static bool distValida(int mm) { return mm > DIST_MIN_MM && mm < DIST_MAX_MM; }

bool alturaPessoaPresente() {
  int mm;
  return lerDistanciaMM(mm) && distValida(mm);
}

bool alturaEstavel(float &metros) {
  float v[ALTURA_AMOSTRAS];
  int n = 0;
  for (int i = 0; i < ALTURA_AMOSTRAS; i++) {
    int mm;
    if (lerDistanciaMM(mm) && distValida(mm)) v[n++] = mm;
    delay(50);
  }
  if (n < (ALTURA_AMOSTRAS * 3) / 4) return false;
  if (*std::max_element(v, v + n) - *std::min_element(v, v + n) > ALTURA_VARIACAO_MM) return false;

  float alt = (ALTURA_SENSOR_MM - mediana(v, n)) / 1000.0f;
  if (alt < ALTURA_MIN_M || alt > ALTURA_MAX_M) return false;
  metros = alt;
  return true;
}
