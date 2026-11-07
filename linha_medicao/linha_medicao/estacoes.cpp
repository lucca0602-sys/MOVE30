#include <Preferences.h>
#include "estacoes.h"

SessaoEstacao estacoes[NUM_ESTACOES];
static Preferences prefs;
static const uint32_t VERSAO = 3;

struct Blob { uint32_t versao; SessaoEstacao est[NUM_ESTACOES]; };

void estacoesCarregar() {
  prefs.begin("estacoes", false);
  Blob b;
  if (prefs.getBytesLength("dados") == sizeof(Blob)) {
    prefs.getBytes("dados", &b, sizeof(Blob));
    if (b.versao == VERSAO) {
      for (int i = 0; i < NUM_ESTACOES; i++) estacoes[i] = b.est[i];
    }
  }
}

void estacoesSalvar() {
  Blob b; b.versao = VERSAO;
  for (int i = 0; i < NUM_ESTACOES; i++) b.est[i] = estacoes[i];
  prefs.putBytes("dados", &b, sizeof(Blob));
}


