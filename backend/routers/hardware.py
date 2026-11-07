import hmac
import logging
import os

import psycopg
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status

from backend.models.hardware import (
    HardwareAssessmentStatus,
    HardwareMeasurementAccepted,
    HardwareMeasurementBatch,
)
from backend.services.hardware_ingest_service import (
    AssessmentNotAssigned,
    ConflictingHardwareMessage,
    OutOfSequenceMeasurement,
    InvalidHardwareMeasurement,
    claim_next_assessment,
    release_assessment,
    save_hardware_batch,
)
from backend.services.analysis_service import analyze_completed_assessment

logger = logging.getLogger(__name__)
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


def _raise_service_error(exc: Exception) -> None:
    if isinstance(exc, OutOfSequenceMeasurement):
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if isinstance(exc, (ConflictingHardwareMessage, AssessmentNotAssigned)):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, InvalidHardwareMeasurement):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if isinstance(exc, psycopg.Error):
        logger.error("Erro de banco na rota de hardware: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Armazenamento das medições indisponível; confirme as migrações do banco.",
        ) from exc
    raise exc


@router.get(
    "/assessments/next",
    response_model=HardwareAssessmentStatus,
    summary="Reserva ou retoma a próxima avaliação para o dispositivo",
)
def next_assessment(
    _device: None = Depends(require_device_key),
    x_device_id: str = Header(alias="X-Device-ID", min_length=1, max_length=100),
) -> HardwareAssessmentStatus:
    try:
        return HardwareAssessmentStatus(**claim_next_assessment(x_device_id))
    except psycopg.Error as exc:
        _raise_service_error(exc)


@router.post(
    "/measurements",
    response_model=HardwareMeasurementAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Armazena uma leitura bruta e atualiza a etapa da avaliação ativa",
)
def receive_measurements(
    batch: HardwareMeasurementBatch,
    background_tasks: BackgroundTasks,
    _device: None = Depends(require_device_key),
    x_device_id: str = Header(alias="X-Device-ID", min_length=1, max_length=100),
) -> HardwareMeasurementAccepted:
    if not hmac.compare_digest(x_device_id, batch.device_id):
        raise HTTPException(status_code=409, detail="X-Device-ID deve corresponder ao device_id do lote.")
    try:
        result = save_hardware_batch(batch)
    except (ConflictingHardwareMessage, AssessmentNotAssigned, OutOfSequenceMeasurement, InvalidHardwareMeasurement, psycopg.Error) as exc:
        _raise_service_error(exc)

    if result["complete"] and result["inserted"]:
        background_tasks.add_task(analyze_completed_assessment, batch.assessment_id)

    return HardwareMeasurementAccepted(
        accepted=True,
        duplicate=not result["inserted"],
        device_id=batch.device_id,
        assessment_id=batch.assessment_id,
        message_id=batch.message_id,
        next_measurement=result["next_measurement"],
        complete=result["complete"],
    )


@router.post(
    "/assessments/current/cancel",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancela a avaliação ativa sem apagar medições já recebidas",
)
def cancel_current_assessment(
    _device: None = Depends(require_device_key),
    x_device_id: str = Header(alias="X-Device-ID", min_length=1, max_length=100),
) -> None:
    try:
        release_assessment(x_device_id)
    except psycopg.Error as exc:
        _raise_service_error(exc)


