"""Arquivo pós-feira: o script copia só o que o link público mostra, e nada de dado interno."""
import os

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from scripts.publicar_resultados import coletar, publicar
from tests.conftest import TEST_DB

PROIBIDOS = ("email", "nome", "id", "pessoa_id", "token_publico", "fas")


@pytest.fixture
def destino(db):
    """O 'Neon' do teste é o próprio move30_test, com as tabelas do arquivo zeradas."""
    url = make_conninfo(host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"), user=os.getenv("DB_USER"),
                        password=os.getenv("DB_PASSWORD"), dbname=TEST_DB)
    with psycopg.connect(url) as connection:
        connection.execute("DROP TABLE IF EXISTS resultados_publicos, painel_publico;")
    return url


def inserir(db, nome, email, perfil="Perfil", cancelada=False, mensagem="M"):
    with db.get_connection() as connection:
        return str(connection.execute(
            """
            INSERT INTO participantes (nome, email, idade, peso, altura, fas, fc_pre_teste, fc_pos_teste,
                                       imc, tipo_teste, perfil, destaque, oportunidade, mensagem, cancelada_em)
            VALUES (%s, %s, 16, 60, 1.7, 4, 70, 140, 20.8, 'moderate', %s, 'D', 'O', %s,
                    CASE WHEN %s THEN NOW() END)
            RETURNING token_publico;
            """,
            (nome, email, perfil, mensagem, cancelada),
        ).fetchone()[0])


def ler(url):
    with psycopg.connect(url) as connection:
        resultados = dict(connection.execute("SELECT token_publico::text, dados FROM resultados_publicos;").fetchall())
        painel = connection.execute("SELECT dados FROM painel_publico WHERE id = 1;").fetchone()
    return resultados, painel[0] if painel else None


def test_publica_so_prontos_e_sem_dado_interno(db, destino):
    pronta = inserir(db, "Ana Maria Souza", "ana@example.com")
    sem_analise = inserir(db, "Bruno Lima", "bruno@example.com", perfil=None)
    cancelada = inserir(db, "Carla Dias", "carla@example.com", cancelada=True)

    publicar(destino, *coletar())
    resultados, painel = ler(destino)

    assert set(resultados) == {pronta}
    assert sem_analise not in resultados and cancelada not in resultados
    dados = resultados[pronta]
    assert dados["primeiro_nome"] == "Ana"
    assert dados["status"] == "pronto"
    assert dados["analise"] == {"perfil": "Perfil", "destaque": "D", "oportunidade": "O", "mensagem": "M"}
    assert not set(dados) & set(PROIBIDOS)
    texto = str(dados) + str(painel)
    for vazamento in ("ana@example.com", "Souza", "Bruno", "Carla"):
        assert vazamento not in texto
    # Mesmo formato do /public/coletivo; 2 pessoas ativas (abaixo do mínimo, então sem média).
    assert painel["participantes"] == 2
    assert painel["medias"]["imc"]["valor"] is None


def test_nome_completo_escrito_pela_ia_vira_primeiro_nome(db, destino):
    token = inserir(db, "Ana Maria Souza", "ana@example.com",
                    mensagem="Ana Maria Souza, 16 anos, foi bem. ana souza também. Anabela Souza não é ela.")

    publicar(destino, *coletar())
    resultados, _ = ler(destino)

    assert resultados[token]["analise"]["mensagem"] == "Ana, 16 anos, foi bem. Ana também. Anabela Souza não é ela."


def test_idempotente_e_espelha_cancelamento(db, destino):
    tokens = [inserir(db, f"Pessoa {i}", f"p{i}@example.com") for i in range(3)]
    publicar(destino, *coletar())
    feito = publicar(destino, *coletar())
    assert feito == {"publicados": 3, "removidos": 0}

    with db.get_connection() as connection:
        connection.execute("UPDATE participantes SET cancelada_em = NOW() WHERE token_publico = %s;", (tokens[0],))
    feito = publicar(destino, *coletar())
    resultados, painel = ler(destino)

    assert feito == {"publicados": 2, "removidos": 1}
    assert set(resultados) == set(tokens[1:])
    assert painel["participantes"] == 2


def test_grafico_por_hora_ancorado_na_ultima_avaliacao(db, destino):
    for i in range(3):
        inserir(db, f"Pessoa {i}", f"p{i}@example.com")
    with db.get_connection() as connection:
        connection.execute("UPDATE participantes SET criado_em = TIMESTAMPTZ '2026-11-14 10:30-03';")

    _, painel = coletar()

    por_hora = painel["avaliacoes_por_hora"]
    assert por_hora[-1] == {"hora": "10h", "total": 3}
    assert painel["medias"]["imc"]["valor"] == 20.8


def test_sem_publicar_nao_envia_nada(db, destino, monkeypatch, capsys):
    import sys

    from scripts import publicar_resultados

    inserir(db, "Ana", "ana@example.com")
    monkeypatch.setattr(sys, "argv", ["publicar_resultados", "--banco", TEST_DB])
    monkeypatch.setenv("ARQUIVO_DATABASE_URL", destino)
    publicar_resultados.main()

    assert "1 resultado(s)" in capsys.readouterr().out
    with psycopg.connect(destino) as connection:
        assert connection.execute("SELECT to_regclass('public.resultados_publicos');").fetchone()[0] is None
