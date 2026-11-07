import uuid

import pytest
from fastapi.testclient import TestClient

TESTE = {"nome": "Ana Clara Souza", "idade": 16, "peso": 55.0, "altura": 1.62, "fc_repouso": 72}


@pytest.fixture
def publico(db, analise_ia):
    from backend.public_app import app

    return TestClient(app)


def _criar(publico, **extra):
    response = publico.post("/public/teste", json={**TESTE, **extra})
    assert response.status_code == 201, response.text
    return response.json()["token"]


def test_teste_simples_salva_analisa_e_devolve_pelo_token(publico, analise_ia):
    token = _criar(publico)

    # A análise roda em segundo plano logo após a resposta (TestClient executa na hora).
    assert len(analise_ia) == 1
    indicadores = analise_ia[0]["indicadores"]
    assert indicadores["nome"] == "Ana"
    assert indicadores["tipo_avaliacao"] == "simples"
    assert indicadores["fc_pre_teste"] == 72
    assert indicadores["fc_pos_teste"] is None
    assert "normal" in indicadores["faixa_fc_repouso"]
    assert "email" not in indicadores

    resultado = publico.get(f"/public/resultado/{token}").json()
    assert resultado["status"] == "pronto"
    assert resultado["primeiro_nome"] == "Ana"
    assert resultado["imc"] == 21.0
    assert resultado["analise"]["perfil"] == "Perfil de teste"
    assert "id" not in resultado and "email" not in resultado and "nome" not in resultado


def test_resultado_mostra_analisando_enquanto_ia_nao_responde(publico, monkeypatch):
    def ia_fora(_payload):
        raise RuntimeError("IA indisponível")

    monkeypatch.setattr("backend.services.analysis_service.enviar_para_n8n", ia_fora)
    token = _criar(publico)
    resultado = publico.get(f"/public/resultado/{token}").json()
    assert resultado["status"] == "analisando"
    assert resultado["analise"] is None

    from backend.services.participant_service import listar_analises_pendentes, ANALISE_PENDENTE
    from backend.database import get_connection

    # Sem esperar o intervalo de retry, o teste simples deve contar como pendente.
    with get_connection() as connection:
        connection.execute("UPDATE participantes SET ia_proxima_tentativa = NULL;")
    assert len(listar_analises_pendentes()) == 1
    assert "simples" in ANALISE_PENDENTE


def test_token_de_um_nao_mostra_outro_e_token_invalido_falha(publico):
    token_ana = _criar(publico)
    token_bruno = _criar(publico, nome="Bruno Lima", peso=90.0)

    assert publico.get(f"/public/resultado/{token_ana}").json()["primeiro_nome"] == "Ana"
    assert publico.get(f"/public/resultado/{token_bruno}").json()["primeiro_nome"] == "Bruno"
    assert publico.get(f"/public/resultado/{uuid.uuid4()}").status_code == 404
    assert publico.get("/public/resultado/1").status_code == 422
    assert publico.get("/public/resultado/../participantes").status_code in (404, 422)


def test_app_publico_nao_tem_rotas_internas(publico):
    for metodo, rota in (
        ("get", "/participantes"),
        ("get", "/participantes/1"),
        ("get", "/indicadores/coletivos"),
        ("get", "/estacao/status"),
        ("get", "/docs"),
        ("get", "/openapi.json"),
        ("post", "/participantes"),
    ):
        assert getattr(publico, metodo)(rota).status_code == 404, rota


def test_rotas_internas_nao_vazam_token(publico, client):
    _criar(publico)
    participante = client.get("/participantes").json()["participantes"][0]
    assert "token_publico" not in participante
    assert "token_publico" not in client.get(f"/participantes/{participante['id']}").json()["participante"]


def test_teste_simples_nao_entra_na_fila_do_hardware(publico, client):
    _criar(publico)
    assert client.get("/estacao/status").json()["fila"] == []


@pytest.mark.parametrize("campo,valor", [("peso", 5), ("altura", 3), ("fc_repouso", 10), ("nome", "A"), ("idade", 2)])
def test_teste_simples_valida_medidas(publico, campo, valor):
    assert publico.post("/public/teste", json={**TESTE, campo: valor}).status_code == 422
