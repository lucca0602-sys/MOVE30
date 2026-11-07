#pragma once
void  pesoIniciar();
bool  pesoTarar();           // balança TEM que estar vazia
bool  pesoPessoaPresente();
bool  pesoEstavel(float &kg);// chame a CADA volta do loop(); não trava
float pesoUltimaLeitura();
long  pesoUltimoBruto();     // contagens do HX711; satura em +-8388607
float pesoBruto();
