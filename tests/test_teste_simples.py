"""Cadastro único do totem (com corrida ou simples), link público do QR e painel /geral."""
import uuid

import pytest
from fastapi.testclient import TestClient

from tests.test_hardware_flow import enviar, proxima

CADASTRO = {"nome": "Ana Clara Souza", "email": "ana@example.com", "idade": 16, "altura": 1.62, "fas": 3}


@pytest.fixture
def publico(db, analise_ia):
    from backend.public_app import app

    return TestClient(app)


def _cadastrar(publico, tipo="simples", **extra):
    corpo = {**CADASTRO, "tipo_avaliacao": tipo, **extra}
    if tipo == "completa":
        corpo.setdefault("tipo_teste", "moderate")
    response = publico.post("/public/cadastro", json=corpo)
    assert response.status_code == 201, response.text
    return response.json()


def _medir_simples(client, peso=55.0, fc=72):
    """A estação pega o próximo da fila e mede peso + 1 batimento."""
    atual = proxima(client)
    assert atual["next_measurement"] == "weight"
    assert enviar(client, atual["assessment_id"], "weight", peso, "kg").json()["complete"] is False
    return enviar(client, atual["assessment_id"], "heart_rate_rest", fc, "bpm").json()


def test_simples_termina_no_primeiro_batimento_e_dispara_a_ia(publico, client, analise_ia):
    cadastro = _cadastrar(publico)
    assert publico.get(f"/public/resultado/{cadastro['token']}").json()["status"] == "aguardando_medicoes"

    resposta = _medir_simples(client)
    # Sem corrida: a estação recebe "complete" e não pede o batimento pós-teste.
    assert resposta["complete"] is True and resposta["next_measurement"] is None
    assert len(analise_ia) == 1
    indicadores = analise_ia[0]["indicadores"]
    assert indicadores["nome"] == "Ana" and indicadores["tipo_avaliacao"] == "simples"
    assert indicadores["fc_pre_teste"] == 72 and indicadores["fc_pos_teste"] is None
    assert "email" not in indicadores

    resultado = publico.get(f"/public/resultado/{cadastro['token']}").json()
    assert resultado["status"] == "pronto" and resultado["imc"] == 21.0
    assert resultado["analise"]["perfil"] == "Perfil de teste"
    assert "id" not in resultado and "email" not in resultado and "nome" not in resultado


def test_com_corrida_continua_pedindo_o_batimento_pos(publico, client):
    _cadastrar(publico, tipo="completa")
    atual = proxima(client)
    enviar(client, atual["assessment_id"], "weight", 60.0, "kg")
    resposta = enviar(client, atual["assessment_id"], "heart_rate_rest", 70, "bpm").json()
    assert resposta["complete"] is False and resposta["next_measurement"] == "heart_rate_post"


def test_simples_e_corrida_dividem_a_mesma_fila_na_ordem(publico, client):
    primeiro = _cadastrar(publico, tipo="completa")
    segundo = _cadastrar(publico, tipo="simples", nome="Bruno Lima")
    fila = client.get("/estacao/status").json()["fila"]
    assert [p["id"] for p in fila] == [primeiro["numero"], segundo["numero"]]


@pytest.mark.parametrize("corpo,erro", [
    ({"tipo_avaliacao": "completa"}, "nível"),                         # bike sem nível
    ({"tipo_avaliacao": "completa", "modalidade": "bike"}, "nível"),
    ({"tipo_avaliacao": "completa", "modalidade": "remo"}, "modalidade"),
    ({"tipo_avaliacao": "simples", "fc_pos_teste": 120}, "esforço"),    # simples com FC pós
])
def test_regras_do_tipo_de_teste(publico, corpo, erro):
    response = publico.post("/public/cadastro", json={**CADASTRO, **corpo})
    assert response.status_code == 422 and erro in response.text


def test_simples_com_medidas_manuais_ja_analisa(publico, analise_ia):
    cadastro = _cadastrar(publico, peso=55.0, fc_pre_teste=72)
    assert len(analise_ia) == 1
    assert publico.get(f"/public/resultado/{cadastro['token']}").json()["status"] == "pronto"


def test_resultado_mostra_analisando_enquanto_ia_nao_responde(publico, client, monkeypatch):
    def ia_fora(_payload):
        raise RuntimeError("IA indisponível")

    monkeypatch.setattr("backend.services.analysis_service.enviar_para_n8n", ia_fora)
    cadastro = _cadastrar(publico)
    _medir_simples(client)
    resultado = publico.get(f"/public/resultado/{cadastro['token']}").json()
    assert resultado["status"] == "analisando" and resultado["analise"] is None

    from backend.database import get_connection
    from backend.services.participant_service import listar_analises_pendentes

    # Sem esperar o intervalo de retry, o simples medido conta como pendente para a IA.
    with get_connection() as connection:
        connection.execute("UPDATE participantes SET ia_proxima_tentativa = NULL;")
    assert len(listar_analises_pendentes()) == 1


def test_token_de_um_nao_mostra_outro_e_token_invalido_falha(publico):
    ana = _cadastrar(publico)
    bruno = _cadastrar(publico, nome="Bruno Lima")
    assert publico.get(f"/public/resultado/{ana['token']}").json()["primeiro_nome"] == "Ana"
    assert publico.get(f"/public/resultado/{bruno['token']}").json()["primeiro_nome"] == "Bruno"
    assert publico.get(f"/public/resultado/{uuid.uuid4()}").status_code == 404
    assert publico.get("/public/resultado/1").status_code == 422


