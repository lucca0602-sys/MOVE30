from uuid import uuid4

import psycopg
import pytest

from backend.services.analysis_service import retry_pending_analyses
from backend.services.analytics_service import calcular_medias_coletivas
from backend.services.backup_service import criar_backup, restaurar_backup
from tests.test_hardware_flow import cadastrar, enviar, proxima, sessao


def completar(client, assessment_id, peso=70, antes=60, depois=140):
    proxima(client)
    assert enviar(client, assessment_id, "weight", peso, "kg").status_code == 202
    assert enviar(client, assessment_id, "heart_rate_rest", antes, "bpm").status_code == 202
    assert enviar(client, assessment_id, "heart_rate_post", depois, "bpm").status_code == 202


def test_medicao_manual_nao_sobrescreve_valor_gravado(client):
    assessment_id = cadastrar(client)
    assert client.patch(f"/participantes/{assessment_id}/medicoes", json={"peso": 70}).status_code == 200

    response = client.patch(f"/participantes/{assessment_id}/medicoes", json={"peso": 90})

    assert response.status_code == 409
    assert float(sessao(client, assessment_id)["peso"]) == 70
    # Repeating the same value is harmless.
    assert client.patch(f"/participantes/{assessment_id}/medicoes", json={"peso": 70}).status_code == 200


def test_banco_bloqueia_sobrescrita_e_apagamento(client, db):
    assessment_id = cadastrar(client)
    with pytest.raises(psycopg.errors.RaiseException):
        with db.get_connection() as connection:
            connection.execute("UPDATE participantes SET altura = 1.9 WHERE id = %s;", (assessment_id,))
    with pytest.raises(psycopg.errors.RaiseException):
        with db.get_connection() as connection:
            connection.execute("DELETE FROM participantes WHERE id = %s;", (assessment_id,))
    assert float(sessao(client, assessment_id)["altura"]) == 1.75


def test_banco_bloqueia_apagar_leitura_bruta(client, db):
    assessment_id = cadastrar(client)
    proxima(client)
    enviar(client, assessment_id, "weight", 70, "kg")
    with pytest.raises(psycopg.errors.RaiseException):
        with db.get_connection() as connection:
            connection.execute("DELETE FROM hardware_measurement_batches;")


def test_analise_salva_nao_e_sobrescrita(client, analise_ia):
    assessment_id = cadastrar(client)
    completar(client, assessment_id)

    response = client.post(f"/participantes/{assessment_id}/analisar")

    assert response.status_code == 409
    assert len(analise_ia) == 1


def test_ia_falha_e_nova_tentativa_automatica_salva_depois(client, monkeypatch, analise_ia):
    monkeypatch.setenv("IA_INTERVALO_S", "0")

    def falha(_payload):
        raise RuntimeError("IA indisponível")

    assessment_id = cadastrar(client)
    with monkeypatch.context() as patch:
        patch.setattr("backend.services.analysis_service.enviar_para_n8n", falha)
        completar(client, assessment_id)
        retry_pending_analyses()
    assert sessao(client, assessment_id)["perfil"] is None
    assert sessao(client, assessment_id)["ia_tentativas"] == 2

    retry_pending_analyses()

    assert sessao(client, assessment_id)["perfil"] == "Perfil de teste"
    # Once saved, nothing is sent again.
    retry_pending_analyses()
    assert len(analise_ia) == 1


def test_nova_tentativa_respeita_o_intervalo(client, monkeypatch, analise_ia):
    monkeypatch.setenv("IA_INTERVALO_S", "3600")

    def falha(_payload):
        raise RuntimeError("IA indisponível")

    assessment_id = cadastrar(client)
    with monkeypatch.context() as patch:
        patch.setattr("backend.services.analysis_service.enviar_para_n8n", falha)
        completar(client, assessment_id)

    retry_pending_analyses()

    assert analise_ia == []
    assert sessao(client, assessment_id)["ia_tentativas"] == 1


def test_mesmo_nome_nao_mistura_pessoas(client):
    primeira = cadastrar(client, nome="Ana Souza", email="ana1@example.com")
    segunda = cadastrar(client, nome="Ana  Souza", email="ana2@example.com")
    retorno = cadastrar(client, nome="ana souza", email="ANA1@example.com")

    linhas = {p["id"]: p for p in client.get("/participantes").json()["participantes"]}

    assert linhas[primeira]["pessoa_id"] != linhas[segunda]["pessoa_id"]
    assert linhas[retorno]["pessoa_id"] == linhas[primeira]["pessoa_id"]


