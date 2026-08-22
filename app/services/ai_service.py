import json


def enviar_para_ia(prompt: str) -> str:
    """Simula a resposta da IA em formato JSON."""
    resposta = {
        "perfil": "Ativo e saudavel",
        "destaque": "Excelente pontuacao de atividade",
        "oportunidade": "Melhorar habitos alimentares",
        "mensagem": "Continue com seus habitos saudaveis e considere uma avaliacao profissional.",
    }

    return json.dumps(resposta, ensure_ascii=False)