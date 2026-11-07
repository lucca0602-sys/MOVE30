#include <Arduino.h>
#include "config.h"
#include "botoes.h"

void botoesIniciar() {
  pinMode(PIN_BTN_EMERG, INPUT_PULLUP);
}

bool emergenciaAcionada() { return digitalRead(PIN_BTN_EMERG) == LOW; }
