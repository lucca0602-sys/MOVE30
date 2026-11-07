from psycopg.types.json import Jsonb
from psycopg.rows import dict_row

from backend.database import get_connection
from backend.models.hardware import HardwareMeasurementBatch
from backend.services.analytics_service import calcular_imc


class ConflictingHardwareMessage(Exception):
    """The device reused a message ID for different content."""


class AssessmentNotAssigned(Exception):
    """The assessment is not the active one reserved to this device."""


class OutOfSequenceMeasurement(Exception):
    """The reading arrived before its assigned assessment step."""

class InvalidHardwareMeasurement(Exception):
    """The sensor reading does not match the current stage or unit."""


MEASUREMENTS = {
    "height": ("altura", "m", 1.0, 2.2),
    "weight": ("peso", "kg", 10.0, 200.0),
    "heart_rate_rest": ("fc_pre_teste", "bpm", 30.0, 220.0),
    "heart_rate_post": ("fc_pos_teste", "bpm", 30.0, 220.0),
}


def next_measurement(participant: dict) -> str | None:
    for name, (column, _, _, _) in MEASUREMENTS.items():
        # Teste simples termina no batimento de repouso: o firmware só pede corrida
        # quando a etapa é heart_rate_post, então a ESP32 não precisa mudar.
        if name == "heart_rate_post" and participant.get("tipo_avaliacao") == "simples":
            continue
        if participant.get(column) is None:
            return name
    return None


def _lock_device(cursor, device_id: str) -> None:
    cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0));", (device_id,))
    cursor.execute(
        """
        INSERT INTO hardware_assessment_assignments (device_id, assessment_id)
        VALUES (%s, NULL)
        ON CONFLICT (device_id) DO NOTHING;
        """,
        (device_id,),
    )
    cursor.execute(
        "SELECT assessment_id FROM hardware_assessment_assignments WHERE device_id = %s FOR UPDATE;",
        (device_id,),
    )


def claim_next_assessment(device_id: str) -> dict:
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            _lock_device(cursor, device_id)
            assignment = cursor.fetchone()
            participant = None
            if assignment["assessment_id"] is not None:
                cursor.execute(
                    "SELECT * FROM participantes WHERE id = %s FOR UPDATE;",
                    (assignment["assessment_id"],),
                )
                participant = cursor.fetchone()
                if (participant and participant["cancelada_em"] is None
                        and participant["altura"] is not None
                        and next_measurement(participant)):
                    return {
                        "status": "active",
                        "assessment_id": participant["id"],
                        "next_measurement": next_measurement(participant),
                        "tipo_teste": participant["tipo_teste"],
                    }
                cursor.execute(
                    """
                    UPDATE hardware_assessment_assignments
                    SET assessment_id = NULL, assigned_at = NULL, updated_at = NOW()
                    WHERE device_id = %s;
                    """,
                    (device_id,),
                )

            # Only one device picks from the queue at a time, so two never choose the same person.
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended('move30-fila', 0));")
            # The height comes from registration; without it the station cannot advance.
            cursor.execute(
                """
                SELECT p.*
                FROM participantes AS p
                WHERE p.cancelada_em IS NULL
                  AND p.altura IS NOT NULL
                  AND (p.peso IS NULL OR p.fc_pre_teste IS NULL
                       OR (p.fc_pos_teste IS NULL AND p.tipo_avaliacao = 'completa'))
                  AND NOT EXISTS (
                      SELECT 1 FROM hardware_assessment_assignments AS a
                      WHERE a.assessment_id = p.id
                  )
                ORDER BY p.id ASC
                LIMIT 1
                FOR UPDATE OF p SKIP LOCKED;
                """
            )
            participant = cursor.fetchone()
            if participant is None:
                return {"status": "waiting", "assessment_id": None,
                        "next_measurement": None, "tipo_teste": None}

            step = next_measurement(participant)
            cursor.execute(
                """
                UPDATE hardware_assessment_assignments
                SET assessment_id = %s, assigned_at = NOW(), updated_at = NOW()
                WHERE device_id = %s;
                """,
                (participant["id"], device_id),
            )
            return {
                "status": "active",
                "assessment_id": participant["id"],
                "next_measurement": step,
                "tipo_teste": participant["tipo_teste"],
            }


