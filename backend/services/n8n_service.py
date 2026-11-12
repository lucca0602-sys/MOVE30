from backend.models.participant import classificar_imc
from backend.services.analytics_service import calcular_fc_score, classificar_fc_repouso, descrever_atividade


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
            frases.append(f"IMC {_br(imc, 1)}: ABAIXO da faixa de referência (18,5 a 24,9). Diga isso com clareza e carinho; NÃO é um ponto positivo. Sugira conversar com um profissional de saúde e reforce alimentação de qualidade.")
        elif imc < 18.5:
            frases.append(f"IMC {_br(imc, 1)}: um pouco ABAIXO da faixa de referência (18,5 a 24,9). Diga isso com clareza e carinho. Incentive alimentação de qualidade e exercícios de força.")
        elif imc < 25:
            frases.append(f"IMC {_br(imc, 1)}: dentro da faixa de referência (18,5 a 24,9). É um ponto positivo.")
        elif imc < 30:
            frases.append(f"IMC {_br(imc, 1)}: um pouco ACIMA da faixa de referência (18,5 a 24,9). Diga isso com clareza e carinho; NÃO diga que está dentro da faixa. Incentive movimento diário e alimentação equilibrada, sem dieta restritiva.")
        else:
            frases.append(f"IMC {_br(imc, 1)}: ACIMA da faixa de referência (18,5 a 24,9). Diga isso com clareza e carinho, sem assustar; NÃO diga que está dentro da faixa. Sugira acompanhamento de um profissional de saúde e incentive pequenos passos de movimento.")
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
        atividade = descrever_atividade(participant.get("modalidade"), participant.get("tipo_teste")) or "o esforço"
        frases.append(f"Depois de {atividade} os batimentos foram a {fc_pos} bpm (subiram {fc_pos - fc} bpm): é a resposta normal do corpo ao esforço. NÃO diga que isso prova bom condicionamento.")
    frases.append(f"Ponto positivo para o destaque: {_ponto_positivo(imc, fc, fc_pos)}")
    return " ".join(frases)


def _ponto_positivo(imc: float | None, fc: int | None, fc_pos: int | None) -> str:
    """O back-end escolhe o que dá para elogiar de verdade; a IA não precisa adivinhar."""
    if imc is not None and 18.5 <= imc < 25:
        return f"o IMC {_br(imc, 1)} dentro da faixa de referência."
    if fc is not None and fc <= 100:
        return f"os batimentos em repouso de {fc} bpm, {'abaixo de 60, sinal de coração eficiente' if fc < 60 else 'dentro da faixa normal'}."
    if fc_pos is not None:
        return "ter encarado a atividade até o fim e medido seus números: conhecer o próprio corpo é o primeiro passo."
    return "ter medido seus números hoje: conhecer o próprio corpo é o primeiro passo para cuidar dele."


def montar_payload_n8n(participant: dict) -> dict:
    return {
        # Só o primeiro nome vai para a IA (n8n e Ollama rodam neste PC); e-mail nunca sai do banco.
        "id": participant["id"],
        "indicadores": {
            "nome": (participant.get("nome") or "").split()[0] if participant.get("nome") else "participante",
            "tipo_avaliacao": participant.get("tipo_avaliacao", "completa"),
            "modalidade": participant.get("modalidade"),
            # Ex.: "2 min de bike no nível médio" ou "20 repetições de flexão"; None no simples.
            "atividade": descrever_atividade(participant.get("modalidade"), participant.get("tipo_teste")),
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
