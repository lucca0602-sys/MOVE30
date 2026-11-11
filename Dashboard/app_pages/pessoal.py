import importlib
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from shared import (
    api_base,
    buscar_token_publico,
    etapa_atual,
    link_pessoal,
    load_participants,
    make_qr_png,
    number_or_none,
    numeric_or_missing,
    participant_labels,
    render_etapas,
)
import visuals

importlib.reload(visuals)
from visuals import PALETTE, PLOT_CONFIG, metric_card, section_heading, style_cartesian_axes, style_plotly


def _api_json(path: str, method: str, payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"{api_base()}{path}", data=body, method=method,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    try:
        # The AI service may take up to two attempts of 180 s each.
        with urlopen(request, timeout=380) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("detail", "")
        except (ValueError, UnicodeDecodeError):
            detail = ""
        raise RuntimeError(detail or f"A API respondeu com erro HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Não foi possível acessar a API em {api_base()}.") from exc


@st.fragment(run_every="3s")
def render_dashboard():
    st.title("Dashboard pessoal", icon=":material/person:")
    st.caption("Veja seus resultados, sua evolução e a análise da IA.")

    frame, error = load_participants()
    if error:
        st.error(error)
        st.info("Confira se o FastAPI está em execução e se API_URL aponta para ele.")
        st.stop()
    if frame is None or frame.empty:
        st.info("Ainda não há avaliações cadastradas.")
        st.stop()
    if "nome" not in frame.columns or "id" not in frame.columns:
        st.error("A API precisa retornar os campos id e nome para localizar avaliações.")
        st.stop()

    frame = frame.dropna(subset=["nome", "id"]).copy()
    frame["nome"] = frame["nome"].astype(str).str.strip()
    frame = frame[frame["nome"] != ""]
    if frame.empty:
        st.info("Ainda não há participantes com nome e identificador válidos.")
        st.stop()

    people = frame.sort_values("id", ascending=False).drop_duplicates("pessoa_id", keep="first")
    people = people.sort_values("nome", key=lambda values: values.str.casefold())
    record_ids = [str(int(value)) for value in people["id"]]
    label_by_id = dict(zip(record_ids, participant_labels(people)))

    query_value = str(st.query_params.get("participante", "")).strip()
    selected_from_url = query_value if query_value in record_ids else None
    if selected_from_url is None and query_value:
        normalized_query = " ".join(query_value.split()).casefold()
        matches = people[people["nome"].map(lambda value: " ".join(value.split()).casefold()) == normalized_query]
        # A name that matches several people is ambiguous: let the person choose.
        if len(matches) == 1:
            selected_from_url = str(int(matches.iloc[0]["id"]))
    if selected_from_url not in record_ids:
        selected_from_url = record_ids[0]

    selection_col, latest_col = st.columns([2.2, 1], vertical_alignment="bottom")
    with selection_col:
        with st.container(border=True):
            selected_id = st.selectbox(
                "Selecione seu nome",
                options=record_ids,
                index=record_ids.index(selected_from_url),
                format_func=lambda value: label_by_id.get(str(value), "Participante"),
                key="participant_selector",
            )
    selected_person = people.loc[people["id"] == int(selected_id)].iloc[0]
    selected_name = str(selected_person["nome"])
    matching = frame[frame["pessoa_id"] == selected_person["pessoa_id"]].copy().sort_values("id", ascending=False)
    latest = matching.iloc[0]
    with latest_col:
        metric_card("Última avaliação", f"#{int(latest['id'])}", "clock", PALETTE["pre"])

    st.subheader(f"Olá, {selected_name}")
    # A toggle (not a button) survives the 3 s fragment refresh while the person scans the code.
    if st.toggle("Mostrar QR de novo (perdeu o do totem)", key="mostrar_qr", help="Mostra o QR e o link pessoal da última avaliação."):
        try:
            token = buscar_token_publico(int(latest["id"]))
        except Exception:  # noqa: BLE001 - any DB failure only hides the QR
            token = None
        if token is None:
            st.warning("Não foi possível buscar o link desta avaliação no banco.")
        else:
            url = link_pessoal(token)
            with st.container(border=True, horizontal=True, vertical_alignment="center"):
                st.image(make_qr_png(url), width=260)
                with st.container():
                    st.markdown(f"**Senha na estação:** #{int(latest['id'])}")
                    st.caption("Peça para a pessoa apontar a câmera do celular ou copiar o link:")
                    st.code(url, language=None)
    has_analysis = any(pd.notna(latest.get(key)) and str(latest.get(key)).strip() for key in ("perfil", "destaque", "oportunidade", "mensagem"))
    render_etapas(etapa_atual(
        number_or_none(latest, "peso"),
        number_or_none(latest, "fc_pre_teste"),
        number_or_none(latest, "fc_pos_teste"),
        has_analysis,
    ))
    with st.container(horizontal=True):
        metric_card("FC pré-teste", numeric_or_missing(latest, "fc_pre_teste", 0, " bpm"), "heart", PALETTE["alert"])
        metric_card("FC pós-teste", numeric_or_missing(latest, "fc_pos_teste", 0, " bpm"), "heart", PALETTE["post"])
        metric_card("FC Score", numeric_or_missing(latest, "fc_score", 1, " bpm"), "star", PALETTE["score"])
        metric_card("Altura", numeric_or_missing(latest, "altura", 2, " m"), "ruler", PALETTE["pre"])
        metric_card("Peso", numeric_or_missing(latest, "peso", 1, " kg"), "scale", PALETTE["purple"])

    required_measurements = ("peso", "altura", "fc_pre_teste", "fc_pos_teste")
    missing_measurements = [field for field in required_measurements if number_or_none(latest, field) is None]
    if missing_measurements:
        st.info("A análise ficará disponível quando as medições de peso, altura e frequência cardíaca estiverem completas.")
    elif not has_analysis:
        if st.button("Gerar análise para esta avaliação", icon=":material/psychology_alt:", type="primary"):
            with st.spinner("Gerando análise para o dashboard..."):
                try:
                    _api_json(f"/participantes/{int(latest['id'])}/analisar", "POST")
                    load_participants.clear()
                    st.success("Análise atualizada.")
                    st.rerun()
                except RuntimeError as exc:
                    st.error(str(exc))

    ia_col, points_col = st.columns([2.1, 1], gap="small")
    with ia_col:
        with st.container(border=True):
            section_heading("Análise da IA", "brain", PALETTE["pre"], 2)
            profile = latest.get("perfil")
            message = latest.get("mensagem")
            if pd.notna(profile) and str(profile).strip():
                st.markdown("**Resumo da avaliação**")
                st.write(str(profile))
            if pd.notna(message) and str(message).strip():
                st.write(str(message))
            if not any(pd.notna(latest.get(key)) and str(latest.get(key)).strip() for key in ("perfil", "mensagem")):
                st.info("A análise da IA ainda não está disponível para esta avaliação.")
    with points_col:
        with st.container(border=True):
            section_heading("Pontos principais", "checklist", PALETTE["pre"], 2)
            for key, label in (("destaque", "Destaque"), ("oportunidade", "Recomendação")):
                value = latest.get(key)
                if pd.notna(value) and str(value).strip():
                    section_heading(label, "bulb" if key == "oportunidade" else "checklist", PALETTE["score"] if key == "oportunidade" else PALETTE["post"], 4)
                    st.write(str(value))
            if not any(pd.notna(latest.get(key)) and str(latest.get(key)).strip() for key in ("destaque", "oportunidade")):
                st.caption("Os pontos da análise aparecerão aqui quando estiverem disponíveis.")

    history_rows = []
    for row in matching.sort_values("id").itertuples(index=False):
        record = row._asdict()
        evaluation_id = record.get("id")
        history_rows.append({
            "Avaliação": f"#{int(evaluation_id)}" if pd.notna(evaluation_id) else "Sem ID",
            "FC pré (bpm)": record.get("fc_pre_teste"),
            "FC pós (bpm)": record.get("fc_pos_teste"),
            "FC Score (bpm)": record.get("fc_score"),
            "Resultado da IA": "Disponível" if any(
                pd.notna(record.get(field)) and str(record.get(field)).strip()
                for field in ("perfil", "destaque", "oportunidade", "mensagem")
            ) else "Pendente",
        })
    history = pd.DataFrame(history_rows)
    chart_history = history.copy()
    for column in ("FC pré (bpm)", "FC pós (bpm)", "FC Score (bpm)"):
        chart_history[column] = pd.to_numeric(chart_history[column], errors="coerce")

    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(border=True):
            section_heading("Evolução da frequência cardíaca", "activity", PALETTE["pre"], 2)
            fig = go.Figure()
            for column, label, color in (
                ("FC pré (bpm)", "FC pré", PALETTE["pre"]),
                ("FC pós (bpm)", "FC pós", PALETTE["post"]),
            ):
                values = chart_history[column]
                fig.add_trace(go.Bar(
                    x=chart_history["Avaliação"], y=values, name=label,
                    marker=dict(color=color, line=dict(color="#B4EFFF" if label == "FC pré" else "#8AF4D5", width=.5)),
                    text=values, texttemplate="%{y:.0f}", textposition="inside", insidetextanchor="end",
                    hovertemplate="<b>%{x}</b><br>" + label + ": %{y:.0f} bpm<extra></extra>",
                ))
            fig.update_layout(
                barmode="group", bargap=.3, bargroupgap=.12,
                legend=dict(orientation="h", y=1.12, x=0, xanchor="left", font=dict(size=11)),
                xaxis=dict(title="Avaliação", type="category", automargin=True),
                yaxis=dict(title="Batimentos por minuto (bpm)", range=[0, 200], dtick=50),
            )
            style_plotly(fig, height=360, margins=dict(l=66, r=20, t=46, b=58))
            style_cartesian_axes(fig)
            st.plotly_chart(fig, width="stretch", theme=None, config=PLOT_CONFIG, alt="Frequência cardíaca antes e depois por avaliação")
    with right:
        with st.container(border=True):
            section_heading("Evolução do FC Score", "star", PALETTE["score"], 2)
            score_values = chart_history["FC Score (bpm)"]
            fig = go.Figure(go.Scatter(
                x=chart_history["Avaliação"], y=score_values, mode="lines+markers+text",
                line=dict(color=PALETTE["score"], width=3),
                marker=dict(size=10, color=PALETTE["score"], line=dict(color="#FFF2BF", width=1.5)),
                text=score_values, texttemplate="%{y:.1f}", textposition="top center",
                name="FC Score", connectgaps=False,
                hovertemplate="<b>%{x}</b><br>FC Score: %{y:.1f} bpm<extra></extra>",
            ))
            fig.update_layout(
                showlegend=False,
                xaxis=dict(title="Avaliação", type="category", automargin=True),
                yaxis=dict(title="Batimentos por minuto (bpm)", range=[0, 200], dtick=50),
            )
            style_plotly(fig, height=360, margins=dict(l=66, r=24, t=44, b=58))
            style_cartesian_axes(fig)
            st.plotly_chart(fig, width="stretch", theme=None, config=PLOT_CONFIG, alt="Média dos batimentos cardíacos em cada avaliação")

    with st.container(border=True):
        section_heading("Histórico de avaliações", "calendar", PALETTE["pre"], 2)
        st.dataframe(history.iloc[::-1], hide_index=True, width="stretch", alt="Histórico de avaliações pessoais")


render_dashboard()
