from __future__ import annotations

import io
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False)

NUMERIC_COLUMNS = (
    "id",
    "pessoa_id",
    "idade",
    "peso",
    "altura",
    "fas",
    "fc_pre_teste",
    "fc_pos_teste",
    "imc",
    "resistencia",
    "fc_score",
    "velocidade_teste",
)


def api_base() -> str:
    return os.getenv("API_URL", "http://127.0.0.1:8002").rstrip("/")


ETAPAS = ("Cadastro", "Peso", "Altura", "FC de repouso", "Esforço e FC depois", "Análise da IA", "Concluído")
INSTRUCOES = {
    1: "Suba na balança e fique parado até esta etapa mudar.",
    2: "Desça da balança e fique em pé, reto e parado, embaixo do sensor de altura.",
    3: "Coloque o dedo no sensor e mantenha parado por cerca de 15 s.",
    4: "Tire o dedo e faça a atividade (bike pelo tempo do nível ou as 20 repetições). Ao terminar, coloque o dedo de novo: a leitura começa no mínimo 60 s depois da FC de repouso.",
    5: "Medições salvas. A IA está gerando a análise; costuma levar cerca de 1 minuto.",
    6: "Avaliação completa. O resultado está no dashboard pessoal.",
}


def etapa_atual(peso: object, altura: object, fc_pre: object, fc_pos: object, analise_pronta: bool) -> int:
    """Index in ETAPAS of what the person is doing now, derived from the saved data."""
    if peso is None or pd.isna(peso):
        return 1
    if altura is None or pd.isna(altura):
        return 2
    if fc_pre is None or pd.isna(fc_pre):
        return 3
    if fc_pos is None or pd.isna(fc_pos):
        return 4
    return 6 if analise_pronta else 5


def render_etapas(atual: int) -> None:
    """Show the assessment steps, highlighting the current one."""
    itens = []
    for indice, nome in enumerate(ETAPAS):
        if indice < atual or atual == len(ETAPAS) - 1:
            cor, fundo, marca = "#13D6A0", "rgba(19,214,160,.12)", "✓"
        elif indice == atual:
            cor, fundo, marca = "#22B8FF", "rgba(34,184,255,.20)", "▶"
        else:
            cor, fundo, marca = "#A9C0D9", "transparent", "○"
        destaque = 700 if indice == atual else 500
        itens.append(
            f'<div style="flex:1 1 120px;padding:10px 12px;border:1px solid {cor};border-radius:10px;'
            f'background:{fundo};color:{cor};font-weight:{destaque};font-size:.92rem;">{marca} {nome}</div>'
        )
    st.html(f'<div style="display:flex;flex-wrap:wrap;gap:8px;">{"".join(itens)}</div>')
    instrucao = INSTRUCOES.get(atual)
    if instrucao:
        st.markdown(f"**Agora:** {instrucao}")


@st.cache_data(ttl=2, max_entries=2, show_spinner=False)
def load_participants() -> tuple[pd.DataFrame | None, str | None]:
    """Read the current participant/evaluation records from FastAPI."""
    request = Request(f"{api_base()}/participantes", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=8) as response:
            payload = response.read().decode("utf-8")
        decoded = __import__("json").loads(payload)
        rows = decoded.get("participantes", []) if isinstance(decoded, dict) else None
        if not isinstance(rows, list):
            return None, "A API respondeu em um formato diferente do esperado."
        frame = pd.DataFrame(rows)
        for column in NUMERIC_COLUMNS:
            if column in frame.columns:
                frame[column] = pd.to_numeric(frame[column], errors="coerce")
        return frame, None
    except HTTPError as exc:
        return None, f"A API respondeu com erro HTTP {exc.code}."
    except (URLError, TimeoutError, OSError):
        return None, f"Não foi possível acessar a API em {api_base()}."
    except (ValueError, UnicodeDecodeError):
        return None, "A API não retornou JSON válido."


def aviso_backend_offline(detalhe: str | None = None) -> None:
    """Same warning on every page; the page keeps refreshing and recovers by itself."""
    st.warning(
        "**Backend offline.** O painel continua aberto e volta sozinho quando a API "
        f"({api_base()}) responder de novo. Confira se o `subir_evento.ps1` está rodando.",
        icon=":material/cloud_off:",
    )
    if detalhe:
        st.caption(detalhe)


@st.cache_data(ttl=1, max_entries=4, show_spinner=False)
def load_api_json(path: str) -> dict | None:
    """Read a JSON object from FastAPI; None when it is unavailable."""
    request = Request(f"{api_base()}{path}", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=8) as response:
            decoded = json.loads(response.read().decode("utf-8"))
        return decoded if isinstance(decoded, dict) else None
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        return None


def participant_labels(frame: pd.DataFrame) -> list[str]:
    """Names for display; people with the same name are told apart by assessment number."""
    names = frame["nome"].astype(str).str.strip()
    repeated = names.str.casefold().duplicated(keep=False)
    return [
        f"{name} (#{int(identifier)})" if is_repeated else name
        for name, identifier, is_repeated in zip(names, frame["id"], repeated)
    ]


def format_number(value: object, decimals: int = 1, suffix: str = "") -> str:
    if value is None or pd.isna(value):
        return "Não informado"
    return f"{float(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".") + suffix


def number_or_none(row: pd.Series, field: str) -> float | None:
    if field not in row.index:
        return None
    value = pd.to_numeric(row[field], errors="coerce")
    return None if pd.isna(value) else float(value)


def mean_or_none(frame: pd.DataFrame, field: str) -> float | None:
    if field not in frame.columns:
        return None
    values = pd.to_numeric(frame[field], errors="coerce").dropna()
    return None if values.empty else float(values.mean())


def dashboard_url(participant_id: str | None = None) -> str:
    """Build a shareable personal-dashboard URL without embedding a name."""
    configured = os.getenv("DASHBOARD_PUBLIC_URL", "").strip()
    if configured:
        parts = urlsplit(configured)
        base_path = parts.path.rstrip("/")
        if base_path.endswith("/pessoal"):
            page_path = base_path
        else:
            page_path = f"{base_path}/pessoal"
        base = f"{parts.scheme}://{parts.netloc}{page_path}"
    else:
        current = urlsplit(st.context.url)
        current_path = current.path.rstrip("/")
        if current_path.endswith("/pessoal"):
            page_path = current_path
        elif current_path.endswith("/coletivo"):
            page_path = current_path[: -len("/coletivo")] + "/pessoal"
        else:
            page_path = f"{current_path}/pessoal"
        base = f"{current.scheme}://{current.netloc}{page_path}"
    if participant_id is None:
        return base
    return f"{base}?{urlencode({'participante': str(participant_id)})}"


def link_pessoal(token: str) -> str:
    """Public /dash/<token> link, the same one the totem shows in the QR Code."""
    base = os.getenv("FRONT_PUBLIC_URL", "https://ia-frontend-seven.vercel.app").strip().rstrip("/")
    return f"{base}/dash/{token}"


def buscar_token_publico(participant_id: int) -> str | None:
    """Reads the public token straight from the database (staff-only, never through the API)."""
    import psycopg

    with psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    ) as connection:
        row = connection.execute(
            "SELECT token_publico FROM participantes WHERE id = %s AND cancelada_em IS NULL;",
            (int(participant_id),),
        ).fetchone()
    return str(row[0]) if row and row[0] else None


def make_qr_png(url: str) -> bytes:
    import qrcode

    image = qrcode.make(url)
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def numeric_or_missing(row: pd.Series, field: str, decimals: int = 1, suffix: str = "") -> str:
    return format_number(number_or_none(row, field), decimals, suffix)
