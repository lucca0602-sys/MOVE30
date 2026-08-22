import json

from pydantic import ValidationError

from app.models.participant import AnalysisResponse


def validar_resposta(resposta: str) -> AnalysisResponse:
	"""Converte e valida a resposta JSON recebida da IA."""
	try:
		dados = json.loads(resposta)
		return AnalysisResponse.model_validate(dados)
	
	except (json.JSONDecodeError, ValidationError) as erro:
		raise ValueError("A resposta da IA possui um formato invalido.") from erro
