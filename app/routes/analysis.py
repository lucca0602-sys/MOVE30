from fastapi import APIRouter

from app.agent.prompt import criar_prompt
from app.models.participant import AnalysisResponse, ParticipantIndicators
from app.services.ai_service import enviar_para_ia


router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse)
def analyze_indicators(indicators: ParticipantIndicators) -> AnalysisResponse:
	prompt = criar_prompt(indicators)
	resposta_ia = enviar_para_ia(prompt)

	return AnalysisResponse(
		perfil="Analise recebida",
		destaque=f"Indice MOVE: {indicators.indice_move}",
		oportunidade="Aguardando interpretacao do agente",
		mensagem=resposta_ia,
	)
