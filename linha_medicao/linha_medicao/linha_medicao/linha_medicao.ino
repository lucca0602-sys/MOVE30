// ============================================================
// MOVE30 - ESP32-S3, fluxo sequencial por avaliação:
// altura -> peso -> FC repouso -> FC pós-teste.
// A avaliação é reservada pela API e retomada após reinicialização.
// ============================================================
#include <Arduino.h>
#include <Wire.h>
#include <esp_system.h>
#include <string.h>
#include "config.h"
#include "estacoes.h"
#include "api_client.h"
#include "sensor_altura.h"
#include "sensor_peso.h"
#include "sensor_fc.h"
#include "botoes.h"

static int avaliacaoId = -1;
static char etapaAtual[32] = "";
static char tipoTeste[16] = "";
static unsigned long ultimaConsulta = 0;

static void gerarMessageId(char* destino, size_t tamanho) {
  uint8_t bytes[16];
  esp_fill_random(bytes, sizeof(bytes));
  bytes[6] = (bytes[6] & 0x0F) | 0x40;
  bytes[8] = (bytes[8] & 0x3F) | 0x80;
  snprintf(destino, tamanho,
      "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",
      bytes[0], bytes[1], bytes[2], bytes[3], bytes[4], bytes[5], bytes[6], bytes[7],
      bytes[8], bytes[9], bytes[10], bytes[11], bytes[12], bytes[13], bytes[14], bytes[15]);
}

static void consultarAvaliacao() {
  if (avaliacaoId > 0 || millis() - ultimaConsulta < 1500) return;
  ultimaConsulta = millis();
  int id = -1;
  char etapa[32] = "";
  char nivel[16] = "";
  if (apiProximaAvaliacao(id, etapa, sizeof(etapa), nivel, sizeof(nivel))) {
    avaliacaoId = id;
    strlcpy(etapaAtual, etapa, sizeof(etapaAtual));
    strlcpy(tipoTeste, nivel, sizeof(tipoTeste));
    Serial.printf("Avaliação #%d reservada | nível: %s | próxima etapa: %s\n",
                  avaliacaoId, tipoTeste, etapaAtual);
  }
}

static bool travarLeitura(SessaoEstacao& s, float valor, const char* nome,
                          int casas, const char* unidade) {
  if (s.medido || avaliacaoId <= 0) return false;
  char horario[21];
  if (!apiHoraAtual(horario, sizeof(horario))) {
    Serial.println("Aguardando horário UTC via NTP; leitura ainda não foi travada.");
    return false;
  }
  s.valor = valor;
  s.assessmentId = avaliacaoId;
  s.casas = casas;
  strlcpy(s.measuredAt, horario, sizeof(s.measuredAt));
  strlcpy(s.nome, nome, sizeof(s.nome));
  strlcpy(s.unidade, unidade, sizeof(s.unidade));
  gerarMessageId(s.messageId, sizeof(s.messageId));
  s.medido = true;
  estacoesSalvar();
  return true;
}

static bool enviarPendente(SessaoEstacao& s) {
  if (!s.medido || s.assessmentId != avaliacaoId) return false;
  bool completa = false;
  char proxima[32] = "";
  if (!apiEnviarMedicao(s.assessmentId, s.messageId, s.measuredAt, s.nome,
                        s.valor, s.casas, s.unidade,
                        proxima, sizeof(proxima), completa)) return false;

  const int idEnviado = s.assessmentId;
  s = SessaoEstacao();
  estacoesSalvar();
  if (completa) {
    Serial.printf("Avaliação #%d concluída. Aguardando a próxima pessoa.\n", idEnviado);
    avaliacaoId = -1;
    etapaAtual[0] = '\0';
    tipoTeste[0] = '\0';
  } else {
    strlcpy(etapaAtual, proxima, sizeof(etapaAtual));
    Serial.printf("Próxima etapa da avaliação #%d: %s\n", idEnviado, etapaAtual);
  }
  return true;
}

static void testeLoop() {
  float v;
  switch (MODO_TESTE) {
    case 1:
      if (alturaPessoaPresente() && alturaEstavel(v)) Serial.printf("Altura: %.2f m\n", v);
      else Serial.println("Sem pessoa ou leitura instável");
      delay(500);
      break;
    case 2:
      Serial.printf("Valor bruto: %.1f\n", pesoBruto());
      delay(1000);
      break;
    case 3:
      if (pesoPessoaPresente() && pesoEstavel(v)) Serial.printf("Peso: %.1f kg\n", v);
      else Serial.println("Balança vazia ou peso instável");
      delay(500);
      break;
    case 4:
      fcAtualizar();
      if (fcStatus() == FC_PRONTO && fcResultado(v)) {
        Serial.printf("FC: %.0f bpm\n", v);
        fcReiniciar();
      } else if (fcStatus() == FC_FALHOU) {
        Serial.println("Falhou, tente de novo");
        fcReiniciar();
      }
      break;
    case 5:
      Serial.printf("Emergência: %s\n", emergenciaAcionada() ? "ACIONADA" : "solto");
      delay(300);
      break;
  }
}

