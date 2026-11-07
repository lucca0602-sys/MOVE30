import logging

from backend.models.participant import AnalysisResponse
from backend.services.AI_service import enviar_para_n8n
from backend.services.n8n_service import montar_payload_n8n
from backend.services.participant_service import (
    buscar_participante_por_id,
    listar_analises_pendentes,
    reservar_tentativa_analise,
    salvar_analise_ia,
)

logger = logging.getLogger(__name__)


def analyze_completed_assessment(assessment_id: int) -> None:
    """Run AI analysis after measurements commit; a failure stays queued for a new attempt."""
    try:
        if not reservar_tentativa_analise(assessment_id):
            return
        participant = buscar_participante_por_id(assessment_id)
        response = enviar_para_n8n(montar_payload_n8n(participant))
        validated = AnalysisResponse.model_validate(response)
        salvar_analise_ia(assessment_id, validated)
    except Exception:
        # The measurements are already saved; the worker tries again later.
        logger.exception("Falha ao gerar a análise da avaliação %s; nova tentativa mais tarde", assessment_id)


def retry_pending_analyses() -> None:
    for assessment_id in listar_analises_pendentes():
        analyze_completed_assessment(assessment_id)
