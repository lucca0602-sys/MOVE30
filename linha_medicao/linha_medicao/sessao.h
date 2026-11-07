#pragma once
#include <Arduino.h>

struct Campo {
  float valor   = 0;
  bool  travado = false;   // medido e TRAVADO, não muda mais nessa passada
  bool  enviado = false;   // a API já confirmou
};

struct Sessao {
  uint32_t versao    = 1;
  int      medicaoId = -1;
  uint8_t  estado    = 0;  // para retomar o estado depois de reiniciar
  Campo altura, peso, fcRepouso, fcPos;
};

extern Sessao sessao;

void sessaoCarregar();
void sessaoSalvar();
void sessaoLimpar();
bool sessaoTravar(Campo &c, float valor);
bool sessaoTemPendencia();