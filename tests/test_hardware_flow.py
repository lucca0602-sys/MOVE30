from uuid import uuid4

import pytest

DEVICE = "estacao-01"
HEADERS = {"X-Device-Key": "chave-de-teste", "X-Device-ID": DEVICE}


def cadastro(**overrides):
    dados = {
        "nome": "Pessoa Teste",
        "email": "Pessoa.Teste@Example.com",
        "altura": 1.75,
        "idade": 30,
        "fas": 4,
        "tipo_teste": "moderate",
    }
    dados.update(overrides)
    return dados


def cadastrar(client, **overrides):
    response = client.post("/participantes", json=cadastro(**overrides))
    assert response.status_code == 200, response.text
    return response.json()["id"]


def proxima(client, device=DEVICE):
    headers = {**HEADERS, "X-Device-ID": device}
    response = client.get("/api/v1/hardware/assessments/next", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def enviar(client, assessment_id, name, value, unit, message_id=None, device=DEVICE):
    return client.post(
        "/api/v1/hardware/measurements",
        headers={**HEADERS, "X-Device-ID": device},
        json={
            "device_id": device,
            "assessment_id": assessment_id,
            "message_id": message_id or str(uuid4()),
            "measured_at": "2026-11-03T12:00:00Z",
            "measurements": [{"name": name, "value": value, "unit": unit}],
        },
    )


def sessao(client, assessment_id):
    response = client.get(f"/participantes/{assessment_id}")
    assert response.status_code == 200, response.text
    return response.json()["participante"]


def test_fluxo_completo_salva_medicoes_e_analise(client, analise_ia):
    assessment_id = cadastrar(client)

    reserva = proxima(client)
    assert reserva["assessment_id"] == assessment_id
    assert reserva["next_measurement"] == "weight"

    peso = enviar(client, assessment_id, "weight", 72.5, "kg")
    assert peso.status_code == 202, peso.text
    assert peso.json()["next_measurement"] == "heart_rate_rest"
    assert float(sessao(client, assessment_id)["peso"]) == 72.5
    assert float(sessao(client, assessment_id)["imc"]) == 23.67

    repouso = enviar(client, assessment_id, "heart_rate_rest", 65, "bpm")
    assert repouso.status_code == 202, repouso.text
    assert repouso.json()["next_measurement"] == "heart_rate_post"
    assert sessao(client, assessment_id)["fc_pre_teste"] == 65
    assert analise_ia == []

    pos = enviar(client, assessment_id, "heart_rate_post", 150, "bpm")
    assert pos.status_code == 202, pos.text
    assert pos.json()["complete"] is True

    final = sessao(client, assessment_id)
    assert final["fc_pos_teste"] == 150
    assert final["perfil"] == "Perfil de teste"
    assert final["mensagem"] == "Mensagem de teste"

    assert len(analise_ia) == 1
    indicadores = analise_ia[0]["indicadores"]
    assert indicadores["altura"] == 1.75
    assert indicadores["peso"] == 72.5
    assert indicadores["fc_pre_teste"] == 65
    assert indicadores["fc_pos_teste"] == 150

    assert proxima(client)["status"] == "waiting"


@pytest.mark.parametrize("alteracao", [
    {"altura": 0.5},
    {"altura": 3.0},
    {"email": "sem-arroba"},
    {"peso": 500},
    {"fc_pre_teste": 10},
    {"fc_pos_teste": 250},
])
def test_cadastro_rejeita_dados_invalidos(client, alteracao):
    response = client.post("/participantes", json=cadastro(**alteracao))
    assert response.status_code == 422


def test_email_fica_no_banco_e_nao_sai_pela_api_nem_para_ia(client, db, analise_ia):
    assessment_id = cadastrar(client)

    with db.get_connection() as connection:
        guardado = connection.execute(
            "SELECT email FROM participantes WHERE id = %s;", (assessment_id,)
        ).fetchone()[0]
    assert guardado == "pessoa.teste@example.com"

    assert "email" not in sessao(client, assessment_id)
    assert "email" not in client.get("/participantes").json()["participantes"][0]

    proxima(client)
    enviar(client, assessment_id, "weight", 70, "kg")
    enviar(client, assessment_id, "heart_rate_rest", 60, "bpm")
    enviar(client, assessment_id, "heart_rate_post", 140, "bpm")
    enviado = str(analise_ia[0]).lower()
    assert "pessoa.teste@example.com" not in enviado
    assert "pessoa teste" not in enviado


@pytest.mark.parametrize("name,value,unit", [
    ("weight", 5, "kg"),
    ("weight", 300, "kg"),
    ("weight", 70000, "g"),
])
def test_peso_absurdo_e_rejeitado(client, name, value, unit):
    assessment_id = cadastrar(client)
    proxima(client)

    response = enviar(client, assessment_id, name, value, unit)

    assert response.status_code == 422
    assert "detail" in response.json()
    assert sessao(client, assessment_id)["peso"] is None


@pytest.mark.parametrize("value", [10, 250, 70.5])
def test_fc_absurda_e_rejeitada(client, value):
    assessment_id = cadastrar(client)
    proxima(client)
    assert enviar(client, assessment_id, "weight", 70, "kg").status_code == 202

    response = enviar(client, assessment_id, "heart_rate_rest", value, "bpm")

    assert response.status_code == 422
    assert sessao(client, assessment_id)["fc_pre_teste"] is None


def test_leitura_nao_altera_outra_sessao(client):
    primeira = cadastrar(client, nome="Primeira Pessoa")
    segunda = cadastrar(client, nome="Segunda Pessoa")
    assert proxima(client)["assessment_id"] == primeira

    response = enviar(client, segunda, "weight", 80, "kg")

    assert response.status_code == 409
    assert sessao(client, segunda)["peso"] is None
    assert sessao(client, primeira)["peso"] is None


def test_medida_ja_gravada_nao_e_sobrescrita(client):
    assessment_id = cadastrar(client)
    proxima(client)
    assert enviar(client, assessment_id, "weight", 70, "kg").status_code == 202

    response = enviar(client, assessment_id, "weight", 95, "kg")

    assert response.status_code == 409
    assert float(sessao(client, assessment_id)["peso"]) == 70


def test_fc_pos_antes_do_repouso_e_recusada(client):
    assessment_id = cadastrar(client)
    proxima(client)
    enviar(client, assessment_id, "weight", 70, "kg")

    response = enviar(client, assessment_id, "heart_rate_post", 150, "bpm")

    assert response.status_code == 409
    assert sessao(client, assessment_id)["fc_pos_teste"] is None


def test_reenvio_nao_duplica_medida_nem_analise(client, analise_ia):
    assessment_id = cadastrar(client)
    proxima(client)
    enviar(client, assessment_id, "weight", 70, "kg")
    enviar(client, assessment_id, "heart_rate_rest", 60, "bpm")
    message_id = str(uuid4())
    assert enviar(client, assessment_id, "heart_rate_post", 140, "bpm", message_id).status_code == 202

    repetido = enviar(client, assessment_id, "heart_rate_post", 140, "bpm", message_id)

    assert repetido.status_code == 202
    assert repetido.json()["duplicate"] is True
    assert repetido.json()["complete"] is True
    assert len(analise_ia) == 1


def test_cancelar_tira_da_fila_e_libera_a_proxima(client):
    desistiu = cadastrar(client, nome="Pessoa Desistiu")
    seguinte = cadastrar(client, nome="Pessoa Seguinte")
    assert proxima(client)["assessment_id"] == desistiu

    response = client.post("/api/v1/hardware/assessments/current/cancel", headers=HEADERS)

    assert response.status_code == 204
    assert proxima(client)["assessment_id"] == seguinte
    assert sessao(client, desistiu)["cancelada_em"] is not None
    nomes = [p["nome"] for p in client.get("/participantes").json()["participantes"]]
    assert nomes == ["Pessoa Seguinte"]


def test_cancelar_preserva_medidas_recebidas(client):
    assessment_id = cadastrar(client)
    proxima(client)
    enviar(client, assessment_id, "weight", 70, "kg")

    client.post("/api/v1/hardware/assessments/current/cancel", headers=HEADERS)

    assert float(sessao(client, assessment_id)["peso"]) == 70


def test_sem_altura_no_cadastro_o_sensor_mede_depois_do_peso(client):
    assessment_id = cadastrar(client, altura=None)

    reserva = proxima(client)
    assert reserva["assessment_id"] == assessment_id
    assert reserva["next_measurement"] == "weight"
    assert client.get("/estacao/status").json()["estacoes"][0]["altura"] is None

    peso = enviar(client, assessment_id, "weight", 72.5, "kg")
    assert peso.json()["next_measurement"] == "height"
    assert sessao(client, assessment_id)["imc"] is None

    altura = enviar(client, assessment_id, "height", 1.75, "m")
    assert altura.status_code == 202, altura.text
    assert altura.json()["next_measurement"] == "heart_rate_rest"
    assert float(sessao(client, assessment_id)["imc"]) == 23.67


def test_altura_digitada_pula_o_sensor(client):
    assessment_id = cadastrar(client)
    proxima(client)

    peso = enviar(client, assessment_id, "weight", 72.5, "kg")

    assert peso.json()["next_measurement"] == "heart_rate_rest"


def test_altura_fora_de_ordem_e_recusada(client):
    assessment_id = cadastrar(client, altura=None)
    proxima(client)

    response = enviar(client, assessment_id, "height", 1.75, "m")

    assert response.status_code == 409


def test_dois_dispositivos_nao_pegam_a_mesma_sessao(client):
    primeira = cadastrar(client, nome="Primeira Pessoa")
    segunda = cadastrar(client, nome="Segunda Pessoa")

    assert proxima(client, "estacao-01")["assessment_id"] == primeira
    assert proxima(client, "estacao-02")["assessment_id"] == segunda


def test_falha_da_ia_nao_perde_medidas_e_pode_tentar_de_novo(client, monkeypatch):
    def falha(_payload):
        raise RuntimeError("IA indisponível")

    assessment_id = cadastrar(client)
    proxima(client)
    enviar(client, assessment_id, "weight", 70, "kg")
    enviar(client, assessment_id, "heart_rate_rest", 60, "bpm")
    with monkeypatch.context() as patch:
        patch.setattr("backend.services.analysis_service.enviar_para_n8n", falha)
        response = enviar(client, assessment_id, "heart_rate_post", 140, "bpm")

    assert response.status_code == 202
    salvo = sessao(client, assessment_id)
    assert salvo["fc_pos_teste"] == 140
    assert salvo["perfil"] is None

    assert client.post(f"/participantes/{assessment_id}/analisar").status_code == 200
    assert sessao(client, assessment_id)["perfil"] == "Perfil de teste"


def test_chave_invalida_e_recusada(client):
    assessment_id = cadastrar(client)
    response = client.get(
        "/api/v1/hardware/assessments/next",
        headers={**HEADERS, "X-Device-Key": "errada"},
    )
    assert response.status_code == 401
    assert sessao(client, assessment_id)["peso"] is None


def test_medicao_manual_continua_funcionando(client):
    assessment_id = cadastrar(client)

    response = client.patch(f"/participantes/{assessment_id}/medicoes", json={"peso": 70})

    assert response.status_code == 200
    assert float(sessao(client, assessment_id)["imc"]) == 22.86
    assert proxima(client)["next_measurement"] == "heart_rate_rest"
