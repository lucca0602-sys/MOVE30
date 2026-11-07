
#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <string.h>
#include <time.h>

#include "config.h"
#include "api_client.h"

// ============================================================
// CONFIGURAÇÃO HTTP
// ============================================================

static void prepararHTTP(HTTPClient& http, const String& url) {
  http.setConnectTimeout(3000);
  http.setTimeout(5000);
  http.begin(url);

  http.addHeader("X-Device-Key", DEVICE_API_KEY);
  http.addHeader("X-Device-ID", DEVICE_ID);
}

// ============================================================
// WI-FI
// ============================================================

void apiConectarWifi() {
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  Serial.print("Conectando ao Wi-Fi");

  unsigned long t0 = millis();

  while (WiFi.status() != WL_CONNECTED &&
         millis() - t0 < 15000) {
    delay(300);
    Serial.print(".");
  }

  Serial.println(
      WiFi.status() == WL_CONNECTED
          ? "\nWi-Fi ok."
          : "\nSem Wi-Fi, tentando depois."
  );

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("IP do ESP32: ");
    Serial.println(WiFi.localIP());
  }

  configTime(0, 0, "pool.ntp.org", "time.google.com");
}

bool apiWifiOk() {
  return WiFi.status() == WL_CONNECTED;
}

void apiReconectar() {
  // WiFi.reconnect() falha com "sta is connecting" e pode nunca sair desse estado
  // depois que o roteador cai. Recomeçar a conexão resolve sem reiniciar a placa.
  Serial.println("[Wi-Fi] Sem conexao; tentando conectar de novo.");
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASS);
}

// ============================================================
// HORÁRIO UTC
// ============================================================

bool apiHoraAtual(char* destino, size_t tamanho) {
  if (!destino || tamanho < 21) {
    return false;
  }

  time_t agora = time(nullptr);

  if (agora < 1700000000) {
    return false;
  }

  struct tm utc;

  if (!gmtime_r(&agora, &utc)) {
    return false;
  }

  return strftime(
      destino,
      tamanho,
      "%Y-%m-%dT%H:%M:%SZ",
      &utc
  ) > 0;
}

// ============================================================
// CONSULTA A PRÓXIMA AVALIAÇÃO
// ============================================================

bool apiProximaAvaliacao(
    int& assessmentId,
    char* proxima,
    size_t tamanhoProxima,
    char* tipoTeste,
    size_t tamanhoTipo) {

  // A consulta se repete a cada 1,5 s: só avisa quando a situação muda.
  static int ultimaSituacao = 0;

  if (!apiWifiOk() || !DEVICE_API_KEY[0]) {
    if (ultimaSituacao != -1000) {
      ultimaSituacao = -1000;
      Serial.println("[API] Sem Wi-Fi ou sem chave; consulta de avaliacao suspensa.");
    }
    return false;
  }

  HTTPClient http;

  prepararHTTP(
      http,
      String(API_URL) +
          "/api/v1/hardware/assessments/next"
  );

  int code = http.GET();
  String response = code > 0 ? http.getString() : String();

  http.end();

  if (code != 200) {
    if (ultimaSituacao != code) {
      ultimaSituacao = code;

      if (code < 0) {
        Serial.printf(
            "[API] Backend inacessivel em %s: %s\n",
            API_URL,
            HTTPClient::errorToString(code).c_str()
        );
      } else {
        Serial.printf("[API] Consulta de avaliacao -> HTTP %d\n", code);
        Serial.println(response);
      }
    }

    return false;
  }

  JsonDocument doc;

  if (deserializeJson(doc, response)) {
    Serial.println("[API] Resposta invalida na consulta de avaliacao.");
    return false;
  }

  if (strcmp(doc["status"] | "", "active") != 0) {
    if (ultimaSituacao != 200) {
      ultimaSituacao = 200;
      Serial.println("[API] Backend ok; aguardando cadastro.");
    }
    return false;
  }

  ultimaSituacao = 0;

  assessmentId = doc["assessment_id"] | -1;

  const char* step =
      doc["next_measurement"] | "";

  const char* level =
      doc["tipo_teste"] | "";

  if (assessmentId <= 0 || !step[0]) {
    return false;
  }

  strlcpy(proxima, step, tamanhoProxima);

  if (tipoTeste && tamanhoTipo) {
    strlcpy(tipoTeste, level, tamanhoTipo);
  }

  return true;
}

// ============================================================
// ENVIO DE MEDIÇÃO
// ============================================================