def test_medias_ignoram_incompletas_e_usam_ultima_avaliacao():
    participantes = [
        {"id": 1, "pessoa_id": 1, "peso": 60, "altura": 1.6, "fc_pre_teste": 60, "fc_pos_teste": 100},
        {"id": 2, "pessoa_id": 1, "peso": 62, "altura": 1.6, "fc_pre_teste": 70, "fc_pos_teste": 110},
        {"id": 3, "pessoa_id": 3, "peso": 80, "altura": 1.8, "fc_pre_teste": 80, "fc_pos_teste": 160},
        {"id": 4, "pessoa_id": 4, "peso": None, "altura": 1.7, "fc_pre_teste": None, "fc_pos_teste": None},
        {"id": 5, "pessoa_id": 5, "peso": 900, "altura": 1.7, "fc_pre_teste": 70, "fc_pos_teste": 120},
        {"id": 6, "pessoa_id": 6, "peso": 70, "altura": 1.7, "fc_pre_teste": 0, "fc_pos_teste": 120},
    ]

    medias = calcular_medias_coletivas(participantes)

    assert medias["participantes_validos"] == 2
    assert medias["avaliacoes_incompletas"] == 1
    assert medias["avaliacoes_invalidas"] == 2
    assert medias["peso"] == 71
    assert medias["altura"] == 1.7
    assert medias["fc_pre_teste"] == 75
    assert medias["fc_pos_teste"] == 135
    assert medias["variacao_fc"] == 60


def test_medias_sem_participantes_nao_quebram(client):
    response = client.get("/indicadores/coletivos")

    assert response.status_code == 200
    medias = response.json()["medias"]
    assert medias["participantes_validos"] == 0
    assert medias["peso"] is None
    assert client.get("/participantes").json()["participantes"] == []


def test_medias_atualizam_com_novo_participante(client):
    primeira = cadastrar(client, email="a@example.com")
    completar(client, primeira, peso=60)
    assert client.get("/indicadores/coletivos").json()["medias"]["peso"] == 60

    segunda = cadastrar(client, email="b@example.com")
    assert client.get("/indicadores/coletivos").json()["medias"]["peso"] == 60

    completar(client, segunda, peso=80)
    assert client.get("/indicadores/coletivos").json()["medias"]["peso"] == 70


def test_backup_so_grava_quando_muda_e_restaura_sem_sobrescrever(client, db, tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    assessment_id = cadastrar(client)
    completar(client, assessment_id, peso=72.5)

    arquivo = criar_backup()
    assert arquivo is not None and arquivo.exists()
    assert criar_backup() is None

    with db.get_connection() as connection:
        connection.execute(
            "TRUNCATE hardware_assessment_assignments, hardware_measurement_batches, participantes CASCADE;"
        )

    inseridos = restaurar_backup(arquivo)
    assert inseridos == {"participantes": 1, "hardware_measurement_batches": 3}
    restaurado = sessao(client, assessment_id)
    assert float(restaurado["peso"]) == 72.5
    assert restaurado["perfil"] == "Perfil de teste"

    # A second restore changes nothing, and new IDs continue after the restored ones.
    assert restaurar_backup(arquivo) == {"participantes": 0, "hardware_measurement_batches": 0}
    assert cadastrar(client, email="novo@example.com") == assessment_id + 1


def test_status_da_estacao_mostra_pessoa_e_fila(client):
    primeira = cadastrar(client, nome="Primeira Pessoa")
    segunda = cadastrar(client, nome="Segunda Pessoa")
    proxima(client)

    status = client.get("/estacao/status").json()

    assert status["estacoes"][0]["id"] == primeira
    assert status["estacoes"][0]["peso"] is None
    assert [item["id"] for item in status["fila"]] == [segunda]
    assert status["ultima_concluida"] is None

    assert enviar(client, primeira, "weight", 70, "kg").status_code == 202
    assert float(client.get("/estacao/status").json()["estacoes"][0]["peso"]) == 70

    enviar(client, primeira, "heart_rate_rest", 60, "bpm")
    enviar(client, primeira, "heart_rate_post", 140, "bpm")
    ultima = client.get("/estacao/status").json()["ultima_concluida"]
    assert ultima["id"] == primeira and ultima["analise_pronta"] is True


def test_cadastro_com_campos_vazios_e_rejeitado(client):
    for corpo in ({}, {"nome": "", "email": "", "altura": "", "idade": "", "fas": "", "tipo_teste": ""}):
        assert client.post("/participantes", json=corpo).status_code == 422
    assert client.get("/participantes").json()["participantes"] == []


def test_reenvio_com_conteudo_diferente_e_recusado(client):
    assessment_id = cadastrar(client)
    proxima(client)
    message_id = str(uuid4())
    assert enviar(client, assessment_id, "weight", 70, "kg", message_id).status_code == 202

    response = enviar(client, assessment_id, "weight", 71, "kg", message_id)

    assert response.status_code == 409
    assert float(sessao(client, assessment_id)["peso"]) == 70
