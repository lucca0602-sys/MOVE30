
#pragma once

#include <stddef.h>

void apiConectarWifi();
bool apiWifiOk();
void apiReconectar();

bool apiHoraAtual(char* destino, size_t tamanho);

bool apiProximaAvaliacao(
    int& assessmentId,
    char* proxima,
    size_t tamanhoProxima,
    char* tipoTeste,
    size_t tamanhoTipo
);

enum ApiEnvio {
  API_ENVIO_OK,               // servidor confirmou a leitura
  API_ENVIO_TENTAR_DE_NOVO,   // falha temporária: manter a leitura e reenviar
  API_ENVIO_REJEITADO         // servidor recusou: reenviar não adianta
};

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
    bool& completa
);

bool apiCancelarAvaliacao();

// Teste de comunicacao somente de leitura.
bool apiTestarConexao();
