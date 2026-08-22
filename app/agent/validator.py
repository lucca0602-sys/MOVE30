from app.models.participant import AnalysisResponse


def validar_resposta(resposta: str) -> AnalysisResponse:
	"""Converte a resposta textual da IA para o formato esperado pela API."""
	campos: dict[str, str] = {}
	nomes_campos = {
		"Perfil": "perfil",
		"Destaque": "destaque",
		"Oportunidade": "oportunidade",
		"Mensagem": "mensagem",
	}

	for linha in resposta.splitlines():
		for nome, campo in nomes_campos.items():
			prefixo = f"{nome}:"
			if linha.startswith(prefixo):
				campos[campo] = linha[len(prefixo):].strip()

	if set(campos) != set(nomes_campos.values()):
		raise ValueError("A resposta da IA nao possui todos os campos esperados.")

	return AnalysisResponse(**campos)
