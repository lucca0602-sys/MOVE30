#pragma once
// ============================================================
// CONFIGURAÇÃO da ESP32-S3
// ============================================================

#define WIFI_SSID  "SUA_REDE"
#define WIFI_PASS  "SUA_SENHA"
#define API_URL    "http://192.168.0.10:8000" // IP/porta do backend acessível na rede local
#define DEVICE_ID  "move30-esp32-01"         // manter estável entre reinicializações

// Crie secrets.h a partir de secrets.example.h e não versione a chave real.
#if __has_include("secrets.h")
  #include "secrets.h"
#else
  #define DEVICE_API_KEY ""
#endif

// 0 = estações + envio à API; 1..5 = testes locais de sensores/botão
#define MODO_TESTE 0

#define PIN_SDA          8
#define PIN_SCL          9
#define PIN_HX_DT        4
#define PIN_HX_SCK       5
#define PIN_BTN_EMERG    7

#define ALTURA_SENSOR_MM   2300.0f
#define DIST_MIN_MM        200
#define DIST_MAX_MM        1300
#define ALTURA_MIN_M       1.0f
#define ALTURA_MAX_M       2.2f
#define ALTURA_AMOSTRAS    20
#define ALTURA_VARIACAO_MM 20

#define FATOR_BALANCA      1.0f
#define PESO_MIN_KG        10.0f
#define PESO_MAX_KG        200.0f
#define PESO_AMOSTRAS      15
#define PESO_VARIACAO_KG   0.5f

#define FC_DEDO_LIMIAR     50000L
#define FC_ASSENTAR_MS     2000UL
#define FC_JANELA_MS       12000UL
#define FC_MIN_BATIDAS     6
#define FC_VARIACAO_MAX    15
