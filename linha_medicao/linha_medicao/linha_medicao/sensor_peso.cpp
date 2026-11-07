#include <Arduino.h>
#include <HX711.h>
#include "config.h"
#include "util.h"
#include "sensor_peso.h"

static HX711 balanca;

void pesoIniciar() {
  balanca.begin(PIN_HX_DT, PIN_HX_SCK);
  balanca.set_scale(FATOR_BALANCA);
  delay(500);
  balanca.tare(20);                 // balança TEM que estar vazia aqui
}

bool pesoPessoaPresente() {
  return balanca.is_ready() && balanca.get_units(3) > PESO_MIN_KG;
}

bool pesoEstavel(float &kg) {
  float v[PESO_AMOSTRAS];
  for (int i = 0; i < PESO_AMOSTRAS; i++) v[i] = balanca.get_units(1);
  float mx = *std::max_element(v, v + PESO_AMOSTRAS);
  float mn = *std::min_element(v, v + PESO_AMOSTRAS);
  if (mx - mn > PESO_VARIACAO_KG) return false;
  float p = mediana(v, PESO_AMOSTRAS);
  if (p < PESO_MIN_KG || p > PESO_MAX_KG) return false;
  kg = p;
  return true;
}

float pesoBruto() {
  balanca.set_scale(1.0f);
  float v = balanca.get_value(10);
  balanca.set_scale(FATOR_BALANCA);
  return v;
}
