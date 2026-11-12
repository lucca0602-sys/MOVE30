"""Checagem barata de coerência da resposta da IA contra os números reais.

O llama3.2 (3B) às vezes contradiz os dados (ex.: "abaixo do peso" com IMC 22).
- problemas_de_coerencia: erros graves; a resposta é reprovada e a IA é chamada de novo.
- ajustar_resposta: faltas leves que o back-end completa sem gastar outra chamada
  (ex.: IMC fora da faixa que o texto não mencionou ganha a frase verdadeira no começo do perfil).
Número não citado no texto não reprova: o dashboard já mostra os números.
"""

import re

# "elevado" só conta quando fala dos batimentos: "IMC elevado" com FC normal não é contradição.
# "IMC ... considerado saudável" com o IMC fora da faixa (visto no llama3.2 com IMC 28,6).
IMC_SAUDAVEL = re.compile(r"imc[^.!?]{0,60}saud[aá]ve")
FC_ACIMA = re.compile(r"(batiment|bpm)[^.!?]{0,40}acima")
FC_ELEVADA = re.compile(r"(batiment|frequ[eê]ncia|\bfc\b|bpm|cora[cç][aã]o)[^.!?]{0,40}elevad")

PALAVRAS_PROIBIDAS = ("doença", "doenca", "diabetes", "hipertens", "infarto", "risco", "remédio", "remedio", "dieta restritiva",
                      # Público com adolescentes: nada de meta de peso nem suplemento (visto no llama3.2).
                      "suplement", "perder peso", "perda de peso", "emagre", "caloria")
FRASES_DE_IMC_NORMAL = ("na faixa de referência", "dentro da faixa de referência", "faixa considerada saudável", "dentro da faixa saudável")
FRASE_PROFISSIONAL = "Vale conversar com um profissional de saúde para uma orientação feita para você."


def _texto(resposta: dict) -> str:
    return " ".join(str(resposta.get(c) or "") for c in ("perfil", "destaque", "oportunidade", "mensagem")).lower()


def _precisa_profissional(indicadores: dict) -> bool:
    imc, fc = indicadores.get("imc"), indicadores.get("fc_pre_teste")
    return (imc is not None and (float(imc) < 17 or float(imc) >= 30)) or (fc is not None and fc > 100)


def problemas_de_coerencia(resposta: dict, indicadores: dict) -> list[str]:
    texto = _texto(resposta)
    problemas = []

    imc = indicadores.get("imc")
    if imc is not None:
        imc = float(imc)
        if 18.5 <= imc < 25:
            proibidas = ("abaixo do peso", "acima do peso", "sobrepeso", "obesidade")
        elif imc < 18.5:
            proibidas = ("acima do peso", "sobrepeso", "obesidade")
        elif imc < 30:
            proibidas = ("abaixo do peso", "obesidade")
        else:
            proibidas = ("abaixo do peso",)
        problemas += [f"contradiz o IMC ({p})" for p in proibidas if p in texto]
        # Visto no llama3.2: IMC 26,3 descrito como "na faixa de referência".
        if not 18.5 <= imc < 25:
            problemas += [f"contradiz o IMC ({p})" for p in FRASES_DE_IMC_NORMAL if p in texto]
            if IMC_SAUDAVEL.search(texto):
                problemas.append("contradiz o IMC (saudável)")

    fc = indicadores.get("fc_pre_teste")
    if fc is not None:
        if 60 <= fc <= 100:
            if FC_ELEVADA.search(texto):
                problemas.append("contradiz a FC normal (elevad)")
            problemas += [f"contradiz a FC normal ({p})" for p in (
                "acima de 100", "batimento alto", "batimentos altos",
                "pouco baixo", "muito baixo", "batimento baixo", "batimentos baixos") if p in texto]
        elif fc < 60:
            if FC_ELEVADA.search(texto):
                problemas.append("contradiz a FC baixa (elevad)")
            problemas += [f"contradiz a FC baixa ({p})" for p in ("acima de 100", "batimento alto", "batimentos altos") if p in texto]
        # FC alta não comentada: ajustar_resposta completa (outra chamada custa 1-2 min na CPU).

    # "sem dieta restritiva" é a própria orientação da leitura repetida pela IA: não é proibido.
    sem_negacoes = texto
    for negacao in ("sem dieta restritiva", "nada de dieta restritiva", "não precisa de dieta restritiva"):
        sem_negacoes = sem_negacoes.replace(negacao, "")
    problemas += [f"termo proibido ({p})" for p in PALAVRAS_PROIBIDAS if p in sem_negacoes]
    if any(p in texto for p in ("o participante", "a participante")):
        problemas.append("fala da pessoa em terceira pessoa")
    return problemas


def _imc_fora_sem_aviso(resposta: dict, indicadores: dict) -> str | None:
    """Frase verdadeira sobre o IMC quando ele está fora da faixa e o texto não disse."""
    imc = indicadores.get("imc")
    if imc is None or 18.5 <= float(imc) < 25:
        return None
    imc = float(imc)
    direcao = "acima" if imc >= 25 else "abaixo"
    if direcao in _texto(resposta):
        return None
    quanto = "um pouco " if 17 <= imc < 30 else ""
    return f"Seu IMC de {imc:.1f}".replace(".", ",") + f" está {quanto}{direcao} da faixa de referência (18,5 a 24,9)."


def _fc_alta_sem_aviso(resposta: dict, indicadores: dict) -> str | None:
    fc = indicadores.get("fc_pre_teste")
    texto = _texto(resposta)
    if fc is None or fc <= 100 or any(p in texto for p in ("100", "elevad", "alto", "acelerad")) or FC_ACIMA.search(texto):
        return None
    return f"Seus batimentos em repouso, {fc} bpm, ficaram acima de 100: vale medir de novo com calma."


def ajustar_resposta(resposta: dict, indicadores: dict) -> dict:
    ajustada = dict(resposta)
    avisos = [a for a in (_imc_fora_sem_aviso(resposta, indicadores), _fc_alta_sem_aviso(resposta, indicadores)) if a]
    if avisos:
        ajustada["perfil"] = " ".join([*avisos, str(ajustada["perfil"]).strip()])
    if _precisa_profissional(indicadores) and "profissional" not in _texto(resposta):
        ajustada["oportunidade"] = f"{str(ajustada['oportunidade']).rstrip()} {FRASE_PROFISSIONAL}"
    return ajustada
