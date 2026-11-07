#include <Arduino.h>
#include <Wire.h>
#include <MAX30105.h>
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

// Detector de batidas. O checkForBeat da biblioteca descarta pulsos com
// variação acima de 1000, e o sinal real deste sensor chega a cerca de 2500.
static const float FC_AMPLITUDE_MIN = 15;
static const unsigned long FC_INTERVALO_MIN_MS = 270;   // cerca de 220 bpm

static bool detectorIniciado = false;
static float sinalRapido = 0;
static float sinalLento = 0;
static bool sinalSubindo = true;
static float sinalExtremo = 0;
static unsigned long tExtremo = 0;
static float amplitudeMedia = 0;

static void detectorReiniciar() {
  detectorIniciado = false;
  sinalSubindo = true;
  sinalExtremo = 0;
  amplitudeMedia = 0;
}

// Devolve true quando confirma uma batida; tBatida é o instante do pico.
static bool detectarBatida(long ir, unsigned long agora, unsigned long &tBatida) {
  if (!detectorIniciado) {
    detectorIniciado = true;
    sinalRapido = ir;
    sinalLento = ir;
  }

  sinalRapido += (ir - sinalRapido) * 0.25f;
  sinalLento += (ir - sinalLento) * 0.02f;
  float ac = sinalRapido - sinalLento;

  if (!sinalSubindo) {
    if (ac < sinalExtremo) {
      sinalExtremo = ac;
    } else if (ac > sinalExtremo * 0.4f) {
      sinalSubindo = true;
      sinalExtremo = ac;
    }
    return false;
  }

  if (ac > sinalExtremo) {
    sinalExtremo = ac;
    tExtremo = agora;
    return false;
  }

  if (sinalExtremo <= FC_AMPLITUDE_MIN || ac >= sinalExtremo * 0.4f) {
    return false;
  }

  // O pico terminou: conta só se tiver tamanho e distância de uma batida real.
  bool batida =
      sinalExtremo >= amplitudeMedia * 0.4f &&
      (tUltimaBatida == 0 || tExtremo - tUltimaBatida >= FC_INTERVALO_MIN_MS);

  if (batida) {
    amplitudeMedia = amplitudeMedia == 0
        ? sinalExtremo
        : amplitudeMedia * 0.8f + sinalExtremo * 0.2f;
    tBatida = tExtremo;
  }

  sinalSubindo = false;
  sinalExtremo = ac;
  return batida;
}

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
  detectorReiniciar();
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
        detectorReiniciar();
      }
      break;

    case FC_COLETANDO:
      if (ir < FC_DEDO_LIMIAR) {
        Serial.printf("[FC] Falha: sinal IR baixo (%ld)\n", ir);
        estado = FC_FALHOU;
        break;
      }
      {
        bool novaBatida = false;
        unsigned long tBatida = 0;
        if (detectarBatida(ir, millis(), tBatida)) {
          if (tUltimaBatida > 0) {
            float b = 60000.0f / (tBatida - tUltimaBatida);
            if (b > 40 && b < 220 && nBpms < 40) {
              bpms[nBpms++] = b;
              novaBatida = true;
            }
          }
          tUltimaBatida = tBatida;
        }

        const unsigned long decorrido = millis() - tMarco;

        // Termina assim que juntar FC_BATIDAS_ALVO leituras. Descarta as que fogem
        // da mediana (batida falsa ou perdida com o dedo tremendo) e faz a média do resto.
        if (novaBatida && nBpms >= FC_BATIDAS_ALVO) {
          const float med = mediana(bpms, nBpms);
          float soma = 0;
          int usadas = 0;
          for (int i = 0; i < nBpms; i++) {
            if (fabsf(bpms[i] - med) <= med * FC_TOLERANCIA) { soma += bpms[i]; usadas++; }
          }
          bpmFinal = roundf(usadas >= 3 ? soma / usadas : med);
          Serial.printf("[FC] Pronto em %.1f s: %.0f bpm (%d de %d batidas usadas)\n",
                        decorrido / 1000.0f, bpmFinal, usadas, nBpms);
          estado = FC_PRONTO;
        } else if (decorrido >= FC_JANELA_MS) {
          Serial.printf("[FC] Falha: poucas batidas (%d)\n", nBpms);
          estado = FC_FALHOU;
        }
      }
      break;

    case FC_PRONTO:
    case FC_FALHOU:
      break;
  }
}
