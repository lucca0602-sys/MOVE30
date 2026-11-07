"""Banco limpo para o dia do evento (os testes ficam guardados no banco atual).

Nada é apagado: o evento usa outro banco, e voltar é trocar uma linha do .env.

    .\\.venv\\Scripts\\python.exe -m scripts.preparar_evento            -> mostra a situação
    .\\.venv\\Scripts\\python.exe -m scripts.preparar_evento --criar    -> cria o banco vazio (pode rodar antes)
    .\\.venv\\Scripts\\python.exe -m scripts.preparar_evento --ativar   -> sábado 9h: passa a usar o banco do evento
    .\\.venv\\Scripts\\python.exe -m scripts.preparar_evento --voltar   -> volta para o banco de testes

Depois de --ativar ou --voltar, feche as janelas da API, do app público e do Streamlit e rode
.\\scripts\\subir_evento.ps1 de novo (o Funnel não precisa mudar).
"""
import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import psycopg
from dotenv import dotenv_values

from backend.schema import criar_estrutura

RAIZ = Path(__file__).resolve().parent.parent
ENV = RAIZ / ".env"
BANCO_EVENTO = "move30_evento"
MARCA_ANTERIOR = "# DB_NAME antes do evento: "


def _env() -> dict:
    return dotenv_values(ENV)


def _conectar(dbname: str, **kwargs):
    cfg = _env()
    return psycopg.connect(host=cfg.get("DB_HOST"), port=cfg.get("DB_PORT"), user=cfg.get("DB_USER"),
                           password=cfg.get("DB_PASSWORD"), dbname=dbname, **kwargs)


def _existe(nome: str) -> bool:
    with _conectar("postgres", autocommit=True) as c:
        return c.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (nome,)).fetchone() is not None


def _contar(nome: str) -> int | None:
    try:
        with _conectar(nome) as c:
            return c.execute("SELECT COUNT(*) FROM participantes WHERE cancelada_em IS NULL;").fetchone()[0]
    except psycopg.Error:
        return None


def criar() -> None:
    if not _existe(BANCO_EVENTO):
        with _conectar("postgres", autocommit=True) as c:
            c.execute(f"CREATE DATABASE {BANCO_EVENTO};")
        print(f"Banco {BANCO_EVENTO} criado.")
    with _conectar(BANCO_EVENTO) as c:
        tem_tabela = c.execute("SELECT to_regclass('public.participantes') IS NOT NULL;").fetchone()[0]
        if tem_tabela:
            print(f"{BANCO_EVENTO} já tem a estrutura (nada a fazer).")
            return
        criar_estrutura(c)
    print(f"Estrutura criada em {BANCO_EVENTO}: tabela, migrations, proteções contra apagar/sobrescrever.")


def _trocar_db_name(novo: str, guardar_anterior: bool) -> str:
    linhas = ENV.read_text(encoding="utf-8").splitlines()
    anterior = next((l.split("=", 1)[1] for l in linhas if l.startswith("DB_NAME=")), "")
    copia = ENV.with_name(f".env.bak-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(ENV, copia)  # backup do .env antes de mexer (fica fora do Git: .env*)
    linhas = [l for l in linhas if not (guardar_anterior and l.startswith(MARCA_ANTERIOR))]
    saida = []
    for l in linhas:
        if l.startswith("DB_NAME="):
            if guardar_anterior:
                saida.append(f"{MARCA_ANTERIOR}{anterior}")
            saida.append(f"DB_NAME={novo}")
        else:
            saida.append(l)
    ENV.write_text("\n".join(saida) + "\n", encoding="utf-8")
    print(f"Backup do .env: {copia.name}")
    return anterior


def ativar() -> None:
    criar()
    atual = _env().get("DB_NAME")
    if atual == BANCO_EVENTO:
        print(f"O .env já usa {BANCO_EVENTO}.")
    else:
        anterior = _trocar_db_name(BANCO_EVENTO, guardar_anterior=True)
        print(f"DB_NAME: {anterior} -> {BANCO_EVENTO}. Os testes continuam guardados em {anterior}.")
    print("\nAGORA: feche as janelas da API, do app público e do Streamlit e rode .\\scripts\\subir_evento.ps1")


def voltar() -> None:
    linhas = ENV.read_text(encoding="utf-8").splitlines()
    anterior = next((l[len(MARCA_ANTERIOR):] for l in linhas if l.startswith(MARCA_ANTERIOR)), None)
    if not anterior:
        sys.exit("Não achei no .env qual era o banco anterior. Edite DB_NAME à mão.")
    _trocar_db_name(anterior, guardar_anterior=False)
    ENV.write_text("\n".join(l for l in ENV.read_text(encoding="utf-8").splitlines()
                             if not l.startswith(MARCA_ANTERIOR)) + "\n", encoding="utf-8")
    print(f"DB_NAME voltou para {anterior}. Reinicie os serviços (.\\scripts\\subir_evento.ps1).")


def situacao() -> None:
    atual = _env().get("DB_NAME")
    print(f"Banco em uso (.env): {atual}  ->  {_contar(atual)} avaliação(ões) ativa(s)")
    if _existe(BANCO_EVENTO):
        print(f"Banco do evento:     {BANCO_EVENTO}  ->  {_contar(BANCO_EVENTO)} avaliação(ões) ativa(s)")
    else:
        print(f"Banco do evento:     {BANCO_EVENTO}  ->  ainda não criado (rode --criar)")


def main() -> None:
    os.chdir(RAIZ)
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--criar", action="store_true")
    grupo.add_argument("--ativar", action="store_true")
    grupo.add_argument("--voltar", action="store_true")
    args = parser.parse_args()
    if args.criar:
        criar()
    elif args.ativar:
        ativar()
    elif args.voltar:
        voltar()
    else:
        situacao()


if __name__ == "__main__":
    main()
