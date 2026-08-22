from app.models.participant import ParticipantIndicators


def criar_prompt(indicators: ParticipantIndicators) -> str:
    """Cria as instrucoes que serao enviadas ao modelo de IA."""
    return (
        "Voce e um agente de IA especializado em interpretar indicadores "
        "de saude e bem-estar.\n\n"
        "Interprete os dados abaixo e retorne uma analise com os campos: "
        "perfil, destaque, oportunidade e mensagem.\n"
        "Nao faca diagnosticos nem prescreva tratamentos. "
        "Quando necessario, recomende avaliacao profissional.\n\n"
        "Indicadores do participante:\n"
        f"Idade: {indicators.idade}\n"
        f"IMC: {indicators.imc}\n"
        f"Frequencia cardiaca em repouso: {indicators.fc_repouso}\n"
        f"Pontuacao de atividade: {indicators.atividade_score}\n"
        f"Pontuacao de resistencia: {indicators.resistencia_score}\n"
        f"Pontuacao de frequencia cardiaca: {indicators.fc_score}\n"
        f"Pontuacao de habitos: {indicators.habitos_score}\n"
        f"Indice MOVE: {indicators.indice_move}\n"
    )