static void atualizarAltura() {
  SessaoEstacao& s = estacoes[EST_ALTURA];
  if (enviarPendente(s) || s.medido) return;
  if (strcmp(etapaAtual, "height") != 0) return;
  if (!s.ocupada) {
    if (alturaPessoaPresente()) { s.ocupada = true; estacoesSalvar(); }
    return;
  }
  float valor;
  if (alturaEstavel(valor) && travarLeitura(s, valor, "height", 2, "m"))
    Serial.printf("[Altura] leitura travada: %.2f m\n", valor);
}

static void atualizarPeso() {
  SessaoEstacao& s = estacoes[EST_PESO];
  if (enviarPendente(s) || s.medido) return;
  if (strcmp(etapaAtual, "weight") != 0) return;
  if (!s.ocupada) {
    if (pesoPessoaPresente()) { s.ocupada = true; estacoesSalvar(); }
    return;
  }
  float valor;
  if (pesoEstavel(valor) && travarLeitura(s, valor, "weight", 1, "kg"))
    Serial.printf("[Peso] leitura travada: %.1f kg\n", valor);
}

static void atualizarFC() {
  SessaoEstacao& s = estacoes[EST_FC];
  // Uma pendência preserva o nome original mesmo se a resposta HTTP anterior se perdeu.
  if (enviarPendente(s)) { fcReiniciar(); return; }
  if (s.medido) return;
  const bool repouso = strcmp(etapaAtual, "heart_rate_rest") == 0;
  const bool posTeste = strcmp(etapaAtual, "heart_rate_post") == 0;
  if (!repouso && !posTeste) return;
  if (!s.ocupada) {
    if (fcDedoPresente()) { s.ocupada = true; estacoesSalvar(); }
    return;
  }
  fcAtualizar();
  if (fcStatus() == FC_PRONTO) {
    float bpm;
    const char* nome = repouso ? "heart_rate_rest" : "heart_rate_post";
    if (fcResultado(bpm) && travarLeitura(s, bpm, nome, 0, "bpm"))
      Serial.printf("[FC %s] leitura travada: %.0f bpm\n", repouso ? "repouso" : "pós-teste", bpm);
  } else if (fcStatus() == FC_FALHOU) {
    Serial.println("[FC] leitura falhou, tentando novamente");
    fcReiniciar();
  }
}

void setup() {
  Serial.begin(115200);
  botoesIniciar();
  Wire.begin(PIN_SDA, PIN_SCL);

  if (!alturaIniciar()) Serial.println("Aviso: VL53L0X não encontrado.");
  if (!fcIniciar()) Serial.println("Aviso: MAX30102 não encontrado.");
  if (MODO_TESTE == 0 || MODO_TESTE == 2 || MODO_TESTE == 3) pesoIniciar();
  if (MODO_TESTE != 0) {
    Serial.printf("MODO_TESTE = %d\n", MODO_TESTE);
    return;
  }

  apiConectarWifi();
  estacoesCarregar();
  if (!DEVICE_API_KEY[0])
    Serial.println("Configure secrets.h com a mesma chave ESP32_API_KEY do backend.");
  Serial.printf("MOVE30 pronto | dispositivo: %s\n", DEVICE_ID);
}

void loop() {
  if (MODO_TESTE != 0) { testeLoop(); return; }
  if (!apiWifiOk()) {
    static unsigned long tWifi = 0;
    if (millis() - tWifi > 5000) { tWifi = millis(); apiReconectar(); }
  }

  if (emergenciaAcionada()) {
    const bool existePendente = estacoes[EST_ALTURA].medido ||
                                estacoes[EST_PESO].medido ||
                                estacoes[EST_FC].medido;
    if (!existePendente && avaliacaoId > 0 && apiCancelarAvaliacao()) {
      Serial.printf("Avaliação #%d liberada pelo botão de emergência.\n", avaliacaoId);
      avaliacaoId = -1;
      etapaAtual[0] = '\0';
      tipoTeste[0] = '\0';
    }
    for (int i = 0; i < NUM_ESTACOES; i++) {
      if (estacoes[i].ocupada && !estacoes[i].medido) estacoes[i] = SessaoEstacao();
    }
    fcReiniciar();
    estacoesSalvar();
    delay(500);
    return;
  }

  consultarAvaliacao();
  if (avaliacaoId <= 0) return;
  atualizarAltura();
  atualizarPeso();
  atualizarFC();
}
