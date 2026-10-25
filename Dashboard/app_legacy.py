"""
MOVE 30 | MARK II - Dashboard em Streamlit
Consumo de dados exclusivamente via FastAPI (sem conexão direta ao banco).
"""
import html
import json
import os
import urllib.error
import urllib.request
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ───────────────────────── Identidade visual ─────────────────────────
BG = "#06172B"
CARD = "#0A2544"
AZUL = "#0787F9"
TURQUESA = "#00C2A8"
ROXO = "#7C5CFF"
AMARELO = "#F5B942"
VERMELHO = "#FF5C70"
TEXTO = "#F4F8FF"
TEXTO2 = "#9ABFE8"
BORDA = "#16406B"

NUMERICAS = [
    "idade", "peso", "altura", "fas", "fc_pre_teste", "fc_pos_teste",
    "imc", "resistencia", "indice_move", "velocidade_teste"
]
ORDEM_TESTES = ["light", "moderate", "hard"]
COR_TESTE = {"light": TURQUESA, "moderate": AZUL, "hard": ROXO}

st.set_page_config(page_title="MOVE 30 | MARK II", page_icon="🏃", layout="wide")

st.markdown(
    f"""
<style>
.stApp {{ background: {BG}; color: {TEXTO}; }}
header[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 1.2rem; padding-bottom: 1rem; max-width: 1600px; }}
h1, h2, h3, h4, p, label, span, div {{ color: {TEXTO}; }}
div[data-testid="stVerticalBlockBorderWrapper"] {{
    background: {CARD}; border: 1px solid {BORDA}; border-radius: 14px;
    box-shadow: 0 4px 14px rgba(0,0,0,.25);
}}
.brand {{ font-size: 2rem; font-weight: 800; letter-spacing: .5px; }}
.brand b {{ color: {AZUL}; }}
.brand small {{ color: {TEXTO2}; font-weight: 600; font-size: 1rem; margin-left: 10px;
               border-left: 1px solid {BORDA}; padding-left: 10px; }}
.subtitulo {{ color: {TEXTO2}; margin-top: -6px; }}
.kpi {{ background: {CARD}; border: 1px solid {BORDA}; border-radius: 14px;
        padding: 16px 18px; box-shadow: 0 4px 14px rgba(0,0,0,.25); height: 130px; }}
.kpi .nome {{ color: {TEXTO2}; font-size: .9rem; font-weight: 600; }}
.kpi .valor {{ font-size: 2.3rem; font-weight: 800; line-height: 1.2; }}
.kpi .valor span {{ font-size: 1rem; color: {TEXTO2}; font-weight: 600; margin-left: 4px; }}
.kpi .barra {{ height: 4px; border-radius: 4px; margin-top: 8px; }}
.titulo-painel {{ font-size: 1.05rem; font-weight: 700; margin-bottom: 2px; }}
.legenda {{ color: {TEXTO2}; font-size: .8rem; margin-bottom: 6px; }}
table.tb {{ width: 100%; border-collapse: collapse; font-size: .88rem; }}
table.tb th {{ color: {TEXTO2}; font-weight: 600; text-align: left; padding: 8px 6px;
              border-bottom: 1px solid {BORDA}; }}
table.tb td {{ padding: 9px 6px; border-bottom: 1px solid rgba(22,64,107,.5); }}
.ia-box {{ border: 1px dashed {AZUL}; border-radius: 12px; padding: 22px; color: {TEXTO2};
           background: rgba(7,135,249,.06); min-height: 120px; }}
.ia-item {{ border: 1px solid {BORDA}; border-radius: 10px; padding: 10px 12px; margin-bottom: 8px;
            background: rgba(7,135,249,.06); font-size: .88rem; }}
.ia-item b {{ color: {AZUL}; display: block; margin-bottom: 2px; font-size: .8rem; }}
.ia-tag {{ float: right; border: 1px solid {AZUL}; color: {AZUL}; border-radius: 20px;
           padding: 1px 10px; font-size: .72rem; }}
div[data-baseweb="select"] > div {{ background: {CARD}; border-color: {BORDA}; }}
</style>
""",
    unsafe_allow_html=True,
)

# ───────────────────────── Configuração e Leitura da API ─────────────────────────
def api_base():
    url = os.getenv("API_URL")
    if not url:
        try:
            url = st.secrets["API_URL"]
        except Exception:
            url = "http://127.0.0.1:8002"
    return str(url).rstrip("/")

