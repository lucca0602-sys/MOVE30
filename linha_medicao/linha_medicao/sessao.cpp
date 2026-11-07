#include <Preferences.h>
#include "sessao.h"

Sessao sessao;
static Preferences prefs;

void sessaoCarregar() {
  prefs.begin("linha", false);
  if (prefs.getBytesLength("sessao") == sizeof(Sessao)) {
    Sessao tmp;
    prefs.getBytes("sessao", &tmp, sizeof(Sessao));
    if (tmp.versao == 1) sessao = tmp;
  }
}

void sessaoSalvar() { prefs.putBytes("sessao", &sessao, sizeof(Sessao)); }

void sessaoLimpar() { sessao = Sessao(); sessaoSalvar(); }

bool sessaoTravar(Campo &c, float valor) {
  if (c.travado) return false;        // já travado: ignora nova leitura
  c.valor = valor;
  c.travado = true;
  c.enviado = false;
  sessaoSalvar();                     // vai para a flash na hora
  return true;
}

bool sessaoTemPendencia() {
  Campo* cs[] = { &sessao.altura, &sessao.peso, &sessao.fcRepouso, &sessao.fcPos };
  for (Campo* c : cs) if (c->travado && !c->enviado) return true;
  return false;
}