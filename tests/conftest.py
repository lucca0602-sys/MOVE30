import os

import psycopg
import pytest
from fastapi.testclient import TestClient

from backend import database  # noqa: F401  (loads .env before the overrides below)
from backend.schema import criar_estrutura

TEST_DB = "move30_test"


def _server_connection(**kwargs):
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        **kwargs,
    )


@pytest.fixture(scope="session")
def test_database():
    with _server_connection(dbname="postgres", autocommit=True) as connection:
        connection.execute(f"DROP DATABASE IF EXISTS {TEST_DB};")
        connection.execute(f"CREATE DATABASE {TEST_DB};")

    os.environ["DB_NAME"] = TEST_DB
    os.environ["ESP32_API_KEY"] = "chave-de-teste"

    with database.get_connection() as connection:
        criar_estrutura(connection)

    yield

    with _server_connection(dbname="postgres", autocommit=True) as connection:
        connection.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE);")


@pytest.fixture
def db(test_database):
    with database.get_connection() as connection:
        name = connection.execute("SELECT current_database();").fetchone()[0]
        assert name == TEST_DB, "Os testes só podem limpar o banco de teste."
        connection.execute(
            """
            TRUNCATE hardware_assessment_assignments, hardware_measurement_batches, participantes
            RESTART IDENTITY CASCADE;
            """
        )
    return database


@pytest.fixture
def analise_ia(monkeypatch):
    """Replaces the n8n webhook and records every payload sent to it."""
    payloads = []

    def fake(payload):
        payloads.append(payload)
        return {
            "perfil": "Perfil de teste",
            "destaque": "Destaque de teste",
            "oportunidade": "Oportunidade de teste",
            "mensagem": "Mensagem de teste",
        }

    monkeypatch.setattr("backend.services.analysis_service.enviar_para_n8n", fake)
    monkeypatch.setattr("backend.main.enviar_para_n8n", fake)
    return payloads


@pytest.fixture
def client(db, analise_ia):
    from backend.main import app

    return TestClient(app)
