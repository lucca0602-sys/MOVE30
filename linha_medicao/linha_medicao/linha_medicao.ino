// ============================================================
// MOVE30 - ESP32-S3
// Fluxo sequencial por avaliação:
// peso -> FC repouso -> corrida -> FC pós-teste.
// A altura é digitada no cadastro.
//
// MODO_TESTE = 6:
// testa Wi-Fi e comunicação com o backend via GET /health.
// Não reserva avaliações nem envia medições.
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

// ============================================================
// GERA ID ÚNICO PARA CADA MEDIÇÃO
// ============================================================

static void gerarMessageId(char* destino, size_t tamanho) {
  uint8_t bytes[16];
  esp_fill_random(bytes, sizeof(bytes));

  bytes[6] = (bytes[6] & 0x0F) | 0x40;
  bytes[8] = (bytes[8] & 0x3F) | 0x80;

  snprintf(
      destino,
      tamanho,
      "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",
      bytes[0], bytes[1], bytes[2], bytes[3],
      bytes[4], bytes[5], bytes[6], bytes[7],
      bytes[8], bytes[9], bytes[10], bytes[11],
      bytes[12], bytes[13], bytes[14], bytes[15]
  );
}

// ============================================================
// CONSULTA A PRÓXIMA AVALIAÇÃO
// ============================================================

static void consultarAvaliacao() {
  if (avaliacaoId > 0 || millis() - ultimaConsulta < 1500) {
    return;
  }

  ultimaConsulta = millis();

  int id = -1;
  char etapa[32] = "";
  char nivel[16] = "";

  if (apiProximaAvaliacao(
          id,
          etapa,
          sizeof(etapa),
          nivel,
          sizeof(nivel))) {

    avaliacaoId = id;

    strlcpy(etapaAtual, etapa, sizeof(etapaAtual));
    strlcpy(tipoTeste, nivel, sizeof(tipoTeste));

    Serial.printf(
        "Avaliação #%d reservada | nível: %s | próxima etapa: %s\n",
        avaliacaoId,
        tipoTeste,
        etapaAtual
    );
  }
}

// ============================================================
// TRAVA UMA LEITURA PARA ENVIO
// ============================================================

