import json
import os
from datetime import datetime, timezone
from pathlib import Path

from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from backend.database import BASE_DIR, get_connection

TABELAS = {
    "participantes": "id",
    "hardware_measurement_batches": "received_at, device_id, message_id",
}


def pasta_backup() -> Path:
    return Path(os.getenv("BACKUP_DIR") or BASE_DIR / "backups")


def _exportar() -> bytes:
    dados = {}
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            for tabela, ordem in TABELAS.items():
                cursor.execute(f"SELECT * FROM {tabela} ORDER BY {ordem};")
                dados[tabela] = cursor.fetchall()
    return json.dumps(dados, ensure_ascii=False, indent=1, default=str).encode("utf-8")


def criar_backup() -> Path | None:
    """Write a new file only when the data changed. Old backups are never removed."""
    pasta = pasta_backup()
    pasta.mkdir(parents=True, exist_ok=True)
    conteudo = _exportar()

    existentes = sorted(pasta.glob("move30_*.json"))
    if existentes and existentes[-1].read_bytes() == conteudo:
        return None

    agora = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    destino = pasta / f"move30_{agora}.json"
    temporario = destino.with_suffix(".tmp")
    # The rename keeps a power loss from leaving a half-written backup.
    with open(temporario, "wb") as arquivo:
        arquivo.write(conteudo)
        arquivo.flush()
        os.fsync(arquivo.fileno())
    os.replace(temporario, destino)
    return destino


def restaurar_backup(arquivo: Path) -> dict:
    """Insert only the rows that are missing; existing rows are never changed."""
    dados = json.loads(Path(arquivo).read_text(encoding="utf-8"))
    inseridos = {}
    with get_connection() as connection:
        with connection.cursor() as cursor:
            for tabela in TABELAS:
                inseridos[tabela] = 0
                cursor.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s;",
                    (tabela,),
                )
                colunas_validas = {linha[0] for linha in cursor.fetchall()}
                for linha in dados.get(tabela, []):
                    colunas = [coluna for coluna in linha if coluna in colunas_validas]
                    valores = [
                        Jsonb(linha[coluna]) if coluna == "measurements" else linha[coluna]
                        for coluna in colunas
                    ]
                    cursor.execute(
                        sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT DO NOTHING;").format(
                            sql.Identifier(tabela),
                            sql.SQL(", ").join(map(sql.Identifier, colunas)),
                            sql.SQL(", ").join(sql.Placeholder() * len(colunas)),
                        ),
                        valores,
                    )
                    inseridos[tabela] += cursor.rowcount
            # New registrations must continue after the highest restored ID.
            cursor.execute(
                "SELECT setval(pg_get_serial_sequence('participantes', 'id'), GREATEST((SELECT MAX(id) FROM participantes), 1));"
            )
    return inseridos
