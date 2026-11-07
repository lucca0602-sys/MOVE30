#pragma once
#include <Arduino.h>

enum Estacao { EST_ALTURA, EST_PESO, EST_FC, NUM_ESTACOES };

struct SessaoEstacao {
  bool ocupada = false;
  bool medido = false;
  float valor = 0;
  int assessmentId = -1;
  uint8_t casas = 0;
  char messageId[37] = "";
  char measuredAt[21] = "";
  char nome[24] = "";
  char unidade[8] = "";
};

extern SessaoEstacao estacoes[NUM_ESTACOES];
void estacoesCarregar();
void estacoesSalvar();
