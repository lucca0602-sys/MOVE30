import importlib

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from shared import aviso_backend_offline, load_api_json, load_participants, participant_labels
import visuals

importlib.reload(visuals)
from visuals import PALETTE, PLOT_CONFIG, metric_card, section_heading, status_pill, style_cartesian_axes, style_plotly


# Above this, charts show only the most recent people to stay readable.
LIMITE_GRAFICO = 40


def _ultimas_avaliacoes(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or not {"nome", "id", "pessoa_id"}.issubset(frame.columns):
        return pd.DataFrame()
    latest = frame.dropna(subset=["nome", "id", "pessoa_id"]).copy()
    latest = latest[latest["nome"].astype(str).str.strip() != ""]
    return latest.sort_values("id", kind="stable").drop_duplicates("pessoa_id", keep="last")


def _media(valor: object, casas: int, sufixo: str) -> str:
    if valor is None:
        return "—"
    return f"{float(valor):.{casas}f}".replace(".", ",") + sufixo


def _indice_move_coletivo(participants: pd.DataFrame) -> tuple[float | None, int, float | None, float | None]:
    required = {"fas", "resistencia"}
    if participants.empty or not required.issubset(participants.columns):
        return None, 0, None, None
    fas = pd.to_numeric(participants["fas"], errors="coerce")
    resistance = pd.to_numeric(participants["resistencia"], errors="coerce")
    valid = participants.loc[
        fas.between(1, 7) & resistance.between(0, 100)
    ].copy()
    if valid.empty:
        return None, 0, None, None
    fas = pd.to_numeric(valid["fas"], errors="coerce")
    resistance = pd.to_numeric(valid["resistencia"], errors="coerce")
    fas_mean_normalized = float((((fas - 1) / 6) * 100).mean())
    resistance_mean = float(resistance.mean())
    score = (fas_mean_normalized + resistance_mean) / 2
    return round(score, 1), len(valid), round(fas_mean_normalized, 1), round(resistance_mean, 1)


@st.fragment(run_every="5s")
def render_dashboard():
    st.title("Dashboard geral", icon=":material/desktop_windows:")
    st.caption("Visão completa das avaliações e dos indicadores do grupo.")

    if st.button("Atualizar agora", icon=":material/refresh:"):
        load_participants.clear()
        st.rerun()

    frame, error = load_participants()
    if error:
        aviso_backend_offline(error)
        st.stop()
    if frame is None or frame.empty:
        st.info("Ainda não há avaliações cadastradas.")
        st.stop()
    if not {"nome", "id"}.issubset(frame.columns):
        st.error("A API precisa retornar os campos id e nome para consolidar o grupo.")
        st.stop()

    show_names = st.checkbox("Exibir nomes completos (somente com autorização dos participantes)", value=True)
    latest = _ultimas_avaliacoes(frame)
    if latest.empty:
        st.info("Ainda não há participantes com nome e identificador válidos.")
        st.stop()

    now = pd.Timestamp.now().strftime("%H:%M:%S")
    status_pill(f"Atualização em tempo real · {now}", "signal", PALETTE["post"])
    st.caption(f"Atualização automática a cada 5 segundos · {len(latest)} participante(s)")

    # The API averages only complete and plausible assessments.
    indicadores = load_api_json("/indicadores/coletivos")
    medias = (indicadores or {}).get("medias") or {}
    if not medias:
        st.warning("Não foi possível obter as médias do grupo.")
    move_index, move_count, fas_normalized_mean, resistance_mean = _indice_move_coletivo(latest)

    with st.container(horizontal=True):
        metric_card("Participantes", len(latest), "users", PALETTE["pre"])
        metric_card("Peso (média)", _media(medias.get("peso"), 1, " kg"), "scale", PALETTE["purple"])
        metric_card("Altura (média)", _media(medias.get("altura"), 2, " m"), "ruler", PALETTE["pre"])
    with st.container(horizontal=True):
        metric_card("FC pré (média)", _media(medias.get("fc_pre_teste"), 0, " bpm"), "heart", PALETTE["pre"])
        metric_card("FC pós (média)", _media(medias.get("fc_pos_teste"), 0, " bpm"), "heart", PALETTE["post"])
        metric_card("Variação da FC (média)", _media(medias.get("variacao_fc"), 0, " bpm"), "activity", PALETTE["alert"])
        metric_card("FC Score (média)", _media(medias.get("fc_score"), 1, " bpm"), "star", PALETTE["score"])
    if medias:
        st.caption(
            f"Médias de {medias['participantes_validos']} pessoa(s) com avaliação completa e válida. "
            f"Fora do cálculo: {medias['avaliacoes_incompletas']} avaliação(ões) incompleta(s) "
            f"e {medias['avaliacoes_invalidas']} com leitura fora da faixa aceita."
        )
    if len(latest) > LIMITE_GRAFICO:
        st.caption(f"Os gráficos mostram as {LIMITE_GRAFICO} pessoas mais recentes; as médias consideram todas.")

    with st.container(border=True):
        section_heading("Frequência cardíaca dos participantes", "activity", PALETTE["pre"], 2)
        chart_frame = latest.sort_values("id").tail(LIMITE_GRAFICO).copy()
        if show_names:
            chart_labels = participant_labels(chart_frame)
        else:
            chart_labels = [f"Participante {index:02d}" for index in range(1, len(chart_frame) + 1)]
        pre_values = pd.to_numeric(chart_frame.get("fc_pre_teste"), errors="coerce")
        post_values = pd.to_numeric(chart_frame.get("fc_pos_teste"), errors="coerce")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=pre_values, y=chart_labels, orientation="h", name="FC Pré",
            marker=dict(color=PALETTE["pre"], line=dict(color="#76DCFF", width=.5)),
            text=pre_values, texttemplate="%{x:.0f}", textposition="outside", cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>FC Pré: %{x:.0f} bpm<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            x=post_values, y=chart_labels, orientation="h", name="FC Pós",
            marker=dict(color=PALETTE["post"], line=dict(color="#72F2CC", width=.5)),
            text=post_values, texttemplate="%{x:.0f}", textposition="outside", cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>FC Pós: %{x:.0f} bpm<extra></extra>",
        ))
        max_hr = pd.concat([pre_values, post_values]).dropna().max()
        max_hr = float(max_hr) if pd.notna(max_hr) and max_hr > 0 else 100.0
        chart_height = min(900, max(390, 126 + 48 * len(chart_labels)))
        fig.update_layout(
            barmode="group", bargap=.28, bargroupgap=.12,
            legend=dict(orientation="h", y=1.12, x=0, xanchor="left", font=dict(size=12)),
            xaxis=dict(title="Batimentos por minuto (bpm)", range=[0, 200], dtick=50),
            yaxis=dict(title=None, autorange="reversed", automargin=True),
        )
        style_plotly(fig, height=chart_height, margins=dict(l=24, r=46, t=44, b=60))
        style_cartesian_axes(fig, horizontal_bars=True)
        st.plotly_chart(fig, width="stretch", theme=None, config=PLOT_CONFIG, alt="Barras horizontais comparando FC pré e FC pós para cada participante")

    index_col, types_col = st.columns(2, gap="medium")
    with index_col:
        with st.container(border=True):
            section_heading("Índice MOVE do grupo", "gauge", PALETTE["pre"], 2)
            metric_card("Índice MOVE coletivo", "—" if move_index is None else f"{move_index:.1f} / 100", "gauge", PALETTE["pre"])
            st.caption("Média do FAS normalizado e da resistência, usando a avaliação mais recente de cada participante.")
            if move_count:
                st.caption(f"Base: {move_count} participante(s) com os dois indicadores válidos.")
            if move_index is not None and fas_normalized_mean is not None and resistance_mean is not None:
                categories = ["Índice MOVE", "FAS normalizado", "Resistência"]
                values = [move_index, fas_normalized_mean, resistance_mean]
                component_fig = go.Figure(go.Bar(
                    x=values, y=categories, orientation="h",
                    marker=dict(color=["#79DFFF", PALETTE["pre"], PALETTE["post"]], line=dict(color="#173A59", width=1)),
                    text=[f"{value:.1f}" if value > 0 else "" for value in values], textposition="outside", cliponaxis=False,
                    hovertemplate="<b>%{y}</b><br>Média: %{x:.1f} / 100<extra></extra>",
                ))
                component_fig.update_layout(
                    xaxis=dict(title="Escala 0–100", range=[0, 100], tickmode="array", tickvals=[0, 25, 50, 75, 100]),
                    yaxis=dict(title=None, autorange="reversed", automargin=True), showlegend=False,
                    annotations=[dict(x=3, y=category, xref="x", yref="y", text=f"{value:.1f}", showarrow=False, xanchor="left", font=dict(size=11, color="#D9E9FA")) for category, value in zip(categories, values) if value == 0],
                )
                style_plotly(component_fig, height=275, margins=dict(l=128, r=44, t=16, b=52))
                style_cartesian_axes(component_fig, horizontal_bars=True)
                st.plotly_chart(component_fig, width="stretch", theme=None, config=PLOT_CONFIG, alt="Índice MOVE e médias de seus componentes em uma escala de zero a cem")
    with types_col:
        with st.container(border=True):
            section_heading("Tipos de avaliação", "donut", PALETTE["post"], 2)
            if "tipo_avaliacao" in latest.columns:
                modalidade = latest["modalidade"] if "modalidade" in latest.columns else pd.Series(None, index=latest.index)
                tipo_teste = latest["tipo_teste"] if "tipo_teste" in latest.columns else pd.Series(None, index=latest.index)
                kinds = [
                    "simples" if tipo == "simples" else (mod if isinstance(mod, str) and mod else ("corrida" if isinstance(nivel, str) and nivel else "nao_informado"))
                    for tipo, mod, nivel in zip(latest["tipo_avaliacao"], modalidade, tipo_teste)
                ]
                test_types = pd.Series(kinds).value_counts()
                labels = {"simples": "Simples", "bike": "Bike", "agachamento": "Agachamento", "abdominal": "Abdominal",
                          "flexao": "Flexão", "corrida": "Esteira (antigo)", "nao_informado": "Não informado"}
                pie_labels = [labels.get(key, key) for key in test_types.index]
                pie_colors = [PALETTE["post"], PALETTE["pre"], PALETTE["purple"], PALETTE["score"], PALETTE["alert"], "#ff8a5b", "#a9c0d9"]
                fig = go.Figure(go.Pie(
                    labels=pie_labels, values=test_types.to_list(), hole=.68, sort=False,
                    marker=dict(colors=pie_colors[:len(pie_labels)], line=dict(color="#061426", width=2)),
                    textinfo="percent", textposition="inside", insidetextorientation="horizontal",
                    textfont=dict(color="#F4F8FF", size=12),
                    hovertemplate="<b>%{label}</b><br>Avaliações: %{value}<br>Participação: %{percent}<extra></extra>",
                ))
                fig.update_layout(
                    showlegend=True,
                    legend=dict(orientation="h", y=-.08, x=.5, xanchor="center", font=dict(size=11)),
                    uniformtext_minsize=10, uniformtext_mode="hide",
                    annotations=[dict(text=f"{int(test_types.sum())}<br><span style='font-size:11px'>avaliações</span>", x=.5, y=.5, showarrow=False, font=dict(size=21, color="#F4F8FF"))],
                )
                style_plotly(fig, height=335, margins=dict(l=18, r=18, t=22, b=54))
                st.plotly_chart(fig, width="stretch", theme=None, config=PLOT_CONFIG, alt="Distribuição percentual dos tipos de avaliação")
            else:
                st.info("A API não retornou o tipo de teste.")

    with st.container(border=True):
        section_heading("Resultados recentes", "bolt", PALETTE["score"], 2)
        recent = latest.sort_values("id", ascending=False).head(7).copy()
        if show_names:
            displayed_names = participant_labels(recent)
        else:
            position_by_id = {
                int(row.id): index for index, row in enumerate(latest.sort_values("id").itertuples(), start=1)
            }
            displayed_names = [f"Participante {position_by_id.get(int(value), 0):02d}" for value in recent["id"]]
        results = pd.DataFrame({
            "Participante": displayed_names,
            "FC Pré (bpm)": pd.to_numeric(recent.get("fc_pre_teste"), errors="coerce").to_list(),
            "FC Pós (bpm)": pd.to_numeric(recent.get("fc_pos_teste"), errors="coerce").to_list(),
            "FC Score (bpm)": pd.to_numeric(recent.get("fc_score"), errors="coerce").to_list() if "fc_score" in recent.columns else None,
            "Avaliação": [f"#{int(value)}" for value in recent["id"]],
        })
        st.dataframe(results, hide_index=True, width="stretch", alt="Avaliações mais recentes do grupo")

    with st.container(border=True):
        section_heading("Indicadores das avaliações mais recentes", "activity", PALETTE["pre"], 2)
        compare = latest.sort_values("id").tail(LIMITE_GRAFICO).copy()
        compare_labels = (
            participant_labels(compare) if show_names
            else [f"Participante {index:02d}" for index in range(1, len(compare) + 1)]
        )
        fig = go.Figure()
        for field, name, color in (
            ("fc_pre_teste", "FC Pré", PALETTE["pre"]),
            ("fc_pos_teste", "FC Pós", PALETTE["post"]),
            ("fc_score", "FC Score", PALETTE["score"]),
        ):
            if field in compare.columns:
                values = pd.to_numeric(compare[field], errors="coerce")
                fig.add_trace(go.Bar(
                    x=compare_labels, y=values, name=name,
                    marker=dict(color=color, line=dict(color="#C5EFFF", width=.6)),
                    text=values, texttemplate="%{y:.0f}", textposition="inside",
                    hovertemplate="<b>%{x}</b><br>" + name + ": %{y:.0f} bpm<extra></extra>",
                ))
        fig.update_layout(
            barmode="group", bargap=.28, bargroupgap=.12,
            legend=dict(orientation="h", y=1.12, x=0, xanchor="left"),
            xaxis=dict(title="Participante", tickangle=-25, automargin=True, type="category"),
            yaxis=dict(title="Batimentos por minuto (bpm)", range=[0, 200], dtick=50),
        )
        style_plotly(fig, height=390, margins=dict(l=66, r=24, t=46, b=84))
        style_cartesian_axes(fig)
        st.plotly_chart(fig, width="stretch", theme=None, config=PLOT_CONFIG, alt="Comparação dos indicadores nas avaliações mais recentes, sem conectar participantes distintos")


render_dashboard()
