import os

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

class MeasurementAlreadySet(Exception):
    """A saved measurement would be replaced by a different value."""


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
                    email,
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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    participant.nome,
                    participant.email,
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
            # pessoa_id groups one person's assessments: same name alone is not the same person.
            cursor.execute(
                """
                SELECT *, MIN(id) OVER (
                    PARTITION BY COALESCE(LOWER(email) || '|' || LOWER(TRIM(nome)), id::text)
                ) AS pessoa_id
                FROM participantes
                WHERE cancelada_em IS NULL
                ORDER BY id;
                """
            )
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
                # These routes have no authentication, so the e-mail stays in the database.
                participant.pop("email", None)
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
                participant.pop("email", None)
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
                WHERE id = %s AND perfil IS NULL;
                """,
                (
                    analise.perfil,
                    analise.destaque,
                    analise.oportunidade,
                    analise.mensagem,
                    participant_id,
                ),
            )

ANALISE_PENDENTE = """
    cancelada_em IS NULL
    AND perfil IS NULL
    AND peso IS NOT NULL AND altura IS NOT NULL
    AND fc_pre_teste IS NOT NULL AND fc_pos_teste IS NOT NULL
    AND (ia_proxima_tentativa IS NULL OR ia_proxima_tentativa <= NOW())
"""


def listar_analises_pendentes() -> list[int]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT id FROM participantes WHERE {ANALISE_PENDENTE} ORDER BY id;")
            return [row[0] for row in cursor.fetchall()]


def reservar_tentativa_analise(participant_id: int) -> bool:
    """Atomically claim one AI attempt, so two callers never analyze the same assessment."""
    # Must stay longer than one full AI call (two attempts of IA_TIMEOUT_S).
    intervalo = float(os.getenv("IA_INTERVALO_S", "600"))
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE participantes
                SET ia_tentativas = ia_tentativas + 1,
                    ia_proxima_tentativa = NOW() + make_interval(secs => %s)
                WHERE id = %s AND {ANALISE_PENDENTE}
                RETURNING id;
                """,
                (intervalo, participant_id),
            )
            return cursor.fetchone() is not None


def status_estacoes() -> dict:
    """Who is being measured now and who is next, so the staff can call the right person."""
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT a.device_id, p.*
                FROM hardware_assessment_assignments AS a
                JOIN participantes AS p ON p.id = a.assessment_id
                ORDER BY a.device_id;
                """
            )
            em_medicao = cursor.fetchall()
            cursor.execute(
                """
                SELECT p.id, p.nome
                FROM participantes AS p
                WHERE p.cancelada_em IS NULL
                  AND p.altura IS NOT NULL
                  AND (p.peso IS NULL OR p.fc_pre_teste IS NULL OR p.fc_pos_teste IS NULL)
                  AND NOT EXISTS (
                      SELECT 1 FROM hardware_assessment_assignments AS a
                      WHERE a.assessment_id = p.id
                  )
                ORDER BY p.id;
                """
            )
            fila = cursor.fetchall()
            cursor.execute(
                """
                SELECT id, nome, perfil IS NOT NULL AS analise_pronta
                FROM participantes
                WHERE cancelada_em IS NULL
                  AND peso IS NOT NULL AND altura IS NOT NULL
                  AND fc_pre_teste IS NOT NULL AND fc_pos_teste IS NOT NULL
                ORDER BY id DESC
                LIMIT 1;
                """
            )
            ultima_concluida = cursor.fetchone()
    return {
        "estacoes": [
            {
                "device_id": row["device_id"],
                "id": row["id"],
                "nome": row["nome"],
                "altura": row["altura"],
                "peso": row["peso"],
                "fc_pre_teste": row["fc_pre_teste"],
                "fc_pos_teste": row["fc_pos_teste"],
            }
            for row in em_medicao
        ],
        "fila": fila,
        "ultima_concluida": ultima_concluida,
    }


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

            for field, value in changes.items():
                if participant[field] is not None and float(participant[field]) != float(value):
                    raise MeasurementAlreadySet(f"O campo {field} já foi gravado e não pode ser sobrescrito.")

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
