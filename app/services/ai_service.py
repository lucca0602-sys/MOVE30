import json
import os
from urllib.request import Request, urlopen

from app.models.participant import ParticipantIndicators
from app.services.n8n_service import montar_payload_n8n

def enviar_para_ia(prompt: str, indicators: ParticipantIndicators) -> str:
    """Envia o prompt e os indicadores para o webhook do n8n."""
    webhook_url = os.getenv("N8N_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("N8N_WEBHOOK_URL nao configurada")

    payload = montar_payload_n8n(indicators, prompt)
    request = Request(
        webhook_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=120) as response:
        resposta = json.loads(response.read().decode("utf-8"))

    if isinstance(resposta, list) and resposta:
        resposta = resposta[0]
    if isinstance(resposta, dict):
        resposta = resposta.get("output", resposta.get("answer", resposta))

    return resposta if isinstance(resposta, str) else json.dumps(resposta, ensure_ascii=False)