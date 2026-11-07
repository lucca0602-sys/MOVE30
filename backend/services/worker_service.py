import logging
import os
import threading

from backend.services.analysis_service import retry_pending_analyses
from backend.services.backup_service import criar_backup

logger = logging.getLogger(__name__)


def _repetir(parar: threading.Event, tarefa, nome: str) -> None:
    intervalo = float(os.getenv("WORKER_INTERVALO_S", "60"))
    while True:
        try:
            tarefa()
        except Exception:
            logger.exception("Falha na tarefa periódica: %s", nome)
        if parar.wait(intervalo):
            return


def iniciar_workers() -> threading.Event:
    # Separate threads: a slow AI must not delay the backups.
    parar = threading.Event()
    for tarefa, nome in ((criar_backup, "backup"), (retry_pending_analyses, "analise-ia")):
        threading.Thread(target=_repetir, args=(parar, tarefa, nome), name=nome, daemon=True).start()
    return parar
