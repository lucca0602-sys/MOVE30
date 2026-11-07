#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <string.h>
#include <time.h>
#include "config.h"
#include "api_client.h"

static void prepararHTTP(HTTPClient& http, const String& url) {
  http.setTimeout(5000);
  http.begin(url);
  http.addHeader("X-Device-Key", DEVICE_API_KEY);
  http.addHeader("X-Device-ID", DEVICE_ID);
}

void apiConectarWifi() {
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Conectando ao Wi-Fi");
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 15000) {
    delay(300);
    Serial.print(".");
  }
  Serial.println(WiFi.status() == WL_CONNECTED
      ? "\nWi-Fi ok."
      : "\nSem Wi-Fi, tentando depois.");
  configTime(0, 0, "pool.ntp.org", "time.google.com");
}

bool apiWifiOk() { return WiFi.status() == WL_CONNECTED; }
void apiReconectar() { WiFi.reconnect(); }

bool apiHoraAtual(char* destino, size_t tamanho) {
  if (!destino || tamanho < 21) return false;
  time_t agora = time(nullptr);
  if (agora < 1700000000) return false;
  struct tm utc;
  if (!gmtime_r(&agora, &utc)) return false;
  return strftime(destino, tamanho, "%Y-%m-%dT%H:%M:%SZ", &utc) > 0;
}

bool apiProximaAvaliacao(int& assessmentId, char* proxima, size_t tamanhoProxima,
                         char* tipoTeste, size_t tamanhoTipo) {
  if (!apiWifiOk() || !DEVICE_API_KEY[0]) return false;
  HTTPClient http;
  prepararHTTP(http, String(API_URL) + "/api/v1/hardware/assessments/next");
  int code = http.GET();
  String response = http.getString();
  http.end();
  if (code != 200) return false;

  JsonDocument doc;
  if (deserializeJson(doc, response) || strcmp(doc["status"] | "", "active") != 0) return false;
  assessmentId = doc["assessment_id"] | -1;
  const char* step = doc["next_measurement"] | "";
  const char* level = doc["tipo_teste"] | "";
  if (assessmentId <= 0 || !step[0]) return false;
  strlcpy(proxima, step, tamanhoProxima);
  if (tipoTeste && tamanhoTipo) strlcpy(tipoTeste, level, tamanhoTipo);
  return true;
}

bool apiEnviarMedicao(int assessmentId, const char* messageId,
                      const char* measuredAt, const char* nome,
                      float valor, int casas, const char* unidade,
                      char* proxima, size_t tamanhoProxima, bool& completa) {
  if (!apiWifiOk() || !DEVICE_API_KEY[0]) return false;
  HTTPClient http;
  prepararHTTP(http, String(API_URL) + "/api/v1/hardware/measurements");
  http.addHeader("Content-Type", "application/json");

  JsonDocument doc;
  doc["device_id"] = DEVICE_ID;
  doc["assessment_id"] = assessmentId;
  doc["message_id"] = messageId;
  doc["measured_at"] = measuredAt;
  JsonArray readings = doc["measurements"].to<JsonArray>();
  JsonObject reading = readings.add<JsonObject>();
  reading["name"] = nome;
  reading["value"] = valor;
  reading["unit"] = unidade;
  String body;
  serializeJson(doc, body);

  int code = http.POST(body);
  String response = http.getString();
  http.end();
  if (code != 202) {
    Serial.printf("POST %s=%.*f -> HTTP %d\n", nome, casas, valor, code);
    if (response.length()) Serial.println(response);
    return false;
  }

  JsonDocument result;
  if (deserializeJson(result, response)) return false;
  completa = result["complete"] | false;
  const char* step = result["next_measurement"] | "";
  if (!completa && !step[0]) return false;
  if (proxima && tamanhoProxima) strlcpy(proxima, step, tamanhoProxima);
  Serial.printf("Avaliação #%d: %s confirmada (%.*f %s)\n", assessmentId, nome, casas, valor, unidade);
  return true;
}

bool apiCancelarAvaliacao() {
  if (!apiWifiOk() || !DEVICE_API_KEY[0]) return false;
  HTTPClient http;
  prepararHTTP(http, String(API_URL) + "/api/v1/hardware/assessments/current/cancel");
  int code = http.POST("");
  http.end();
  return code == 204;
}
