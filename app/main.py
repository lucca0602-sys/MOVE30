from fastapi import FastAPI

app = FastAPI(
    title="Agente de IA para Interpretacao de Indicadores",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
