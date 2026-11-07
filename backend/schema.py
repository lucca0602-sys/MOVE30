"""Estrutura completa do banco: tabela base + migrations, em ordem.

Usado pelos testes (banco move30_test) e por scripts/preparar_evento.py (banco do dia do evento).
"""
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parent / "migrations"

# Tabela como existia antes das migrations (o repositório não tinha script que a criasse).
BASELINE = """
CREATE TABLE participantes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    idade INTEGER NOT NULL,
    peso NUMERIC NOT NULL,
    altura NUMERIC NOT NULL,
    fas INTEGER NOT NULL,
    fc_pre_teste INTEGER NOT NULL,
    fc_pos_teste INTEGER NOT NULL,
    imc NUMERIC NOT NULL,
    resistencia NUMERIC,
    indice_move NUMERIC,
    velocidade_teste NUMERIC,
    tipo_teste VARCHAR(20),
    perfil TEXT,
    destaque TEXT,
    oportunidade TEXT,
    mensagem TEXT
);
"""


def criar_estrutura(connection) -> None:
    """Cria tudo num banco vazio: tabela base e todas as migrations em ordem."""
    connection.execute(BASELINE)
    for migration in sorted(MIGRATIONS.glob("*.sql")):
        connection.execute(migration.read_text(encoding="utf-8"))
