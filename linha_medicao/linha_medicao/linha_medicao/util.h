#pragma once
#include <Arduino.h>
#include <algorithm>

inline float mediana(float* v, int n) {
  float c[64];
  if (n > 64) n = 64;
  for (int i = 0; i < n; i++) c[i] = v[i];
  std::sort(c, c + n);
  return (n % 2) ? c[n / 2] : (c[n / 2 - 1] + c[n / 2]) / 2.0f;
}