ApiEnvio apiEnviarMedicao(
    int assessmentId,
    const char* messageId,
    const char* measuredAt,
    const char* nome,
    float valor,
    int casas,
    const char* unidade,
    char* proxima,
    size_t tamanhoProxima,
    bool& completa) {

  if (!apiWifiOk() || !DEVICE_API_KEY[0]) {
    Serial.printf(
        "[API] Sem Wi-Fi ou sem chave; %s fica guardada para reenvio.\n",
        nome
    );
    return API_ENVIO_TENTAR_DE_NOVO;
  }

  HTTPClient http;

  prepararHTTP(
      http,
      String(API_URL) +
          "/api/v1/hardware/measurements"
  );

  http.addHeader("Content-Type", "application/json");

  JsonDocument doc;

  doc["device_id"] = DEVICE_ID;
  doc["assessment_id"] = assessmentId;
  doc["message_id"] = messageId;
  doc["measured_at"] = measuredAt;

  JsonArray readings =
      doc["measurements"].to<JsonArray>();

  JsonObject reading =
      readings.add<JsonObject>();

  reading["name"] = nome;
  reading["value"] = valor;
  reading["unit"] = unidade;

  String body;

  serializeJson(doc, body);

  int code = http.POST(body);
  String response = code > 0 ? http.getString() : String();

  http.end();

  if (code != 202) {
    if (code < 0) {
      Serial.printf(
          "[API] POST %s falhou: %s; nova tentativa em breve.\n",
          nome,
          HTTPClient::errorToString(code).c_str()
      );
    } else {
      Serial.printf(
          "[API] POST %s=%.*f -> HTTP %d\n",
          nome,
          casas,
          valor,
          code
      );
    }

    if (response.length()) {
      Serial.println(response);
    }

    // 409 e 422 são recusas do servidor; o resto pode ser temporário.
    return (code == 409 || code == 422)
        ? API_ENVIO_REJEITADO
        : API_ENVIO_TENTAR_DE_NOVO;
  }

  JsonDocument result;

  if (deserializeJson(result, response)) {
    Serial.printf("[API] Resposta invalida ao enviar %s.\n", nome);
    return API_ENVIO_TENTAR_DE_NOVO;
  }

  completa = result["complete"] | false;

  const char* step =
      result["next_measurement"] | "";

  if (!completa && !step[0]) {
    Serial.printf("[API] Resposta sem proxima etapa ao enviar %s.\n", nome);
    return API_ENVIO_TENTAR_DE_NOVO;
  }

  if (proxima && tamanhoProxima) {
    strlcpy(proxima, step, tamanhoProxima);
  }

  Serial.printf(
      "Avaliacao #%d: %s confirmada (%.*f %s)\n",
      assessmentId,
      nome,
      casas,
      valor,
      unidade
  );

  return API_ENVIO_OK;
}

// ============================================================
// CANCELAMENTO DE AVALIAÇÃO
// ============================================================

bool apiCancelarAvaliacao() {
  if (!apiWifiOk() || !DEVICE_API_KEY[0]) {
    return false;
  }

  HTTPClient http;

  prepararHTTP(
      http,
      String(API_URL) +
          "/api/v1/hardware/assessments/current/cancel"
  );

  int code = http.POST("");

  http.end();

  return code == 204;
}

// ============================================================
// TESTE DE COMUNICAÇÃO COM O BACKEND
// Consulta somente GET /health.
// Não reserva avaliações nem envia medições.
// ============================================================

bool apiTestarConexao() {
  if (!apiWifiOk()) {
    Serial.println("ERRO: Wi-Fi desconectado.");
    return false;
  }

  HTTPClient http;

  String url = String(API_URL) + "/health";

  Serial.printf(
      "URL do teste: %s\n",
      url.c_str()
  );

  Serial.println("Iniciando requisicao HTTP...");

  http.setTimeout(5000);

  if (!http.begin(url)) {
    Serial.println(
        "ERRO: nao foi possivel iniciar HTTP."
    );

    return false;
  }

  Serial.println("Enviando GET...");

  int code = http.GET();

  Serial.printf("HTTP: %d\n", code);

  if (code > 0) {
    String response = http.getString();

    Serial.println("Resposta do backend:");
    Serial.println(response);

  } else {
    Serial.printf(
        "Falha HTTP: %s\n",
        HTTPClient::errorToString(code).c_str()
    );
  }

  http.end();

  if (code == 200) {
    Serial.println("BACKEND OK");
    return true;
  }

  Serial.println("BACKEND NAO CONFIRMADO");

  return false;
}
