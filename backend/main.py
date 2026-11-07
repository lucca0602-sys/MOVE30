from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from backend.routers.hardware import router as hardware_router

from backend.models.participant import ParticipantIndicators, ManualMeasurements
from backend.models.participant import AnalysisResponse
from backend.database import get_connection
from backend.services.participant_service import (
    MeasurementAlreadySet,
    salvar_participante,
    salvar_analise_ia,
    atualizar_medicoes_manuais,
    status_estacoes,
)
from backend.cors import configurar_cors
from backend.services.participant_service import listar_participantes
from backend.services.participant_service import buscar_participante_por_id
from backend.services.n8n_service import montar_payload_n8n
from backend.services.AI_service import enviar_para_n8n
from pydantic import ValidationError
from backend.services.analytics_service import calcular_resistencia
from backend.services.analytics_service import calcular_imc
from backend.services.analytics_service import calcular_fc_score
from backend.services.analytics_service import calcular_indice_move_coletivo
from backend.services.analytics_service import calcular_medias_coletivas
from backend.services.worker_service import iniciar_workers


@asynccontextmanager
async def lifespan(_app: FastAPI):
    parar = iniciar_workers()
    yield
    parar.set()


app= FastAPI(
    title="MOVE30 Backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(hardware_router)

configurar_cors(app)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/participantes")
def criar_participante(participant: ParticipantIndicators):
    participant_id= salvar_participante(participant)
    return {
        "mensagem": "Participante cadastrado com sucesso",
        "id": participant_id,
        "fc_score": (
            calcular_fc_score(participant.fc_pre_teste, participant.fc_pos_teste)
            if participant.fc_pre_teste is not None and participant.fc_pos_teste is not None
            else None
        ),
        "aguardando_medicoes": any(value is None for value in (
            participant.peso, participant.altura,
            participant.fc_pre_teste, participant.fc_pos_teste,
        )),
    }

@app.get("/db-health")
def db_health():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")

    return {"database": "ok"}

@app.get("/participantes")
def obter_participantes():
    participants = listar_participantes()
    return {"participantes": participants}


@app.get("/indicadores/coletivos")
def obter_indicadores_coletivos():
    participantes = listar_participantes()
    return {
        **calcular_indice_move_coletivo(participantes),
        "medias": calcular_medias_coletivas(participantes),
    }


@app.get("/estacao/status")
def obter_status_estacao():
    return status_estacoes()


@app.get("/participantes/{participant_id}")
def obter_participante_por_id(participant_id: int):
    participant = buscar_participante_por_id(participant_id)
    if participant:
        return {"participante": participant}
    raise HTTPException(
        status_code=404, 
        detail="Participante não encontrado"
    )

@app.patch("/participantes/{participant_id}/medicoes")
def atualizar_medicoes(participant_id: int, measurements: ManualMeasurements):
    try:
        participant = atualizar_medicoes_manuais(
            participant_id,
            measurements.model_dump(exclude_unset=True),
        )
    except MeasurementAlreadySet as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if participant is None:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")
    return {"mensagem": "Medições atualizadas", "id": participant_id}


@app.get("/participantes/{participant_id}/n8n-payload")
def obter_payload_n8n(participant_id: int):
    participant = buscar_participante_por_id(participant_id)
    if participant:
        return {"payload": montar_payload_n8n(participant)}
    raise HTTPException(
        status_code=404,
        detail="Participante não encontrado"
    )

@app.post("/participantes/{participant_id}/analisar")
def analisar_participante(participant_id: int):
    participant = buscar_participante_por_id(participant_id)

    if participant:
        required_measurements = ("peso", "altura", "fc_pre_teste", "fc_pos_teste")
        pending = [field for field in required_measurements if participant.get(field) is None]
        if pending:
            raise HTTPException(
                status_code=409,
                detail="Preencha as medições pendentes no dashboard antes de gerar a análise.",
            )
        if participant.get("perfil"):
            raise HTTPException(status_code=409, detail="Esta avaliação já tem análise salva.")
        payload = montar_payload_n8n(participant)

        try:
            response = enviar_para_n8n(payload)

            # Valida a resposta da IA com o Pydantic
            validated_response = AnalysisResponse.model_validate(response)

            # Persiste os dados validados no banco de dados
            salvar_analise_ia(participant_id, validated_response)

            return {
                "mensagem": "Payload enviado para n8n com sucesso",
                "resposta_n8n": validated_response.model_dump()
            }

        except RuntimeError as e:
            raise HTTPException(
                status_code=502,
                detail=str(e)
            )

        except ValidationError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Resposta da IA fora do formato esperado: {e}"
            )

    raise HTTPException(
        status_code=404,
        detail="Participante não encontrado"
    )