"""Dados do fluxo público: cria o teste simples e devolve o resultado de UMA pessoa pelo token."""
from uuid import UUID

from psycopg.rows import dict_row

from backend.database import get_connection
from backend.models.participant import TesteSimples, classificar_imc
from backend.services.analytics_service import calcular_fc_score, calcular_imc, classificar_fc_repouso


def salvar_teste_simples(teste: TesteSimples) -> tuple[int, UUID]:
    imc = calcular_imc(teste.peso, teste.altura)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO participantes (nome, idade, peso, altura, fc_pre_teste, imc, tipo_avaliacao)
                VALUES (%s, %s, %s, %s, %s, %s, 'simples')
                RETURNING id, token_publico;
                """,
                (teste.nome, teste.idade, teste.peso, teste.altura, teste.fc_repouso, imc),
            )
            participant_id, token = cursor.fetchone()
            return participant_id, token


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