@st.cache_data(ttl=10, show_spinner="Carregando participantes da API...")
def carregar_dados():
    """Busca os participantes reais via GET /participantes da FastAPI."""
    try:
        url = f"{api_base()}/participantes"
        with urllib.request.urlopen(url, timeout=10) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
            df = pd.DataFrame(dados.get("participantes", []))
            
            if not df.empty:
                for c in NUMERICAS:
                    if c in df.columns:
                        df[c] = pd.to_numeric(df[c], errors="coerce")
            return df, None
    except urllib.error.URLError:
        return None, f"Sem resposta da API em {api_base()}. O FastAPI está rodando na porta 8002?"
    except Exception as e:
        return None, f"Erro ao carregar dados da API: {e}"

# ───────────────────────── Helpers Visuais ─────────────────────────
def fmt(x, casas=1):
    if x is None or pd.isna(x):
        return "—"
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def layout_plotly(fig, altura=300):
    fig.update_layout(
        height=altura, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXTO2), legend=dict(orientation="h", y=-0.15, font=dict(color=TEXTO2)),
    )
    fig.update_xaxes(showgrid=False, linecolor=BORDA)
    fig.update_yaxes(gridcolor="rgba(154,191,232,.15)", zeroline=False)
    return fig

def mostrar_grafico(fig):
    try:
        st.plotly_chart(fig, width="stretch")
    except TypeError:
        st.plotly_chart(fig, use_container_width=True)

def tabela_html(df):
    cab = "".join(f"<th>{c}</th>" for c in df.columns)
    linhas = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in row) + "</tr>"
        for row in df.itertuples(index=False)
    )
    return f'<table class="tb"><thead><tr>{cab}</tr></thead><tbody>{linhas}</tbody></table>'

def kpi(nome, valor, unidade, cor):
    return (
        f'<div class="kpi"><div class="nome">{nome}</div>'
        f'<div class="valor">{valor}<span>{unidade}</span></div>'
        f'<div class="barra" style="background:{cor}"></div></div>'
    )

# ───────────────────────── Carga e Interface ─────────────────────────
st.markdown('<div class="brand"><b>MOVE 30</b><small>MARK II</small></div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo">Dashboard de análise de performance física</div>', unsafe_allow_html=True)

df_total, erro_api = carregar_dados()

if erro_api:
    st.error("Não foi possível carregar os participantes reais da API.")
    st.code(erro_api)
    st.info("Verifique se o FastAPI está em execução: uvicorn backend.main:app --host 127.0.0.1 --port 8002 --reload")
    st.stop()

if df_total is None or df_total.empty:
    st.info("Nenhum participante cadastrado no sistema até o momento.")
    st.stop()

# ───────────────────────── Filtros ─────────────────────────
c_f1, c_f2, c_total = st.columns([1.4, 1.6, 1])

with c_f1:
    existentes = set(df_total["tipo_teste"].dropna())
    tipos = [t for t in ORDEM_TESTES if t in existentes] + sorted(existentes - set(ORDEM_TESTES))
    tipos_sel = st.multiselect("Tipo de teste", tipos, default=tipos)

df = df_total[df_total["tipo_teste"].isin(tipos_sel)] if tipos_sel else df_total.iloc[0:0]

with c_f2:
    ordenados = df.sort_values("nome")
    rotulos = {int(r.id): f"{r.nome} (#{int(r.id)})" for r in ordenados.itertuples()}
    escolhido = st.selectbox(
        "Participante", [None] + list(rotulos), format_func=lambda v: "Todos" if v is None else rotulos[v]
    )

if escolhido is not None:
    df = df[df["id"] == escolhido]
individual = escolhido is not None

with c_total:
    st.markdown(kpi("Participantes", len(df), "", AZUL), unsafe_allow_html=True)

c_cap, c_btn = st.columns([6, 1])
c_cap.caption("Fonte de dados: FastAPI (http://127.0.0.1:8002)")
if c_btn.button("Atualizar"):
    st.cache_data.clear()
    st.rerun()

if df.empty:
    st.info("Nenhum participante para os filtros selecionados.")
    st.stop()

st.write("")