static bool travarLeitura(
    SessaoEstacao& s,
    float valor,
    const char* nome,
    int casas,
    const char* unidade) {

  if (s.medido || avaliacaoId <= 0) {
    return false;
  }

  char horario[21];

  if (!apiHoraAtual(horario, sizeof(horario))) {
    Serial.println(
        "Aguardando horário UTC via NTP; leitura ainda não foi travada."
    );
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

// ============================================================
// ENVIA UMA MEDIÇÃO PENDENTE
// ============================================================

static bool enviarPendente(SessaoEstacao& s) {
  static unsigned long ultimoEnvio = 0;

  if (!s.medido) {
    return false;
  }

  if (ultimoEnvio != 0 && millis() - ultimoEnvio < API_REENVIO_MS) {
    return false;
  }

  ultimoEnvio = millis();

  bool completa = false;
  char proxima[32] = "";

  // O servidor decide a quem a leitura pertence: repetição já gravada volta
  // confirmada e leitura de outra avaliação volta recusada.
  const ApiEnvio resultado = apiEnviarMedicao(
      s.assessmentId,
      s.messageId,
      s.measuredAt,
      s.nome,
      s.valor,
      s.casas,
      s.unidade,
      proxima,
      sizeof(proxima),
      completa);

  if (resultado == API_ENVIO_TENTAR_DE_NOVO) {
    return false;
  }

  ultimoEnvio = 0;

  const int idEnviado = s.assessmentId;

  s = SessaoEstacao();
  estacoesSalvar();

  if (resultado == API_ENVIO_REJEITADO) {
    Serial.printf(
        "Leitura da avaliação #%d recusada e descartada; consultando a etapa atual.\n",
        idEnviado
    );

    avaliacaoId = -1;
    etapaAtual[0] = '\0';
    tipoTeste[0] = '\0';

    return true;
  }

  // Repetição de uma avaliação anterior não muda a etapa da atual.
  if (idEnviado != avaliacaoId) {
    return true;
  }

  if (completa) {
    Serial.printf(
        "Avaliação #%d concluída. Aguardando a próxima pessoa.\n",
        idEnviado
    );

    avaliacaoId = -1;
    etapaAtual[0] = '\0';
    tipoTeste[0] = '\0';

  } else {
    strlcpy(etapaAtual, proxima, sizeof(etapaAtual));

    Serial.printf(
        "Próxima etapa da avaliação #%d: %s\n",
        idEnviado,
        etapaAtual
    );
  }

  return true;
}

// ============================================================
// TESTES INDIVIDUAIS DOS SENSORES
// MODO_TESTE = 1 A 5
// ============================================================

static void testeLoop() {
  float v;

  switch (MODO_TESTE) {

    case 1:
      if (alturaPessoaPresente() && alturaEstavel(v)) {
        Serial.printf("Altura: %.2f m\n", v);
      } else {
        Serial.println("Sem pessoa ou leitura instável");
      }

      delay(500);
      break;

    case 2:
      Serial.printf("Valor bruto: %.1f\n", pesoBruto());
      delay(1000);
      break;

    case 3: {
      static unsigned long tAviso = 0;

      if (pesoEstavel(v)) {
        Serial.printf("Peso: %.1f kg\n", v);
        tAviso = millis();

      } else if (millis() - tAviso > 2000) {
        Serial.println("Balança vazia ou peso instável");
        tAviso = millis();
      }

      break;
    }

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
      Serial.printf(
          "Emergência: %s\n",
          emergenciaAcionada() ? "ACIONADA" : "solto"
      );

      delay(300);
      break;
  }
}

// ============================================================
// ESTAÇÃO DE ALTURA
// ============================================================

static void atualizarAltura() {
  SessaoEstacao& s = estacoes[EST_ALTURA];

  if (enviarPendente(s) || s.medido) {
    return;
  }

  if (strcmp(etapaAtual, "height") != 0) {
    return;
  }

  if (!s.ocupada) {
    if (alturaPessoaPresente()) {
      s.ocupada = true;
      estacoesSalvar();
    }

    return;
  }

  float valor;

  if (alturaEstavel(valor) &&
      travarLeitura(s, valor, "height", 2, "m")) {

    Serial.printf("[Altura] leitura travada: %.2f m\n", valor);
  }
}

// ============================================================
// ESTAÇÃO DE PESO
// ============================================================

static void atualizarPeso() {
  SessaoEstacao& s = estacoes[EST_PESO];

  if (enviarPendente(s) || s.medido) {
    return;
  }

  if (strcmp(etapaAtual, "weight") != 0) {
    return;
  }

  // Mostra o que a balança lê enquanto a etapa espera uma leitura estável.
  static unsigned long tAviso = 0;

  if (millis() - tAviso > 1000) {
    tAviso = millis();
    Serial.printf(
        "[Peso] Lendo: %.3f kg | contagens: %ld\n",
        pesoUltimaLeitura(),
        pesoUltimoBruto()
    );
  }

  if (!s.ocupada) {
    if (pesoPessoaPresente()) {
      s.ocupada = true;
      estacoesSalvar();
    }

    return;
  }

  float valor;

  if (pesoEstavel(valor) &&
      travarLeitura(s, valor, "weight", 1, "kg")) {

    Serial.printf("[Peso] leitura travada: %.1f kg\n", valor);
  }
}

// ============================================================
// TRAVA DA CORRIDA
// A corrida acontece entre as duas FCs. A FC pós-teste só começa
// depois de o dedo sair do sensor e passar o tempo mínimo.
// ============================================================

static bool corridaConcluida() {
  static int avaliacaoLiberada = -1;
  static int avaliacaoEmEspera = -1;
  static unsigned long tInicio = 0;
  static bool dedoSaiu = false;

  if (avaliacaoLiberada == avaliacaoId) {
    return true;
  }

  if (avaliacaoEmEspera != avaliacaoId) {
    avaliacaoEmEspera = avaliacaoId;
    tInicio = millis();
    dedoSaiu = false;

    fcReiniciar();

    Serial.println("[FC] Retire o dedo do sensor e faça a corrida.");
  }

  if (!fcDedoPresente()) {
    dedoSaiu = true;
  }

  if (!dedoSaiu || millis() - tInicio < FC_POS_ESPERA_MS) {
    return false;
  }

  avaliacaoLiberada = avaliacaoId;

  Serial.println("[FC] Ao terminar a corrida, coloque o dedo no sensor.");

  return true;
}

// ============================================================
// TARA DA BALANÇA
// Comando "t" no Serial. A balança precisa estar vazia.
// ============================================================

static void processarComandoTara() {
  while (Serial.available()) {
    const char comando = Serial.read();

    if (comando != 't' && comando != 'T') {
      continue;
    }

    if (estacoes[EST_PESO].medido) {
      Serial.println("[Peso] Tara recusada: há leitura aguardando envio.");

    } else if (pesoPessoaPresente()) {
      Serial.println("[Peso] Tara recusada: a balança não está vazia.");

    } else if (pesoTarar()) {
      Serial.println("[Peso] Tara refeita.");
    }
  }
}

// ============================================================
// ESTAÇÃO DE FREQUÊNCIA CARDÍACA
// ============================================================

static void atualizarFC() {
  SessaoEstacao& s = estacoes[EST_FC];

  // Preserva a medição pendente se uma resposta HTTP anterior se perdeu.
  if (enviarPendente(s)) {
    fcReiniciar();
    return;
  }

  if (s.medido) {
    return;
  }

  const bool repouso =
      strcmp(etapaAtual, "heart_rate_rest") == 0;

  const bool posTeste =
      strcmp(etapaAtual, "heart_rate_post") == 0;

  if (!repouso && !posTeste) {
    return;
  }

  if (posTeste && !corridaConcluida()) {
    return;
  }

  if (!s.ocupada) {
    if (fcDedoPresente()) {
      s.ocupada = true;
      estacoesSalvar();
    }

    return;
  }

  fcAtualizar();

  if (fcStatus() == FC_PRONTO) {
    float bpm;

    const char* nome =
        repouso ? "heart_rate_rest" : "heart_rate_post";

    if (fcResultado(bpm) &&
        travarLeitura(s, bpm, nome, 0, "bpm")) {

      Serial.printf(
          "[FC %s] leitura travada: %.0f bpm\n",
          repouso ? "repouso" : "pós-teste",
          bpm
      );
    }

  } else if (fcStatus() == FC_FALHOU) {
    Serial.println("[FC] leitura falhou, tentando novamente");
    fcReiniciar();
  }
}

// ============================================================
// DIAGNÓSTICO DO BARRAMENTO I2C
// O MAX30102 responde em 0x57 e o VL53L0X em 0x29.
// ============================================================

static void listarDispositivosI2C() {
  int encontrados = 0;

  Wire.setClock(100000);

  Serial.printf("[I2C] Procurando dispositivos (SDA=%d, SCL=%d)...\n", PIN_SDA, PIN_SCL);

  for (uint8_t endereco = 1; endereco < 127; endereco++) {
    Wire.beginTransmission(endereco);

    if (Wire.endTransmission() == 0) {
      Serial.printf("[I2C] Dispositivo em 0x%02X\n", endereco);
      encontrados++;
    }
  }

  if (encontrados == 0) {
    Serial.println("[I2C] Nenhum dispositivo: confira SDA, SCL, 3V3 e GND.");
  }
}

// ============================================================
// INICIALIZAÇÃO
// ============================================================

void setup() {
  Serial.begin(115200);

  delay(1000);

  Serial.println();
  Serial.println("================================");
  Serial.println("       MOVE30 - ESP32-S3");
  Serial.println("================================");

  Serial.printf("MODO_TESTE = %d\n", MODO_TESTE);

  botoesIniciar();

  Wire.begin(PIN_SDA, PIN_SCL);

  // Inicializa o sensor de altura quando necessário.
  if ((USAR_ALTURA || MODO_TESTE == 1) && !alturaIniciar()) {
    Serial.println("Aviso: VL53L0X não encontrado.");
  }

  // Inicializa o sensor de frequência cardíaca quando necessário.
  Serial.println("Iniciando sensor de batimentos...");
  Serial.flush();

  if ((USAR_FC || MODO_TESTE == 4) && !fcIniciar()) {
    Serial.println("Aviso: MAX30102 não encontrado.");
    listarDispositivosI2C();
  }

  Serial.println("Iniciando balança...");
  Serial.flush();

  // A balança só inicia quando for utilizada.
  if ((MODO_TESTE == 0 && USAR_PESO) ||
      MODO_TESTE == 2 ||
      MODO_TESTE == 3) {

    pesoIniciar();
  }

  // ----------------------------------------------------------
  // MODO 6: TESTE DE COMUNICAÇÃO COM O BACKEND
  // GET /health não reserva avaliações nem envia medições.
  // ----------------------------------------------------------

  if (MODO_TESTE == 6) {
    Serial.println();
    Serial.println("[TESTE 6] Teste de comunicação com o backend");

    Serial.println("[TESTE 6] Conectando ao Wi-Fi...");
    apiConectarWifi();

    if (apiWifiOk()) {
      Serial.println("[TESTE 6] Wi-Fi conectado.");
      Serial.println("[TESTE 6] Testando GET /health...");

      bool sucesso = apiTestarConexao();

      if (sucesso) {
        Serial.println("[TESTE 6] BACKEND OK.");
      } else {
        Serial.println("[TESTE 6] Falha no teste do backend.");
      }

    } else {
      Serial.println("[TESTE 6] Wi-Fi indisponível.");
      Serial.println("[TESTE 6] Backend não testado.");
    }

    Serial.println("[TESTE 6] Teste finalizado.");
    return;
  }

  // Outros modos de teste não iniciam o fluxo de avaliações.
  if (MODO_TESTE != 0) {
    Serial.printf("Modo de teste de sensor: %d\n", MODO_TESTE);
    return;
  }

  // ----------------------------------------------------------
  // MODO NORMAL DE OPERAÇÃO
  // ----------------------------------------------------------

  Serial.println("Conectando ao Wi-Fi...");
  apiConectarWifi();

  estacoesCarregar();

  // Sensor de altura desligado: leitura antiga guardada nunca seria enviada.
  if (!USAR_ALTURA && estacoes[EST_ALTURA].medido) {
    estacoes[EST_ALTURA] = SessaoEstacao();
    estacoesSalvar();
  }

  if (!DEVICE_API_KEY[0]) {
    Serial.println(
        "Configure secrets.h com a mesma chave ESP32_API_KEY do backend."
    );
  }

  Serial.printf(
      "MOVE30 pronto | dispositivo: %s\n",
      DEVICE_ID
  );
}

// ============================================================
// LOOP PRINCIPAL
// ============================================================

void loop() {

  // No modo 6, o teste é feito uma vez no setup().
  // Não consulta avaliações nem executa leituras.
  if (MODO_TESTE == 6) {
    delay(1000);
    return;
  }

  if ((MODO_TESTE == 0 && USAR_PESO) ||
      MODO_TESTE == 2 ||
      MODO_TESTE == 3) {

    processarComandoTara();
  }

  // Modos de teste dos sensores.
  if (MODO_TESTE != 0) {
    testeLoop();
    return;
  }

  // Reconexão automática ao Wi-Fi no modo normal.
  static unsigned long tWifi = 0;
  static bool wifiCaiu = false;

  if (apiWifiOk()) {
    if (wifiCaiu) {
      wifiCaiu = false;
      Serial.println("[Wi-Fi] Conexao restabelecida.");
    }
    tWifi = millis();

  } else {
    wifiCaiu = true;

    if (millis() - tWifi > WIFI_REINICIO_MS) {
      tWifi = millis();
      apiReconectar();
    }
  }

  // ----------------------------------------------------------
  // BOTÃO DE EMERGÊNCIA
  // ----------------------------------------------------------

  if (emergenciaAcionada()) {
    const bool existePendente =
        estacoes[EST_ALTURA].medido ||
        estacoes[EST_PESO].medido ||
        estacoes[EST_FC].medido;

    if (!existePendente &&
        avaliacaoId > 0 &&
        apiCancelarAvaliacao()) {

      Serial.printf(
          "Avaliação #%d liberada pelo botão de emergência.\n",
          avaliacaoId
      );

      avaliacaoId = -1;
      etapaAtual[0] = '\0';
      tipoTeste[0] = '\0';

    } else if (existePendente) {
      Serial.println(
          "Emergência: há leitura aguardando envio; solte o botão para enviá-la."
      );
    }

    for (int i = 0; i < NUM_ESTACOES; i++) {
      if (estacoes[i].ocupada && !estacoes[i].medido) {
        estacoes[i] = SessaoEstacao();
      }
    }

    fcReiniciar();
    estacoesSalvar();

    delay(500);
    return;
  }

  // ----------------------------------------------------------
  // FLUXO NORMAL DAS AVALIAÇÕES
  // ----------------------------------------------------------

  consultarAvaliacao();

  if (USAR_ALTURA) {
    atualizarAltura();
  }

  if (USAR_PESO) {
    atualizarPeso();
  }

  if (USAR_FC) {
    atualizarFC();
  }
}