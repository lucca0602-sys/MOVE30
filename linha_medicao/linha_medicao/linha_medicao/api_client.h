#pragma once
#include <stddef.h>
void apiConectarWifi();
bool apiWifiOk();
void apiReconectar();
bool apiHoraAtual(char* destino, size_t tamanho);
bool apiProximaAvaliacao(int& assessmentId, char* proxima, size_t tamanhoProxima,
                         char* tipoTeste, size_t tamanhoTipo);
bool apiEnviarMedicao(int assessmentId, const char* messageId,
                      const char* measuredAt, const char* nome,
                      float valor, int casas, const char* unidade,
                      char* proxima, size_t tamanhoProxima, bool& completa);
bool apiCancelarAvaliacao();
