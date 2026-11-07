"""Restaura um backup: insere só o que falta e não altera nem apaga nada.

Uso, na raiz do projeto:
    .venv\\Scripts\\python.exe -m scripts.restaurar_backup backups\\move30_XXXX.json
"""
import sys
from pathlib import Path

from backend.services.backup_service import restaurar_backup


if __name__ == "__main__":
    if len(sys.argv) != 2 or not Path(sys.argv[1]).is_file():
        raise SystemExit(__doc__)
    print("Linhas inseridas:", restaurar_backup(Path(sys.argv[1])))
