"""Runs the Streamlit pages against a real API on the test database."""
import sys
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from tests.test_simulacao_completa import Api, cadastrar, enviar, ia_falsa, proxima  # noqa: F401

DASHBOARD = Path(__file__).resolve().parent.parent / "Dashboard"
sys.path.insert(0, str(DASHBOARD))
PAGINAS = ("coletivo", "pessoal", "estacao")


@pytest.fixture
def api_dashboard(db, ia_falsa, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    servidor = Api()
    monkeypatch.setenv("API_URL", servidor.url)
    st.cache_data.clear()
    yield servidor
    servidor.desligar()


def abrir(pagina):
    app = AppTest.from_file(str(DASHBOARD / "app_pages" / f"{pagina}.py"), default_timeout=90).run()
    assert not app.exception, app.exception
    return app


@pytest.mark.parametrize("pagina", PAGINAS)
def test_paginas_sem_participantes(api_dashboard, pagina):
    app = abrir(pagina)
    assert not app.error
    assert app.info or pagina == "estacao" or app.caption


@pytest.mark.parametrize("pagina", PAGINAS)
def test_paginas_com_muitos_participantes_e_nomes_repetidos(api_dashboard, db, pagina):
    # Bulk insert: 400 complete people, some with the same name, plus incomplete ones.
    with db.get_connection() as connection:
        for numero in range(400):
            connection.execute(
                """
                INSERT INTO participantes (nome, email, idade, peso, altura, fas, fc_pre_teste, fc_pos_teste,
                                           imc, resistencia, velocidade_teste, tipo_teste, perfil, mensagem)
                VALUES (%s, %s, 30, 70, 1.7, 4, 60, 140, 24.2, 50, 10, 'moderate', 'P', 'M');
                """,
                (f"Pessoa {numero % 150}", f"p{numero}@example.com"),
            )
        for numero in range(5):
            connection.execute(
                "INSERT INTO participantes (nome, email, idade, altura, fas, tipo_teste) VALUES (%s, %s, 30, 1.7, 4, 'light');",
                (f"Na fila {numero}", f"f{numero}@example.com"),
            )

    app = abrir(pagina)

    assert not app.error
    texto = " ".join(item.value for item in app.caption)
    if pagina == "coletivo":
        assert "Médias de 400 pessoa(s)" in texto
        assert "5 avaliação(ões) incompleta(s)" in texto


@pytest.mark.parametrize("peso,altura,antes,depois,analise,esperada", [
    (None, None, None, None, False, "Peso"),
    (70, None, None, None, False, "Altura"),
    (70, 1.75, None, None, False, "FC de repouso"),
    (70, 1.75, 60, None, False, "Esforço e FC depois"),
    (70, 1.75, 60, 140, False, "Análise da IA"),
    (70, 1.75, 60, 140, True, "Concluído"),
])
def test_etapa_atual_segue_os_dados_salvos(peso, altura, antes, depois, analise, esperada):
    from shared import ETAPAS, etapa_atual

    assert ETAPAS[etapa_atual(peso, altura, antes, depois, analise)] == esperada


def test_estacao_mostra_pessoa_e_etapa_ao_vivo(api_dashboard):  # noqa: F811
    api = api_dashboard
    pessoa = cadastrar(api, "Pessoa Estacao", "estacao@example.com", 1.70)
    proxima(api, "estacao-01")

    app = abrir("estacao")
    assert any("Pessoa Estacao" in item.value for item in app.markdown)
    assert any("Suba na balança" in item.value for item in app.markdown)

    assert enviar(api, "estacao-01", pessoa, "weight", 70, "kg").status_code == 202
    st.cache_data.clear()

    app = abrir("estacao")
    assert any("dedo no sensor" in item.value for item in app.markdown)
    assert any("70,0 kg" in item.value for item in app.caption)


def test_pessoal_nao_mistura_mesmo_nome(api_dashboard):  # noqa: F811
    api = api_dashboard
    primeira = cadastrar(api, "Ana Souza", "ana1@example.com", 1.60)
    segunda = cadastrar(api, "Ana Souza", "ana2@example.com", 1.72)
    proxima(api, "estacao-01")
    assert enviar(api, "estacao-01", primeira, "weight", 55, "kg").status_code == 202

    app = abrir("pessoal")

    opcoes = app.selectbox[0].options
    assert sorted(opcoes) == sorted([f"Ana Souza (#{primeira})", f"Ana Souza (#{segunda})"])


def test_pessoal_reemite_qr_da_ultima_avaliacao(api_dashboard, db, monkeypatch):  # noqa: F811
    monkeypatch.setenv("FRONT_PUBLIC_URL", "https://front.example/")
    api = api_dashboard
    avaliacao = cadastrar(api, "Bia Lima", "bia@example.com", 1.65)
    with db.get_connection() as connection:
        token = str(connection.execute(
            "SELECT token_publico FROM participantes WHERE id = %s;", (avaliacao,)
        ).fetchone()[0])

    app = abrir("pessoal")
    assert not any(token in bloco.value for bloco in app.code)

    app.toggle(key="mostrar_qr").set_value(True).run()
    assert not app.exception, app.exception
    assert [bloco.value for bloco in app.code] == [f"https://front.example/dash/{token}"]
    assert any(f"#{avaliacao}" in texto.value for texto in app.markdown)


@pytest.mark.parametrize("pagina", PAGINAS)
def test_paginas_avisam_backend_offline_sem_quebrar(monkeypatch, pagina):
    monkeypatch.setenv("API_URL", "http://127.0.0.1:9")  # porta fechada: API desligada
    st.cache_data.clear()
    app = abrir(pagina)
    assert any("Backend offline" in aviso.value for aviso in app.warning)
