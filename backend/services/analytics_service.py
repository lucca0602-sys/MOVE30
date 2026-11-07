from statistics import mean
from typing import Optional


def calcular_imc(peso: float, altura: float) -> float:
    if peso <= 0:
        raise ValueError("Peso deve ser maior que zero.")

    if altura <= 0:
        raise ValueError("Altura deve ser maior que zero.")

    # O banco devolve Decimal e o sensor envia float.
    return round(float(peso) / (float(altura) ** 2), 2)

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
    """Aggregate one latest FAS/resistance score per person."""
    mais_recentes: dict[int, tuple[int, dict]] = {}
    for participante in participantes:
        identificador = participante.get("id")
        try:
            identificador = int(identificador)
        except (TypeError, ValueError):
            continue
        chave_pessoa = participante.get("pessoa_id", identificador)
        atual = mais_recentes.get(chave_pessoa)
        if atual is None or identificador > atual[0]:
            mais_recentes[chave_pessoa] = (identificador, participante)

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


FAIXAS_VALIDAS = {
    "peso": (10, 200),
    "altura": (1, 2.2),
    "fc_pre_teste": (30, 220),
    "fc_pos_teste": (30, 220),
}


def calcular_medias_coletivas(participantes: list[dict]) -> dict:
    """Average only complete, plausible assessments, using each person's latest valid one."""
    validas: dict[int, dict] = {}
    incompletas = 0
    invalidas = 0
    for participante in sorted(participantes, key=lambda item: item["id"]):
        if any(participante.get(campo) is None for campo in FAIXAS_VALIDAS):
            incompletas += 1
            continue
        valores = {campo: float(participante[campo]) for campo in FAIXAS_VALIDAS}
        if not all(FAIXAS_VALIDAS[campo][0] <= valor <= FAIXAS_VALIDAS[campo][1] for campo, valor in valores.items()):
            invalidas += 1
            continue
        validas[participante.get("pessoa_id", participante["id"])] = valores

    def media(calculo) -> float | None:
        return round(mean(calculo(valores) for valores in validas.values()), 2) if validas else None

    return {
        "participantes_validos": len(validas),
        "avaliacoes_incompletas": incompletas,
        "avaliacoes_invalidas": invalidas,
        "peso": media(lambda v: v["peso"]),
        "altura": media(lambda v: v["altura"]),
        "fc_pre_teste": media(lambda v: v["fc_pre_teste"]),
        "fc_pos_teste": media(lambda v: v["fc_pos_teste"]),
        "variacao_fc": media(lambda v: v["fc_pos_teste"] - v["fc_pre_teste"]),
        "fc_score": media(lambda v: (v["fc_pre_teste"] + v["fc_pos_teste"]) / 2),
        "imc": media(lambda v: v["peso"] / v["altura"] ** 2),
    }


def calcular_fc_score(fc_pre_teste: float, fc_pos_teste: float) -> float:
    """Return the mean heart rate across the before and after measurements."""
    if fc_pre_teste <= 0 or fc_pos_teste <= 0:
        raise ValueError("As frequências cardíacas devem ser maiores que zero.")

    return round(mean((fc_pre_teste, fc_pos_teste)), 2)


def classificar_fc_repouso(fc: int | None) -> str | None:
    """Faixa de referência da FC de repouso em adultos (60 a 100 bpm)."""
    if fc is None:
        return None
    if fc < 60:
        return "abaixo de 60 bpm (baixa; comum em quem treina, mas vale observar se houver tontura ou cansaço)"
    if fc <= 100:
        return "entre 60 e 100 bpm (faixa considerada normal)"
    return "acima de 100 bpm (elevada para repouso)"
