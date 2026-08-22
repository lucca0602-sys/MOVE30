from fastapi import APIRouter

from app.models.participant import AnalysisResponse, ParticipantIndicators


router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse)
def analyze_indicators(indicators: ParticipantIndicators) -> AnalysisResponse:
	return AnalysisResponse(
		perfil="Analise recebida",
		destaque=f"Indice MOVE: {indicators.indice_move}",
		oportunidade="Aguardando interpretacao do agente",
		mensagem="Os indicadores foram validados com sucesso.",
	)
