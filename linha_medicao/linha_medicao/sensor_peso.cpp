#include <Arduino.h>
#include <math.h>
#include "config.h"
#include "sensor_peso.h"

// Leitura direta do HX711: nunca espera sem limite, para não travar a placa.
// O chip gera uma conversão a cada 100 ms (10 amostras por segundo).
static const unsigned long INTERVALO_LEITURA_MS = 100;

static long offsetBalanca = 0;
static long ultimoBruto = 0;
static unsigned long tUltimaLeitura = 0;
static float ultimaLeitura = 0;

// Janela de estabilidade: acumula amostras sem travar o loop().
static int nAmostras = 0;
static float somaAmostras = 0;
static float minAmostra = 0;
static float maxAmostra = 0;
static unsigned long tJanela = 0;

static void janelaReiniciar() {
  nAmostras = 0;
  somaAmostras = 0;
}

// Devolve true só quando há amostra nova; não bloqueia.
static bool lerBruto(long &valor) {
  if (millis() - tUltimaLeitura < INTERVALO_LEITURA_MS) return false;
  if (digitalRead(PIN_HX_DT) == HIGH) return false;

  long v = 0;
  noInterrupts();
  for (int i = 0; i < 24; i++) {
    digitalWrite(PIN_HX_SCK, HIGH);
    delayMicroseconds(5);
    v = (v << 1) | digitalRead(PIN_HX_DT);
    digitalWrite(PIN_HX_SCK, LOW);
    delayMicroseconds(5);
  }
  digitalWrite(PIN_HX_SCK, HIGH);   // 25º pulso: canal A, ganho 128
  delayMicroseconds(5);
  digitalWrite(PIN_HX_SCK, LOW);
  interrupts();

  if (v & 0x800000) v |= 0xFF000000;

  tUltimaLeitura = millis();
  // -1 (todos os bits em 1) e os extremos são leitura inválida: o HX711 não estava pronto.
  // Antes isso entrava na tara e na pesagem e gerava o "peso fantasma".
  if (v == -1 || v == 0x7FFFFF || v == -0x800000) return false;
  ultimoBruto = v;
  valor = v;
  return true;
}

static bool esperarBruto(long &valor, unsigned long limiteMs) {
  unsigned long inicio = millis();
  while (millis() - inicio < limiteMs) {
    if (lerBruto(valor)) return true;
    delay(1);
  }
  return false;
}

bool pesoTarar() {
  // balança TEM que estar vazia aqui
  double soma = 0;
  for (int i = 0; i < 20; i++) {
    long v;
    if (!esperarBruto(v, 1000)) {
      Serial.printf("[Peso] HX711 parou na leitura %d da tara; confira DT, SCK, VCC e GND.\n", i);
      return false;
    }
    soma += v;
  }
  offsetBalanca = lround(soma / 20);
  Serial.printf("[Peso] Tara feita: %ld contagens.\n", offsetBalanca);
  ultimaLeitura = 0;
  janelaReiniciar();
  return true;
}

void pesoIniciar() {
  pinMode(PIN_HX_DT, INPUT);
  pinMode(PIN_HX_SCK, OUTPUT);
  digitalWrite(PIN_HX_SCK, LOW);
  delay(500);
  // Fio longo: o HX711 pode demorar no boot. Insiste antes de desistir (zero errado = peso fantasma).
  for (int tentativa = 1; tentativa <= 10; tentativa++) {
    if (pesoTarar()) return;
    Serial.printf("[Peso] Tara falhou (tentativa %d/10); tentando de novo.\n", tentativa);
    delay(500);
  }
  Serial.println("[Peso] ERRO: sem tara. Confira os fios do HX711 e mande T no Serial.");
}

bool pesoPessoaPresente() {
  long v;
  if (lerBruto(v)) ultimaLeitura = (v - offsetBalanca) / FATOR_BALANCA;
  return ultimaLeitura > PESO_MIN_KG;
}

// Chame a cada volta do loop(): só lê quando o HX711 tem amostra pronta.
bool pesoEstavel(float &kg) {
  long bruto;
  if (!lerBruto(bruto)) return false;

  float v = (bruto - offsetBalanca) / FATOR_BALANCA;
  ultimaLeitura = v;

  if (v < PESO_MIN_KG || v > PESO_MAX_KG) {
    janelaReiniciar();
    return false;
  }

  if (nAmostras > 0 && (max(maxAmostra, v) - min(minAmostra, v)) > PESO_VARIACAO_KG) {
    janelaReiniciar();
  }

  if (nAmostras == 0) {
    minAmostra = v;
    maxAmostra = v;
    tJanela = millis();
  }

  minAmostra = min(minAmostra, v);
  maxAmostra = max(maxAmostra, v);
  somaAmostras += v;
  nAmostras++;

  if (nAmostras < PESO_AMOSTRAS || millis() - tJanela < PESO_JANELA_MS) return false;

  kg = somaAmostras / nAmostras;
  janelaReiniciar();
  return true;
}

float pesoUltimaLeitura() {
  return ultimaLeitura;
}

long pesoUltimoBruto() {
  return ultimoBruto;
}

float pesoBruto() {
  double soma = 0;
  for (int i = 0; i < 10; i++) {
    long v;
    if (!esperarBruto(v, 1000)) return NAN;
    soma += v - offsetBalanca;
  }
  return soma / 10;
}