# ───────────────────────── Indicadores ─────────────────────────
prefixo = "" if individual else " (média)"
k1, k2, k3, k4, k5 = st.columns(5)
k1.markdown(kpi(f"IMC{prefixo}", fmt(df["imc"].mean()), "kg/m²", TURQUESA), unsafe_allow_html=True)
k2.markdown(kpi(f"FC pré-teste{prefixo}", fmt(df["fc_pre_teste"].mean(), 0), "bpm", AZUL), unsafe_allow_html=True)
k3.markdown(kpi(f"FC pós-teste{prefixo}", fmt(df["fc_pos_teste"].mean(), 0), "bpm", VERMELHO), unsafe_allow_html=True)
k4.markdown(kpi(f"Resistência{prefixo}", fmt(df["resistencia"].mean()), "/ 100", ROXO), unsafe_allow_html=True)
k5.markdown(kpi(f"Índice MOVE{prefixo}", fmt(df["indice_move"].mean()), "/ 100", AMARELO), unsafe_allow_html=True)

st.write("")

# ───────────────────────── Gráficos + IA ─────────────────────────
col_a, col_b, col_c = st.columns([1.1, 1.1, 1.2])

with col_a:
    with st.container(border=True):
        if individual:
            st.markdown('<div class="titulo-painel">Resistência e Índice MOVE</div>', unsafe_allow_html=True)
            st.markdown('<div class="legenda">Escala de 0 a 100</div>', unsafe_allow_html=True)
            res, idx = df["resistencia"].iloc[0], df["indice_move"].iloc[0]
            fig = go.Figure(
                go.Bar(
                    x=[0 if pd.isna(res) else res, 0 if pd.isna(idx) else idx],
                    y=["Resistência", "Índice MOVE"], orientation="h",
                    marker_color=[ROXO, AMARELO], text=[fmt(res), fmt(idx)],
                    textposition="outside", textfont=dict(color=TEXTO), width=0.5,
                )
            )
            fig.update_xaxes(range=[0, 115], showgrid=True, gridcolor="rgba(154,191,232,.15)")
            fig.update_yaxes(autorange="reversed")
        else:
            st.markdown('<div class="titulo-painel">Participantes por tipo de teste</div>', unsafe_allow_html=True)
            st.markdown('<div class="legenda">Distribuição dos cadastros</div>', unsafe_allow_html=True)
            cont = df["tipo_teste"].value_counts()
            ordem = [t for t in ORDEM_TESTES if t in cont.index] + [t for t in cont.index if t not in ORDEM_TESTES]
            fig = go.Figure(
                go.Pie(
                    labels=ordem, values=[int(cont[t]) for t in ordem], hole=0.68, sort=False,
                    marker=dict(colors=[COR_TESTE.get(t, TEXTO2) for t in ordem], line=dict(color=CARD, width=2)),
                    textinfo="value", textfont=dict(color=TEXTO),
                )
            )
            fig.add_annotation(
                text=f"<b>{len(df)}</b><br><span style='font-size:12px'>total</span>",
                showarrow=False, font=dict(size=24, color=TEXTO),
            )
            fig.update_layout(legend=dict(orientation="v", x=1.0, y=0.5))
        mostrar_grafico(layout_plotly(fig, 300))

with col_b:
    with st.container(border=True):
        st.markdown('<div class="titulo-painel">Frequência Cardíaca</div>', unsafe_allow_html=True)
        st.markdown('<div class="legenda">Comparação entre pré e pós-teste</div>', unsafe_allow_html=True)
        pre, pos = df["fc_pre_teste"].mean(), df["fc_pos_teste"].mean()
        fig = go.Figure(
            go.Bar(
                x=["Pré-teste", "Pós-teste"], y=[pre, pos], marker_color=[AZUL, TURQUESA],
                text=[fmt(pre, 0), fmt(pos, 0)], textposition="outside",
                textfont=dict(color=TEXTO), width=0.45,
            )
        )
        fig.update_yaxes(title="bpm", range=[0, max(pre, pos) * 1.25])
        mostrar_grafico(layout_plotly(fig, 300))

