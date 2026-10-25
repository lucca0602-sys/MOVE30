from __future__ import annotations

import io
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


@st.cache_data(ttl=8, max_entries=2, show_spinner=False)
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


def make_qr_png(url: str) -> bytes:
    import qrcode

    image = qrcode.make(url)
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def numeric_or_missing(row: pd.Series, field: str, decimals: int = 1, suffix: str = "") -> str:
    return format_number(number_or_none(row, field), decimals, suffix)
