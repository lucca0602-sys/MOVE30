from fastapi import APIRouter

from app.agent.prompt import criar_prompt
from app.agent.validator import validar_resposta
from app.models.participant import AnalysisResponse, ParticipantIndicators
from app.services.ai_service import enviar_para_ia


router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse)
def analyze_indicators(indicators: ParticipantIndicators) -> AnalysisResponse:
	prompt = criar_prompt(indicators)
	resposta_ia = enviar_para_ia(prompt)
	analise = validar_resposta(resposta_ia)

	return AnalysisResponse(
		perfil=analise.perfil,
		destaque=analise.destaque,
		oportunidade=analise.oportunidade,
		mensagem=analise.mensagem,
	)
