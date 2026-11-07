"""Checagem barata de coerência da resposta da IA contra os números reais.

O llama3.2 (3B) às vezes contradiz os dados (ex.: "abaixo do peso" com IMC 22).
- problemas_de_coerencia: erros graves; a resposta é reprovada e a IA é chamada de novo.
- ajustar_resposta: faltas leves que o back-end completa sem gastar outra chamada.
Número não citado no texto não reprova: o dashboard já mostra os números.
"""

PALAVRAS_PROIBIDAS = ("doença", "doenca", "diabetes", "hipertens", "infarto", "risco", "remédio", "remedio", "dieta restritiva")
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

    fc = indicadores.get("fc_pre_teste")
    if fc is not None:
        if 60 <= fc <= 100:
            problemas += [f"contradiz a FC normal ({p})" for p in (
                "acima de 100", "elevad", "batimento alto", "batimentos altos",
                "pouco baixo", "muito baixo", "batimento baixo", "batimentos baixos") if p in texto]
        elif fc < 60:
            problemas += [f"contradiz a FC baixa ({p})" for p in ("acima de 100", "elevad", "batimento alto", "batimentos altos") if p in texto]
        elif not any(p in texto for p in ("100", "elevad", "alto", "acelerad")):
            problemas.append("não comenta a FC elevada")

    problemas += [f"termo proibido ({p})" for p in PALAVRAS_PROIBIDAS if p in texto]
    return problemas


def ajustar_resposta(resposta: dict, indicadores: dict) -> dict:
    ajustada = dict(resposta)
    if _precisa_profissional(indicadores) and "profissional" not in _texto(resposta):
        ajustada["oportunidade"] = f"{str(ajustada['oportunidade']).rstrip()} {FRASE_PROFISSIONAL}"
    return ajustada
