#include <Arduino.h>
#include <Wire.h>
#include <MAX30105.h>
#include <heartRate.h>
#include "config.h"
#include "util.h"
#include "sensor_fc.h"

static MAX30105 sensor;
static FcEstado estado = FC_OCIOSO;
static unsigned long tMarco = 0;
static float bpms[40];
static int nBpms = 0;
static unsigned long tUltimaBatida = 0;
static float bpmFinal = 0;

bool fcIniciar() {
  if (!sensor.begin(Wire, I2C_SPEED_FAST)) return false;
  sensor.setup(0x1F, 4, 2, 400, 411, 4096);
  return true;
}

bool fcDedoPresente() { return sensor.getIR() >= FC_DEDO_LIMIAR; }
FcEstado fcStatus() { return estado; }

void fcReiniciar() {
  estado = FC_OCIOSO;
  nBpms = 0;
  tUltimaBatida = 0;
}

bool fcResultado(float &bpm) {
  if (estado != FC_PRONTO) return false;
  bpm = bpmFinal;
  return true;
}

void fcAtualizar() {
  long ir = sensor.getIR();

  switch (estado) {

    case FC_OCIOSO:
      if (ir >= FC_DEDO_LIMIAR) { estado = FC_ASSENTANDO; tMarco = millis(); }
      break;

    case FC_ASSENTANDO:
      if (ir < FC_DEDO_LIMIAR) { estado = FC_OCIOSO; break; }
      if (millis() - tMarco >= FC_ASSENTAR_MS) {
        estado = FC_COLETANDO;
        tMarco = millis();
        nBpms = 0;
        tUltimaBatida = 0;
      }
      break;

    case FC_COLETANDO:
      if (ir < FC_DEDO_LIMIAR) { estado = FC_FALHOU; break; }
      if (checkForBeat(ir)) {
        unsigned long agora = millis();
        if (tUltimaBatida > 0) {
          float b = 60000.0f / (agora - tUltimaBatida);
          if (b > 40 && b < 220 && nBpms < 40) bpms[nBpms++] = b;
        }
        tUltimaBatida = agora;
      }
      if (millis() - tMarco >= FC_JANELA_MS) {
        if (nBpms < FC_MIN_BATIDAS) { estado = FC_FALHOU; break; }
        float ordenado[40];
        for (int i = 0; i < nBpms; i++) ordenado[i] = bpms[i];
        std::sort(ordenado, ordenado + nBpms);
        float q1 = ordenado[nBpms / 4], q3 = ordenado[(3 * nBpms) / 4];
        if (q3 - q1 > FC_VARIACAO_MAX) { estado = FC_FALHOU; break; }
        bpmFinal = roundf(mediana(bpms, nBpms));
        estado = FC_PRONTO;
      }
      break;

    case FC_PRONTO:
    case FC_FALHOU:
      break;
  }
}
