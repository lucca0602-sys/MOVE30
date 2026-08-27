from fastapi import APIRouter, HTTPException

from app.agent.prompt import criar_prompt
from app.agent.validator import validar_resposta
from app.models.participant import AnalysisResponse, ParticipantIndicators
from app.services.ai_service import enviar_para_ia


router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse)
def analyze_indicators(indicators: ParticipantIndicators) -> AnalysisResponse:
	try:
		prompt = criar_prompt(indicators)
		resposta_ia = enviar_para_ia(prompt, indicators)
		analise = validar_resposta(resposta_ia)
	except (RuntimeError, ValueError, OSError) as erro:
		raise HTTPException(
			status_code=502,
			detail={"error": str(erro), "status": "error"},
		) from erro

	return AnalysisResponse(
		perfil=analise.perfil,
		destaque=analise.destaque,
		oportunidade=analise.oportunidade,
		mensagem=analise.mensagem,
	)