# ───────────────────────── Bloco Direto da IA (Lê do Banco) ─────────────────────────
with col_c:
    with st.container(border=True):
        st.markdown(
            '<div class="titulo-painel">ANÁLISE DA INTELIGÊNCIA ARTIFICIAL <span class="ia-tag">IA</span></div>',
            unsafe_allow_html=True,
        )
        
        if not individual:
            st.markdown(
                '<div class="ia-box">Selecione um participante no filtro para ver a análise da IA.</div>',
                unsafe_allow_html=True,
            )
        else:
            p = df.iloc[0]
            
            # Pega as colunas salvas no banco de dados
            perfil = p.get("perfil")
            destaque = p.get("destaque")
            oportunidade = p.get("oportunidade")
            mensagem = p.get("mensagem")
            
            if perfil and str(perfil).strip():
                st.markdown(
                    f'<div class="ia-item"><b>PERFIL</b>{html.escape(str(perfil))}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="ia-item"><b>DESTAQUE</b>{html.escape(str(destaque))}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="ia-item"><b>OPORTUNIDADE</b>{html.escape(str(oportunidade))}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="ia-item"><b>MENSAGEM</b>{html.escape(str(mensagem))}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="ia-box">Aguardando geração da análise da IA...</div>',
                    unsafe_allow_html=True,
                )

st.write("")

# ───────────────────────── Linha Final ─────────────────────────
var = df["fc_pos_teste"] - df["fc_pre_teste"]

if individual:
    col_d, col_f = st.columns([1.6, 1])
    with col_d:
        with st.container(border=True):
            st.markdown('<div class="titulo-painel">Dados do participante</div>', unsafe_allow_html=True)
            p = df.iloc[0]
            dados = pd.DataFrame(
                [
                    ("Nome", p["nome"]), ("Idade", f"{fmt(p['idade'], 0)} anos"),
                    ("Peso", f"{fmt(p['peso'])} kg"), ("Altura", f"{fmt(p['altura'], 2)} m"),
                    ("FAS", fmt(p["fas"], 0)), ("Tipo de teste", p["tipo_teste"]),
                    ("Velocidade do teste", f"{fmt(p['velocidade_teste'])} km/h"),
                ],
                columns=["Campo", "Valor"],
            )
            st.markdown(tabela_html(dados), unsafe_allow_html=True)
else:
    col_d, col_e, col_f = st.columns([1.6, 1, 1.1])
    with col_d:
        with st.container(border=True):
            st.markdown('<div class="titulo-painel">Desempenho por Tipo de Teste</div>', unsafe_allow_html=True)
            g = (
                df.groupby("tipo_teste")
                .agg(Participantes=("id", "count"), IMC=("imc", "mean"), FAS=("fas", "mean"),
                     FC_pre=("fc_pre_teste", "mean"), FC_pos=("fc_pos_teste", "mean"),
                     Indice=("indice_move", "mean"))
                .reset_index()
            )
            g = g.sort_values("tipo_teste", key=lambda s: s.map({o: i for i, o in enumerate(ORDEM_TESTES)}).fillna(99))
            for col, casas in [("IMC", 1), ("FAS", 1), ("FC_pre", 0), ("FC_pos", 0), ("Indice", 1)]:
                g[col] = g[col].map(lambda v, c=casas: fmt(v, c))
            g.columns = ["Tipo de teste", "Participantes", "IMC", "FAS", "FC pré", "FC pós", "Índice MOVE"]
            st.markdown(tabela_html(g), unsafe_allow_html=True)
    with col_e:
        with st.container(border=True):
            st.markdown('<div class="titulo-painel">Top 5 — Índice MOVE</div>', unsafe_allow_html=True)
            top = df.dropna(subset=["indice_move"]).nlargest(5, "indice_move")[["nome", "indice_move"]].reset_index(drop=True)
            top.insert(0, "#", range(1, len(top) + 1))
            top["indice_move"] = top["indice_move"].map(lambda v: fmt(v))
            top.columns = ["#", "Participante", "Índice MOVE"]
            st.markdown(tabela_html(top), unsafe_allow_html=True)

with col_f:
    with st.container(border=True):
        st.markdown('<div class="titulo-painel">Variação da FC (pós − pré)</div>', unsafe_allow_html=True)
        st.markdown('<div class="legenda">Diferença em bpm</div>', unsafe_allow_html=True)
        if individual:
            fig = go.Figure(go.Bar(x=["Variação"], y=[var.iloc[0]], marker_color=ROXO, width=0.3,
                                   text=[fmt(var.iloc[0], 0)], textposition="outside"))
        else:
            fig = go.Figure(go.Histogram(x=var.dropna(), marker_color=ROXO, nbinsx=10))
            fig.update_xaxes(title="bpm")
            fig.update_yaxes(title="participantes")
        mostrar_grafico(layout_plotly(fig, 240))

st.caption("MOVE 30 | MARK II • Conectado à API FastAPI")