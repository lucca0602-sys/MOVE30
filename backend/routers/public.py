import threading
import time
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.models.participant import TesteSimples
from backend.services.analysis_service import analyze_completed_assessment
from backend.services.participant_service import listar_participantes
from backend.services.public_service import (
    buscar_resultado_publico,
    calcular_painel_publico,
    salvar_teste_simples,
)

router = APIRouter(prefix="/public", tags=["público"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/teste", status_code=201)
def criar_teste_simples(teste: TesteSimples, tarefas: BackgroundTasks):
    participant_id, token = salvar_teste_simples(teste)
    # A IA demora (CPU); responde já e analisa em segundo plano.
    # Se falhar, o worker da API interna tenta de novo (IA_INTERVALO_S).
    tarefas.add_task(analyze_completed_assessment, participant_id)
    # O ID interno não sai: o token é a única chave pública.
    return {"token": str(token)}


@router.get("/resultado/{token}")
def obter_resultado(token: UUID):
    resultado = buscar_resultado_publico(token)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Resultado não encontrado.")
    return resultado


_CACHE_PAINEL = {"quando": 0.0, "dados": None}
_TRAVA_PAINEL = threading.Lock()
CACHE_PAINEL_S = 3


@router.get("/coletivo")
def obter_painel_coletivo():
    """Painel /geral: só médias e contagens; atualiza no máximo a cada 3 s, por mais telas que consultem."""
    with _TRAVA_PAINEL:
        agora = time.monotonic()
        if _CACHE_PAINEL["dados"] is None or agora - _CACHE_PAINEL["quando"] > CACHE_PAINEL_S:
            _CACHE_PAINEL["dados"] = calcular_painel_publico(listar_participantes())
            _CACHE_PAINEL["quando"] = agora
        return _CACHE_PAINEL["dados"]
