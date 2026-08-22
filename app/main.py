from fastapi import FastAPI

from app.routes.analysis import router as analysis_router

app = FastAPI(
    title="Agente de IA para Interpretacao de Indicadores",
    version="0.1.0",
)

app.include_router(analysis_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
