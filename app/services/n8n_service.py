from app.models.participant import ParticipantIndicators


def montar_payload_n8n(indicators: ParticipantIndicators, prompt: str) -> dict:
    """Monta os dados que serao enviados ao webhook do n8n."""
    return {
        "prompt": prompt,
        "indicadores": indicators.model_dump(),
    }
