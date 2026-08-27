import json

from pydantic import ValidationError

from app.models.participant import AnalysisResponse


def _extrair_json(resposta: str) -> str:
	conteudo = resposta.strip()
	if conteudo.startswith("```"):
		linhas = conteudo.splitlines()
		conteudo = "\n".join(linhas[1:-1]).strip()

	if not conteudo.startswith("{"):
		inicio = conteudo.find("{")
		fim = conteudo.rfind("}")
		if inicio == -1 or fim == -1 or fim < inicio:
			raise ValueError("A resposta da IA nao contem um objeto JSON.")
		conteudo = conteudo[inicio:fim + 1]

	return conteudo


def validar_resposta(resposta: str) -> AnalysisResponse:
	"""Converte e valida a resposta JSON recebida da IA."""
	try:
		dados = json.loads(_extrair_json(resposta))
		return AnalysisResponse.model_validate(dados)

	except (json.JSONDecodeError, ValidationError) as erro:
		raise ValueError("A resposta da IA possui um formato invalido.") from erro
