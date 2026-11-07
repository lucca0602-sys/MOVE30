from backend.models.participant import classificar_imc
from backend.services.analytics_service import calcular_fc_score


def _numero_para_json(valor):
    if valor is None:
        return None

    return float(valor)


def montar_payload_n8n(participant: dict) -> dict:
    return {
        # A IA interpreta indicadores: nome e e-mail não saem do sistema.
        "id": participant["id"],
        "indicadores": {
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
            "imc": _numero_para_json(participant["imc"]),
            "classificacao_imc": (
                classificar_imc(float(participant["imc"]))
                if participant["imc"] is not None else None
            ),
            "resistencia": _numero_para_json(participant["resistencia"]),
        },
    }
