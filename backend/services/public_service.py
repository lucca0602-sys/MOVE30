"""Dados do fluxo público: resultado de UMA pessoa pelo token e agregados do grupo."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from psycopg.rows import dict_row

from backend.database import get_connection
from backend.models.participant import classificar_imc
from backend.services.analytics_service import calcular_fc_score, classificar_fc_repouso, descrever_atividade


def _numero(valor):
    return None if valor is None else float(valor)


def _texto(valor):
    return valor.strip() if isinstance(valor, str) and valor.strip() else None


def buscar_resultado_publico(token: UUID) -> dict | None:
    """Só as colunas que o dono do link precisa ver. Nunca e-mail, ID interno ou dados de outras pessoas."""
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT nome, idade, peso, altura, imc, fc_pre_teste, fc_pos_teste, tipo_avaliacao,
                       modalidade, tipo_teste,
                       perfil, destaque, oportunidade, mensagem, criado_em
                FROM participantes
                WHERE token_publico = %s AND cancelada_em IS NULL;
                """,
                (token,),
            )
            row = cursor.fetchone()
    if row is None:
        return None

    imc = _numero(row["imc"])
    analise = {campo: _texto(row[campo]) for campo in ("perfil", "destaque", "oportunidade", "mensagem")}
    simples = row["tipo_avaliacao"] == "simples"
    medidas_completas = all(
        row[campo] is not None
        for campo in (("peso", "altura", "fc_pre_teste") if simples else ("peso", "altura", "fc_pre_teste", "fc_pos_teste"))
    )
    if analise["perfil"]:
        status = "pronto"
    elif medidas_completas:
        status = "analisando"
    else:
        status = "aguardando_medicoes"

    return {
        "primeiro_nome": row["nome"].split()[0],
        "tipo_avaliacao": row["tipo_avaliacao"],
        "atividade": descrever_atividade(row["modalidade"], row["tipo_teste"]),
        "idade": row["idade"],
        "peso": _numero(row["peso"]),
        "altura": _numero(row["altura"]),
        "imc": round(imc, 1) if imc is not None else None,
        "classificacao_imc": classificar_imc(imc) if imc is not None else None,
        "fc_repouso": row["fc_pre_teste"],
        "faixa_fc_repouso": classificar_fc_repouso(row["fc_pre_teste"]),
        "fc_pos_teste": row["fc_pos_teste"],
        "fc_score": (
            calcular_fc_score(row["fc_pre_teste"], row["fc_pos_teste"])
            if row["fc_pre_teste"] is not None and row["fc_pos_teste"] is not None else None
        ),
        "status": status,
        "analise": analise if analise["perfil"] else None,
        "criado_em": row["criado_em"].isoformat() if row["criado_em"] else None,
    }


# Abaixo disso a "média" praticamente revela o dado de uma pessoa: o painel mostra só a contagem.
MINIMO_PARA_MEDIA = 3
FAIXAS_FC = (("baixa", "Abaixo de 60"), ("normal", "60 a 100"), ("elevada", "Acima de 100"))
CLASSES_IMC = ("Abaixo do peso", "Peso considerado normal", "Sobrepeso", "Obesidade grau I", "Obesidade grau II", "Obesidade grau III")


# Brasília sem horário de verão desde 2019; fuso fixo evita depender do tzdata no Windows.
FUSO_EVENTO = timezone(timedelta(hours=-3))
HORAS_NO_GRAFICO = 12


def contar_por_hora(participantes: list[dict], agora: datetime | None = None) -> list[dict]:
    """Avaliações por hora (últimas 12 horas até agora), para o gráfico ao vivo do /geral."""
    agora = (agora or datetime.now(timezone.utc)).astimezone(FUSO_EVENTO).replace(minute=0, second=0, microsecond=0)
    inicio = agora - timedelta(hours=HORAS_NO_GRAFICO - 1)
    contagem = {inicio + timedelta(hours=i): 0 for i in range(HORAS_NO_GRAFICO)}
    for p in participantes:
        criado = p.get("criado_em")
        if criado is None:
            continue
        hora = criado.astimezone(FUSO_EVENTO).replace(minute=0, second=0, microsecond=0)
        if hora in contagem:
            contagem[hora] += 1
    return [{"hora": f"{h.hour:02d}h", "total": n} for h, n in contagem.items()]


def _media(valores: list[float], casas: int = 1) -> dict:
    n = len(valores)
    return {"valor": round(sum(valores) / n, casas) if n >= MINIMO_PARA_MEDIA else None, "n": n}


def calcular_painel_publico(participantes: list[dict]) -> dict:
    """Só agregados do grupo para o painel público (/geral). Nenhum valor individual sai daqui."""
    from backend.services.analytics_service import calcular_indice_move_coletivo

    # Avaliação mais recente de cada pessoa, como no dashboard do Streamlit.
    por_pessoa: dict = {}
    for p in sorted(participantes, key=lambda item: item["id"]):
        por_pessoa[p.get("pessoa_id", p["id"])] = p
    pessoas = list(por_pessoa.values())

    def nums(campo, filtro=lambda p: True):
        return [float(p[campo]) for p in pessoas if p.get(campo) is not None and filtro(p)]

    completas = lambda p: p.get("fc_pre_teste") is not None and p.get("fc_pos_teste") is not None
    fc_repouso = nums("fc_pre_teste")
    imcs = nums("imc")
    total = len(pessoas)
    mostrar_distribuicao = total >= MINIMO_PARA_MEDIA

    def faixa_fc(fc):
        return "baixa" if fc < 60 else "normal" if fc <= 100 else "elevada"

    tipos: dict[str, int] = {}
    for p in pessoas:
        if p.get("tipo_avaliacao") == "simples":
            chave = "simples"
        else:
            chave = p.get("modalidade") or ("corrida" if p.get("tipo_teste") else "nao_informado")
        tipos[chave] = tipos.get(chave, 0) + 1

    indice = calcular_indice_move_coletivo(pessoas)
    return {
        "participantes": total,
        "avaliacoes_por_hora": contar_por_hora(participantes),
        "minimo_para_media": MINIMO_PARA_MEDIA,
        "medias": {
            "peso": _media(nums("peso")),
            "altura": _media(nums("altura"), 2),
            "imc": _media(imcs),
            "fc_repouso": _media(fc_repouso, 0),
            "fc_pos_teste": _media(nums("fc_pos_teste", completas), 0),
            "variacao_fc": _media([float(p["fc_pos_teste"]) - float(p["fc_pre_teste"]) for p in pessoas if completas(p)], 0),
            "fc_score": _media([(float(p["fc_pos_teste"]) + float(p["fc_pre_teste"])) / 2 for p in pessoas if completas(p)]),
        },
        "distribuicao_imc": (
            [{"faixa": c, "total": sum(1 for v in imcs if classificar_imc(v) == c)} for c in CLASSES_IMC]
            if mostrar_distribuicao else None
        ),
        "distribuicao_fc_repouso": (
            [{"faixa": rotulo, "total": sum(1 for v in fc_repouso if faixa_fc(v) == chave)} for chave, rotulo in FAIXAS_FC]
            if mostrar_distribuicao else None
        ),
        "tipos_avaliacao": tipos if mostrar_distribuicao else None,
        "indice_move": {
            "valor": indice["indice_move"] if indice["participantes_considerados"] >= MINIMO_PARA_MEDIA else None,
            "n": indice["participantes_considerados"],
        },
    }
