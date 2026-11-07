from backend.models.participant import classificar_imc
from backend.services.analytics_service import calcular_fc_score, classificar_fc_repouso


def _numero_para_json(valor):
    if valor is None:
        return None

    return float(valor)


def _br(valor: float, casas: int) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")


def montar_leitura(participant: dict) -> str:
    """Interpretação pronta dos números, em frases curtas.

    O llama3.2 (3B) erra regras condicionais ("se IMC < 17...") e chega a inventar valores;
    por isso o back-end decide o que cada número significa e a IA só escreve com o tom certo.
    """
    frases = []
    imc = float(participant["imc"]) if participant.get("imc") is not None else None
    idade = participant.get("idade")
    if imc is not None:
        if imc < 17:
            frases.append(f"IMC {_br(imc, 1)}: abaixo da faixa de referência. NÃO é um ponto positivo. Sugira com carinho conversar com um profissional de saúde e reforce alimentação de qualidade.")
        elif imc < 18.5:
            frases.append(f"IMC {_br(imc, 1)}: um pouco abaixo da faixa de referência (18,5 a 24,9). Incentive alimentação de qualidade e exercícios de força.")
        elif imc < 25:
            frases.append(f"IMC {_br(imc, 1)}: dentro da faixa considerada saudável (18,5 a 24,9). É um ponto positivo.")
        elif imc < 30:
            frases.append(f"IMC {_br(imc, 1)}: um pouco acima da faixa de referência. Incentive movimento diário e alimentação equilibrada, sem dieta restritiva.")
        else:
            frases.append(f"IMC {_br(imc, 1)}: acima da faixa de referência. Sugira com carinho acompanhamento de um profissional de saúde e incentive pequenos passos de movimento.")
        if idade is not None and idade < 18:
            frases.append("A pessoa é adolescente: diga que, nessa idade, o IMC é avaliado por curvas de crescimento, então o número é só uma referência.")
    fc = participant.get("fc_pre_teste")
    if fc is not None:
        if fc < 60:
            frases.append(f"Batimentos em repouso {fc} bpm: abaixo de 60. Costuma aparecer em quem treina bastante, um coração eficiente. Se houver tontura ou cansaço, vale consultar um profissional.")
        elif fc <= 100:
            frases.append(f"Batimentos em repouso {fc} bpm: dentro da faixa normal (60 a 100 bpm). NÃO diga que está alto.")
        else:
            frases.append(f"Batimentos em repouso {fc} bpm: acima de 100, elevado para repouso. Pode ser nervosismo ou café, mas sugira medir de novo com calma e, se continuar alto, conversar com um profissional de saúde.")
    fc_pos = participant.get("fc_pos_teste")
    if fc is not None and fc_pos is not None:
        frases.append(f"Depois da corrida os batimentos foram a {fc_pos} bpm (subiram {fc_pos - fc} bpm).")
    return " ".join(frases)


def montar_payload_n8n(participant: dict) -> dict:
    return {
        # Só o primeiro nome vai para a IA (n8n e Ollama rodam neste PC); e-mail nunca sai do banco.
        "id": participant["id"],
        "indicadores": {
            "nome": (participant.get("nome") or "").split()[0] if participant.get("nome") else "participante",
            "tipo_avaliacao": participant.get("tipo_avaliacao", "completa"),
            "faixa_fc_repouso": classificar_fc_repouso(participant["fc_pre_teste"]),
            "leitura": montar_leitura(participant),
            "imc_texto": _br(float(participant["imc"]), 1) if participant["imc"] is not None else None,
            "idade": participant["idade"],
            "peso": _numero_para_json(participant["peso"]),
            "altura": _numero_para_json(participant["altura"]),
            "fas": participant["fas"],
            "fc_pre_teste": participant["fc_pre_teste"],
            "fc_pos_teste": participant["fc_pos_teste"],
            "fc_score": (
                calcular_fc_score(participant["fc_pre_teste"], participant["fc_pos_teste"])
                if participant["fc_pre_teste"] is not None and participant["fc_pos_teste"] is not None
                else None
            ),
            "tipo_teste": participant["tipo_teste"],
            "velocidade_teste": _numero_para_json(participant["velocidade_teste"]),
            "imc": round(float(participant["imc"]), 1) if participant["imc"] is not None else None,
            "classificacao_imc": (
                classificar_imc(float(participant["imc"]))
                if participant["imc"] is not None else None
            ),
            "resistencia": _numero_para_json(participant["resistencia"]),
        },
    }