def test_app_publico_nao_tem_rotas_internas(publico):
    for metodo, rota in (
        ("get", "/participantes"),
        ("get", "/participantes/1"),
        ("get", "/indicadores/coletivos"),
        ("get", "/estacao/status"),
        ("get", "/docs"),
        ("get", "/openapi.json"),
        ("post", "/participantes"),
        ("get", "/api/v1/hardware/assessments/next"),
    ):
        assert getattr(publico, metodo)(rota).status_code == 404, rota


def test_rotas_internas_nao_vazam_token(publico, client):
    _cadastrar(publico)
    participante = client.get("/participantes").json()["participantes"][0]
    assert "token_publico" not in participante
    assert "token_publico" not in client.get(f"/participantes/{participante['id']}").json()["participante"]


def _painel(publico):
    from backend.routers import public

    public._CACHE_PAINEL["dados"] = None  # sem cache entre testes
    return publico.get("/public/coletivo").json()


def test_painel_coletivo_esconde_medias_com_poucas_pessoas(publico, client):
    for nome in ("Ana Souza", "Bruno Lima"):
        _cadastrar(publico, nome=nome)
        _medir_simples(client)
    painel = _painel(publico)
    assert painel["participantes"] == 2
    assert painel["medias"]["peso"] == {"valor": None, "n": 2}
    assert painel["distribuicao_imc"] is None


def test_painel_coletivo_so_tem_agregados(publico, client):
    for nome, peso, fc in (("Ana Souza", 50.0, 55), ("Bruno Lima", 70.0, 72), ("Caio Reis", 90.0, 110)):
        _cadastrar(publico, nome=nome, email=f"{nome.split()[0].lower()}@example.com")
        _medir_simples(client, peso=peso, fc=fc)
    painel = _painel(publico)
    assert painel["participantes"] == 3
    assert painel["medias"]["peso"] == {"valor": 70.0, "n": 3}
    assert painel["medias"]["fc_repouso"]["valor"] == 79
    assert [f["total"] for f in painel["distribuicao_fc_repouso"]] == [1, 1, 1]
    assert painel["tipos_avaliacao"] == {"simples": 3}
    texto = str(painel).lower()
    assert "ana" not in texto and "bruno" not in texto and "token" not in texto and "'id'" not in texto


def test_contagem_por_hora_so_tem_totais():
    from datetime import datetime, timezone
    from backend.services.public_service import contar_por_hora

    agora = datetime(2026, 11, 14, 17, 30, tzinfo=timezone.utc)  # 14h30 em Brasília
    pessoas = [{"criado_em": datetime(2026, 11, 14, 16, 5, tzinfo=timezone.utc)},
               {"criado_em": datetime(2026, 11, 14, 16, 50, tzinfo=timezone.utc)},
               {"criado_em": datetime(2026, 11, 14, 17, 10, tzinfo=timezone.utc)},
               {"criado_em": None}]
    serie = contar_por_hora(pessoas, agora)
    assert len(serie) == 12 and serie[-1] == {"hora": "14h", "total": 1} and serie[-2] == {"hora": "13h", "total": 2}


def test_cadastro_sem_email_funciona(publico):
    # O totem não pede mais e-mail.
    corpo = {k: v for k, v in CADASTRO.items() if k != "email"}
    response = publico.post("/public/cadastro", json={**corpo, "tipo_avaliacao": "simples"})
    assert response.status_code == 201, response.text
    assert publico.post("/public/cadastro", json={**corpo, "email": "", "tipo_avaliacao": "simples"}).status_code == 201


@pytest.mark.parametrize("modalidade,nivel,atividade", [
    ("bike", "light", "1 min de bike no nível leve"),
    ("bike", "hard", "3 min de bike no nível pesado"),
    ("flexao", None, "20 repetições de flexão"),
    ("agachamento", "hard", "20 repetições de agachamento"),  # exercício ignora nível
])
def test_bike_e_exercicios_salvam_modalidade_e_vao_para_a_ia(publico, client, db, analise_ia, modalidade, nivel, atividade):
    extra = {"modalidade": modalidade} | ({"tipo_teste": nivel} if nivel else {})
    numero = _cadastrar(publico, "completa", **extra)["numero"]
    with db.get_connection() as connection:
        salvo = connection.execute(
            "SELECT modalidade, tipo_teste, velocidade_teste, resistencia FROM participantes WHERE id = %s;", (numero,)
        ).fetchone()
    bike = modalidade == "bike"
    assert salvo[0] == modalidade
    assert salvo[1] == (nivel if bike else None)
    assert salvo[2] is None  # bike não tem km/h
    assert (salvo[3] is not None) == bike  # só a bike entra no Índice MOVE

    payload = client.get(f"/participantes/{numero}/n8n-payload").json()["payload"]["indicadores"]
    assert payload["modalidade"] == modalidade
    assert payload["atividade"] == atividade


def test_simples_nao_tem_atividade(publico, client):
    numero = _cadastrar(publico)["numero"]
    payload = client.get(f"/participantes/{numero}/n8n-payload").json()["payload"]["indicadores"]
    assert payload["modalidade"] is None and payload["atividade"] is None
