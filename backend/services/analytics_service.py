from statistics import mean
from typing import Optional


def calcular_imc(peso: float, altura: float) -> float:
    if peso <= 0:
        raise ValueError("Peso deve ser maior que zero.")

    if altura <= 0:
        raise ValueError("Altura deve ser maior que zero.")

    return round(peso / (altura ** 2), 2)

def calcular_resistencia(velocidade_kmh: float) -> float:
    if velocidade_kmh < 6 or velocidade_kmh > 14:
        raise ValueError(
            "A velocidade deve estar entre 6 e 14 km/h."
        )

    resistencia = (
        (velocidade_kmh - 6) / (14 - 6)
    ) * 100

    return round(resistencia, 2)
VELOCIDADES_TESTE = {
    "light": 6.0,
    "moderate": 10.0,
    "hard": 14.0,
}
def calcular_indice_move(
    fas: int,
    resistencia: float
) -> float:
    if fas < 1 or fas > 7:
        raise ValueError("FAS deve estar entre 1 e 7.")

    if resistencia < 0 or resistencia > 100:
        raise ValueError(
            "Resistência deve estar entre 0 e 100."
        )

    fas_normalizado = ((fas - 1) / 6) * 100

    indice_move = (
        fas_normalizado + resistencia
    ) / 2

    return round(indice_move, 2)


def calcular_indice_move_coletivo(participantes: list[dict]) -> dict:
    """Aggregate one latest FAS/resistance score per named participant."""
    mais_recentes: dict[str, tuple[int, dict]] = {}
    for participante in participantes:
        nome = participante.get("nome")
        identificador = participante.get("id")
        if not isinstance(nome, str) or not nome.strip() or identificador is None:
            continue
        try:
            identificador = int(identificador)
        except (TypeError, ValueError):
            continue
        chave_nome = " ".join(nome.split()).casefold()
        atual = mais_recentes.get(chave_nome)
        if atual is None or identificador > atual[0]:
            mais_recentes[chave_nome] = (identificador, participante)

    indices = []
    for _, participante in mais_recentes.values():
        try:
            fas = int(participante["fas"])
            resistencia = float(participante["resistencia"])
            indices.append(calcular_indice_move(fas, resistencia))
        except (KeyError, TypeError, ValueError):
            continue

    return {
        "indice_move": round(mean(indices), 2) if indices else None,
        "participantes_considerados": len(indices),
    }


def calcular_fc_score(fc_pre_teste: float, fc_pos_teste: float) -> float:
    """Return the mean heart rate across the before and after measurements."""
    if fc_pre_teste <= 0 or fc_pos_teste <= 0:
        raise ValueError("As frequências cardíacas devem ser maiores que zero.")

    return round(mean((fc_pre_teste, fc_pos_teste)), 2)
