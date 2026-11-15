"""Publica o arquivo na nuvem: /dash/<token> e /geral continuam no ar se o PC/Funnel cair.

Copia do banco local para o Postgres da nuvem (Neon) só o que o link público já mostra:
o JSON de /public/resultado de cada avaliação ativa (primeiro nome, idade, medidas,
status e, quando pronta, a análise da IA) e os agregados do /geral.
Avaliação ainda sem análise também vai, para o link mostrar "analisando" em vez de
"não encontrado" se o backend cair no meio da feira. Nada de e-mail, nome completo ou ID:
se a IA escreveu o nome completo no texto, ele vira só o primeiro nome.
As Vercel Functions (frontend/api) leem dali.

Idempotente: pode rodar quantas vezes quiser (upsert por token). Avaliação cancelada ou que
deixou de existir no banco local sai da nuvem também.

    .\\.venv\\Scripts\\python.exe -m scripts.publicar_resultados             -> mostra o que seria publicado
    .\\.venv\\Scripts\\python.exe -m scripts.publicar_resultados --publicar  -> publica de verdade
    ... --publicar --loop 120  -> republica a cada 120 s (durante a feira; subir_evento.ps1 liga)

A connection string do Neon vem de ARQUIVO_DATABASE_URL no .env (nunca no git).
O banco de origem é o do evento (move30_evento); --banco troca.
"""
import argparse
import os
import re
import sys
import time

import psycopg
from psycopg.types.json import Jsonb

from backend import database  # noqa: F401  (carrega o .env)

BANCO_EVENTO = "move30_evento"

ESTRUTURA = """
CREATE TABLE IF NOT EXISTS resultados_publicos (
    token_publico UUID PRIMARY KEY,
    dados JSONB NOT NULL,
    publicado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS painel_publico (
    id SMALLINT PRIMARY KEY CHECK (id = 1),
    dados JSONB NOT NULL,
    publicado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def so_primeiro_nome(texto: str | None, nome: str) -> str | None:
    """A IA às vezes escreve o nome completo ("Ana Maria Souza"): no arquivo fica só "Ana"."""
    partes = nome.split()
    if not texto or len(partes) < 2:
        return texto
    sobrenomes = "|".join(re.escape(p) for p in partes[1:])
    return re.sub(rf"\b{re.escape(partes[0])}(?:\s+(?:{sobrenomes}))+\b", partes[0], texto, flags=re.IGNORECASE)


def coletar() -> tuple[dict[str, dict], dict]:
    """Lê o banco local (DB_NAME do ambiente): resultados por token + agregados do /geral."""
    from backend.services.participant_service import listar_participantes
    from backend.services.public_service import buscar_resultado_publico, calcular_painel_publico

    with database.get_connection() as connection:
        tokens = [
            (str(linha[0]), linha[1]) for linha in connection.execute(
                """
                SELECT token_publico, nome FROM participantes
                WHERE cancelada_em IS NULL AND token_publico IS NOT NULL
                ORDER BY id;
                """
            ).fetchall()
        ]
    resultados = {}
    for token, nome in tokens:
        dados = buscar_resultado_publico(token)
        if not dados:
            continue
        if dados.get("analise"):
            dados["analise"] = {campo: so_primeiro_nome(texto, nome) for campo, texto in dados["analise"].items()}
        resultados[token] = dados

    participantes = listar_participantes()
    ultima = max((p["criado_em"] for p in participantes if p.get("criado_em")), default=None)
    painel = calcular_painel_publico(participantes, agora=ultima)
    return resultados, painel


def publicar(destino: str, resultados: dict[str, dict], painel: dict) -> dict:
    """Espelha no destino, numa transação só: ou publica tudo, ou nada muda."""
    with psycopg.connect(destino) as connection:
        connection.execute(ESTRUTURA)
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO resultados_publicos (token_publico, dados, publicado_em)
                VALUES (%s, %s, NOW())
                ON CONFLICT (token_publico) DO UPDATE
                SET dados = EXCLUDED.dados, publicado_em = EXCLUDED.publicado_em
                WHERE resultados_publicos.dados IS DISTINCT FROM EXCLUDED.dados;
                """,
                [(token, Jsonb(dados)) for token, dados in resultados.items()],
            )
        removidos = connection.execute(
            "DELETE FROM resultados_publicos WHERE NOT (token_publico::text = ANY(%s));",
            (list(resultados),),
        ).rowcount
        connection.execute(
            """
            INSERT INTO painel_publico (id, dados, publicado_em) VALUES (1, %s, NOW())
            ON CONFLICT (id) DO UPDATE SET dados = EXCLUDED.dados, publicado_em = EXCLUDED.publicado_em;
            """,
            (Jsonb(painel),),
        )
        total = connection.execute("SELECT COUNT(*) FROM resultados_publicos;").fetchone()[0]
    return {"publicados": total, "removidos": removidos}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--banco", default=BANCO_EVENTO, help=f"banco local de origem (padrão: {BANCO_EVENTO})")
    parser.add_argument("--publicar", action="store_true", help="publica de verdade (sem isso, só mostra)")
    parser.add_argument("--loop", type=int, metavar="SEGUNDOS", help="republica para sempre a cada SEGUNDOS")
    args = parser.parse_args()

    os.environ["DB_NAME"] = args.banco
    destino = (os.getenv("ARQUIVO_DATABASE_URL") or "").strip()
    if args.publicar and not destino:
        sys.exit("Defina ARQUIVO_DATABASE_URL no .env (connection string do Neon).")
    if not args.loop:
        rodada(args, destino, sair_se_vazio=True)
        return
    # Durante a feira: uma falha (internet, Neon dormindo) não derruba o laço.
    while True:
        try:
            rodada(args, destino, sair_se_vazio=False)
        except Exception as erro:  # noqa: BLE001
            print(f"[{time.strftime('%H:%M:%S')}] Falhou: {erro}. Tento de novo em {args.loop} s.")
        time.sleep(args.loop)


def rodada(args, destino: str, sair_se_vazio: bool) -> None:
    resultados, painel = coletar()
    prontos = sum(1 for dados in resultados.values() if dados["status"] == "pronto")
    print(f"[{time.strftime('%H:%M:%S')}] Banco {args.banco}: {len(resultados)} link(s) "
          f"({prontos} com análise pronta), {painel['participantes']} pessoa(s) no /geral.")
    if not args.publicar:
        print("Nada foi enviado. Rode com --publicar para mandar para a nuvem.")
        return
    if not resultados:
        # Banco errado ou vazio: não apaga o que já está publicado.
        if sair_se_vazio:
            sys.exit("Nenhuma avaliação: confira o --banco. Nada foi enviado.")
        print("Nenhuma avaliação ainda; nada enviado.")
        return
    feito = publicar(destino, resultados, painel)
    print(f"Publicado: {feito['publicados']} link(s) no ar, {feito['removidos']} removido(s).")


if __name__ == "__main__":
    main()
