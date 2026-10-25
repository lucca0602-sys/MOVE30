import hmac
import os

import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException, status

from backend.models.hardware import HardwareMeasurementAccepted, HardwareMeasurementBatch
from backend.services.hardware_ingest_service import (
    ConflictingHardwareMessage,
    save_hardware_batch,
)

router = APIRouter(prefix="/api/v1/hardware", tags=["hardware"])


def require_device_key(x_device_key: str | None = Header(default=None, alias="X-Device-Key")) -> None:
    configured_key = os.getenv("ESP32_API_KEY", "").strip()
    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A recepção de hardware não está configurada no servidor.",
        )
    if not x_device_key or not hmac.compare_digest(x_device_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave do dispositivo inválida ou ausente.",
            headers={"WWW-Authenticate": "Device-Key"},
        )


@router.post(
    "/measurements",
    response_model=HardwareMeasurementAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Recebe um lote bruto de medições do hardware",
    description=(
        "Armazena leituras recebidas sem convertê-las em indicadores MOVE 30. "
        "O ESP32 deve reutilizar o mesmo message_id ao repetir uma transmissão."
    ),
)
def receive_measurements(
    batch: HardwareMeasurementBatch,
    _device: None = Depends(require_device_key),
) -> HardwareMeasurementAccepted:
    try:
        inserted = save_hardware_batch(batch)
    except ConflictingHardwareMessage as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except psycopg.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Armazenamento das medições indisponível; confirme a migração do banco.",
        ) from exc

    return HardwareMeasurementAccepted(
        accepted=True,
        duplicate=not inserted,
        device_id=batch.device_id,
        message_id=batch.message_id,
    )
