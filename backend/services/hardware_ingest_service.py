from psycopg.types.json import Jsonb

from backend.database import get_connection
from backend.models.hardware import HardwareMeasurementBatch


class ConflictingHardwareMessage(Exception):
    """A device reused a message ID for a different batch."""


def save_hardware_batch(batch: HardwareMeasurementBatch) -> bool:
    """Persist a raw batch; return False when the exact message was already stored."""
    measurements_json = Jsonb([
        measurement.model_dump(mode="json") for measurement in batch.measurements
    ])

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO hardware_measurement_batches (
                    device_id, message_id, measured_at, measurements
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (device_id, message_id) DO NOTHING
                RETURNING message_id;
                """,
                (batch.device_id, batch.message_id, batch.measured_at, measurements_json),
            )
            inserted = cursor.fetchone()
            if inserted is not None:
                return True

            cursor.execute(
                """
                SELECT measured_at, measurements
                FROM hardware_measurement_batches
                WHERE device_id = %s AND message_id = %s;
                """,
                (batch.device_id, batch.message_id),
            )
            existing = cursor.fetchone()
            if existing is None:
                # A concurrent delete should not silently acknowledge a missing event.
                raise RuntimeError("A mensagem duplicada não está disponível para confirmação.")

            old_measured_at, old_measurements = existing
            if old_measured_at == batch.measured_at and old_measurements == measurements_json.obj:
                return False

            raise ConflictingHardwareMessage(
                "message_id já foi usado com conteúdo diferente para este dispositivo."
            )
