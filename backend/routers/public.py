from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.models.participant import TesteSimples
from backend.services.analysis_service import analyze_completed_assessment
from backend.services.public_service import buscar_resultado_publico, salvar_teste_simples

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
