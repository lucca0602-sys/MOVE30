
#pragma once

// ============================================================
// CONFIGURACAO DA ESP32-S3 - MOVE30
// ============================================================

#define API_URL "http://172.15.3.139:8002"
#define DEVICE_ID  "move30-esp32-01"

// Chave de autenticacao usada pelo modo normal.
// O teste GET /health nao precisa dessa chave.
// Wi-Fi e chave ficam em secrets.h, fora do controle de versao.
#if __has_include("secrets.h")
  #include "secrets.h"
#else
  #define DEVICE_API_KEY ""
  #define WIFI_SSID ""
  #define WIFI_PASS ""
#endif

// Intervalo entre tentativas de reenviar uma leitura.
#define API_REENVIO_MS 3000UL
// Tempo sem Wi-Fi antes de recomecar a conexao.
#define WIFI_REINICIO_MS 15000UL

// Modos:
// 0 = fluxo normal das estacoes e API
// 1 = teste de altura
// 2 = teste bruto da balanca
// 3 = teste de peso
// 4 = teste do sensor de frequencia cardiaca
// 5 = teste do botao de emergencia
// 6 = teste de comunicacao com GET /health
#define MODO_TESTE 0

// A altura e digitada no cadastro.
#define USAR_ALTURA 0
#define USAR_PESO   1
#define USAR_FC     1

// Conforme a fiacao atual da estacao, confirmada por varredura I2C.
#define PIN_SDA       9
#define PIN_SCL       8
#define PIN_HX_DT     16
#define PIN_HX_SCK    17
#define PIN_BTN_EMERG 7

#define ALTURA_SENSOR_MM   2300.0f
#define DIST_MIN_MM        200
#define DIST_MAX_MM        1300
#define ALTURA_MIN_M       1.0f
#define ALTURA_MAX_M       2.2f
#define ALTURA_AMOSTRAS    20
#define ALTURA_VARIACAO_MM 20

// Calibracao: 23,05 contagens/g = 23050 contagens/kg, para ler em kg.
// PROVISORIO: confirmar o valor exato da calibracao.
#define FATOR_BALANCA      23050.0f
#define PESO_MIN_KG        10.0f
#define PESO_MAX_KG        200.0f
#define PESO_AMOSTRAS      8
#define PESO_JANELA_MS     1000UL
#define PESO_VARIACAO_KG   0.5f

// Sem dedo o sensor le cerca de 750; com dedo, cerca de 120000.
#define FC_DEDO_LIMIAR     30000L
#define FC_ASSENTAR_MS     1500UL
// A leitura termina ao juntar FC_BATIDAS_ALVO batidas e usa a media das que
// ficam a ate FC_TOLERANCIA (15%) da mediana.
// FC_JANELA_MS e so o limite antes de desistir e recomecar.
#define FC_BATIDAS_ALVO    7
#define FC_TOLERANCIA      0.15f
#define FC_JANELA_MS       15000UL
// Tempo minimo entre a FC de repouso e o inicio da FC pos-teste.
#define FC_POS_ESPERA_MS   60000UL
