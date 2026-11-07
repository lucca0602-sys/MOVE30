import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ORIGENS_PADRAO = "http://127.0.0.1:5500,http://localhost:5500"


def configurar_cors(app: FastAPI) -> None:
    """Origens permitidas vêm do .env: CORS_ORIGINS (lista) e CORS_ORIGIN_REGEX (opcional)."""
    origens = [
        origem.strip().rstrip("/")
        for origem in os.getenv("CORS_ORIGINS", ORIGENS_PADRAO).split(",")
        if origem.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origens,
        allow_origin_regex=os.getenv("CORS_ORIGIN_REGEX") or None,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=False,
    )
