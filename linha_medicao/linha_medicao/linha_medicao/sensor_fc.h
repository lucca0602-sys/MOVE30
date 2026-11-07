#pragma once

enum FcEstado { FC_OCIOSO, FC_ASSENTANDO, FC_COLETANDO, FC_PRONTO, FC_FALHOU };

bool fcIniciar();
void fcAtualizar();          // chame a CADA volta do loop(); não trava
FcEstado fcStatus();
bool fcResultado(float &bpm);// só dá true se fcStatus()==FC_PRONTO
void fcReiniciar();          // volta para FC_OCIOSO (pronto para a próxima pessoa)
bool fcDedoPresente();
