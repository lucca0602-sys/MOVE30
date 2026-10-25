from backend.models.participant import ParticipantIndicators
from backend.database import get_connection
from psycopg.rows import dict_row
from backend.services.analytics_service import (
    calcular_imc,
    calcular_resistencia,
    calcular_indice_move,
    VELOCIDADES_TESTE,
    calcular_fc_score,
)

def salvar_participante(participant: ParticipantIndicators):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            imc = (
                calcular_imc(participant.peso, participant.altura)
                if participant.peso is not None and participant.altura is not None
                else None
            )
            velocidade_teste = VELOCIDADES_TESTE[participant.tipo_teste]

            resistencia = calcular_resistencia(
                velocidade_teste
            )
            indice_move = calcular_indice_move(
                participant.fas,
                resistencia
            )
            cursor.execute(
                """
                INSERT INTO participantes (
                    nome,
                    idade,
                    peso,
                    altura,
                    fas,
                    fc_pre_teste,
                    fc_pos_teste,
                    tipo_teste,
                    velocidade_teste,
                    imc,
                    resistencia,
                    indice_move
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    participant.nome,
                    participant.idade,
                    participant.peso,
                    participant.altura,
                    participant.fas,
                    participant.fc_pre_teste,
                    participant.fc_pos_teste,
                    participant.tipo_teste,
                    velocidade_teste,
                    imc,
                    resistencia,
                    indice_move
                ),
            )
            return cursor.fetchone()[0]


def listar_participantes():
    with get_connection() as connection:
        with connection.cursor(row_factory = dict_row) as cursor: 
            cursor.execute("SELECT * FROM participantes;")
            participants = cursor.fetchall()
            for participant in participants:
                participant["fc_score"] = (
                    calcular_fc_score(participant["fc_pre_teste"], participant["fc_pos_teste"])
                    if participant["fc_pre_teste"] is not None and participant["fc_pos_teste"] is not None
                    else None
                )
                # The stored per-assessment value is retained for database compatibility;
                # the MOVE index is now exposed only as a population aggregate.
                participant.pop("indice_move", None)
            return participants


def buscar_participante_por_id(participant_id: int):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM participantes WHERE id = %s;", (participant_id,))
            participant = cursor.fetchone()
            if participant:
                participant["fc_score"] = (
                    calcular_fc_score(participant["fc_pre_teste"], participant["fc_pos_teste"])
                    if participant["fc_pre_teste"] is not None and participant["fc_pos_teste"] is not None
                    else None
                )
                participant.pop("indice_move", None)
            return participant
        

def salvar_analise_ia(participant_id, analise):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE participantes
                SET
                    perfil = %s,
                    destaque = %s,
                    oportunidade = %s,
                    mensagem = %s
                WHERE id = %s;
                """,
                (
                    analise.perfil,
                    analise.destaque,
                    analise.oportunidade,
                    analise.mensagem,
                    participant_id,
                ),
            )

def atualizar_medicoes_manuais(participant_id: int, measurements: dict):
    allowed = {"peso", "altura", "fc_pre_teste", "fc_pos_teste"}
    changes = {key: value for key, value in measurements.items() if key in allowed and value is not None}
    if not changes:
        raise ValueError("Informe ao menos uma medição válida.")

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM participantes WHERE id = %s FOR UPDATE;", (participant_id,))
            participant = cursor.fetchone()
            if participant is None:
                return None

            updated = {**participant, **changes}
            if "peso" in changes or "altura" in changes:
                updated["imc"] = (
                    calcular_imc(updated["peso"], updated["altura"])
                    if updated["peso"] is not None and updated["altura"] is not None
                    else None
                )
                changes["imc"] = updated["imc"]

            columns = list(changes)
            assignments = ", ".join(f"{column} = %s" for column in columns)
            values = [changes[column] for column in columns]
            cursor.execute(
                f"UPDATE participantes SET {assignments} WHERE id = %s;",
                (*values, participant_id),
            )
            return {**updated, **changes}
