import threading
import time
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.models.participant import ParticipantIndicators
from backend.services.analysis_service import analyze_completed_assessment
from backend.services.participant_service import listar_participantes, salvar_participante
from backend.services.public_service import buscar_resultado_publico, calcular_painel_publico

router = APIRouter(prefix="/public", tags=["público"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/cadastro", status_code=201)
def cadastrar(participante: ParticipantIndicators, tarefas: BackgroundTasks):
    """Cadastro do totem (com corrida ou simples). As medidas vêm depois, da estação."""
    participant_id, token = salvar_participante(participante)
    medidas = [participante.peso, participante.altura, participante.fc_pre_teste]
    if participante.tipo_avaliacao == "completa":
        medidas.append(participante.fc_pos_teste)
    if all(valor is not None for valor in medidas):
        # Medidas informadas à mão no cadastro: já analisa em segundo plano.
        tarefas.add_task(analyze_completed_assessment, participant_id)
    # "numero" é a senha da fila da estação (o Streamlit da equipe mostra o mesmo número).
    # O token é a chave do link pessoal /dash/<token> do QR Code.
    return {"token": str(token), "numero": participant_id}


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
