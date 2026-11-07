"""App público: o ÚNICO processo exposto na internet (via Tailscale Funnel).

Só contém as rotas de /public. Listagem de participantes, hardware, estação e
dashboards ficam no app interno (backend.main, porta 8002), que não sai da rede local.
Rodar com: uvicorn backend.public_app:app --host 127.0.0.1 --port 8003
"""
from fastapi import FastAPI

from backend.cors import configurar_cors
from backend.routers.public import router as public_router

# Sem /docs nem /openapi.json: não precisa anunciar as rotas para quem chegar pela URL pública.
app = FastAPI(title="MOVE30 público", docs_url=None, redoc_url=None, openapi_url=None)
configurar_cors(app)
app.include_router(public_router)