def release_assessment(device_id: str) -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            _lock_device(cursor, device_id)
            assessment_id = cursor.fetchone()[0]
            # Cancelling keeps the readings but stops the queue from reserving it again.
            cursor.execute(
                "UPDATE participantes SET cancelada_em = NOW() WHERE id = %s AND cancelada_em IS NULL;",
                (assessment_id,),
            )
            cursor.execute(
                """
                UPDATE hardware_assessment_assignments
                SET assessment_id = NULL, assigned_at = NULL, updated_at = NOW()
                WHERE device_id = %s;
                """,
                (device_id,),
            )


def save_hardware_batch(batch: HardwareMeasurementBatch) -> dict:
    reading = batch.measurements[0]
    spec = MEASUREMENTS.get(reading.name)
    if spec is None:
        raise InvalidHardwareMeasurement("Indicador de hardware desconhecido.")
    column, expected_unit, minimum, maximum = spec
    if reading.unit != expected_unit:
        raise InvalidHardwareMeasurement(f"A unidade de {reading.name} deve ser {expected_unit}.")
    if not minimum <= reading.value <= maximum:
        raise InvalidHardwareMeasurement(f"A leitura de {reading.name} está fora do intervalo aceito.")
    if reading.name.startswith("heart_rate_") and not reading.value.is_integer():
        raise InvalidHardwareMeasurement("A frequência cardíaca deve ser um valor inteiro em bpm.")

    measurements_json = [reading.model_dump(mode="json")]
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            _lock_device(cursor, batch.device_id)
            assignment = cursor.fetchone()

            # Idempotency is checked before the current-step gate so a lost 202 can be replayed.
            cursor.execute(
                """
                SELECT measured_at, measurements, assessment_id
                FROM hardware_measurement_batches
                WHERE device_id = %s AND message_id = %s;
                """,
                (batch.device_id, batch.message_id),
            )
            existing = cursor.fetchone()
            if existing is not None:
                if (existing["measured_at"] != batch.measured_at
                        or existing["measurements"] != measurements_json
                        or existing["assessment_id"] != batch.assessment_id):
                    raise ConflictingHardwareMessage(
                        "message_id já foi usado com conteúdo ou avaliação diferente."
                    )
                cursor.execute("SELECT * FROM participantes WHERE id = %s;", (batch.assessment_id,))
                participant = cursor.fetchone()
                if participant is None:
                    raise AssessmentNotAssigned("A avaliação vinculada não existe mais.")
                step = next_measurement(participant)
                return {"inserted": False, "next_measurement": step,
                        "complete": step is None, "assessment_id": batch.assessment_id}

            if assignment["assessment_id"] != batch.assessment_id:
                raise AssessmentNotAssigned(
                    "A avaliação informada não está reservada para este dispositivo."
                )

            cursor.execute("SELECT * FROM participantes WHERE id = %s FOR UPDATE;", (batch.assessment_id,))
            participant = cursor.fetchone()
            if participant is None:
                raise AssessmentNotAssigned("A avaliação vinculada não foi encontrada.")

            expected = next_measurement(participant)
            if expected is None:
                raise OutOfSequenceMeasurement("Esta avaliação já recebeu todas as medições.")
            if reading.name != expected:
                raise OutOfSequenceMeasurement(
                    f"Etapa esperada: {expected}; leitura recebida: {reading.name}."
                )

            cursor.execute(
                """
                INSERT INTO hardware_measurement_batches (
                    device_id, message_id, measured_at, measurements, assessment_id
                ) VALUES (%s, %s, %s, %s, %s);
                """,
                (batch.device_id, batch.message_id, batch.measured_at,
                 Jsonb(measurements_json), batch.assessment_id),
            )

            updated = {**participant, column: reading.value}
            imc = (
                calcular_imc(updated["peso"], updated["altura"])
                if updated["peso"] is not None and updated["altura"] is not None
                else None
            )
            cursor.execute(
                f"UPDATE participantes SET {column} = %s, imc = %s WHERE id = %s;",
                (reading.value, imc, batch.assessment_id),
            )
            updated["imc"] = imc
            step = next_measurement(updated)
            complete = step is None
            cursor.execute(
                """
                UPDATE hardware_assessment_assignments
                SET assessment_id = %s, assigned_at = CASE WHEN %s THEN NULL ELSE assigned_at END,
                    updated_at = NOW()
                WHERE device_id = %s;
                """,
                (None if complete else batch.assessment_id, complete, batch.device_id),
            )
            return {"inserted": True, "next_measurement": step,
                    "complete": complete, "assessment_id": batch.assessment_id}



