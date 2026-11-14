import importlib

import pandas as pd
import requests
import streamlit as st

from shared import api_base, aviso_backend_offline, etapa_atual, format_number, load_api_json, render_etapas
import visuals

importlib.reload(visuals)
from visuals import PALETTE, section_heading


@st.fragment(run_every="2s")
def render_dashboard():
    st.title("Estação de medição", icon=":material/sensors:")
    st.caption("Ao vivo. Confira quem deve estar na estação: a balança grava a leitura na pessoa mostrada aqui.")

    status = load_api_json("/estacao/status")
    if status is None:
        aviso_backend_offline()
        st.stop()

    estacoes = status.get("estacoes", [])
    fila = status.get("fila", [])
    ultima = status.get("ultima_concluida")

    if not estacoes:
        st.info("Nenhuma pessoa na estação agora.")
    for estacao in estacoes:
        with st.container(border=True):
            section_heading(f"{estacao['nome']} (#{estacao['id']})", "users", PALETTE["post"], 2)
            atividade = estacao.get("atividade")
            st.markdown(f"**Atividade:** {atividade}" if atividade else "**Atividade:** teste simples (sem esforço)")
            render_etapas(etapa_atual(estacao["peso"], estacao["altura"], estacao["fc_pre_teste"], estacao["fc_pos_teste"], False))
            st.caption(
                f"Altura: {format_number(estacao['altura'], 2, ' m')} · "
                f"Peso: {format_number(estacao['peso'], 1, ' kg')} · "
                f"FC repouso: {format_number(estacao['fc_pre_teste'], 0, ' bpm')} · "
                f"FC depois: {format_number(estacao['fc_pos_teste'], 0, ' bpm')} · "
                f"Dispositivo: {estacao['device_id']}"
            )
            confirmar_key = f"confirmar_cancelar_{estacao['device_id']}"
            if st.session_state.get(confirmar_key):
                st.warning(f"Cancelar {estacao['nome']} e liberar a estação pro próximo da fila?")
                col_sim, col_nao = st.columns(2)
                if col_sim.button("Sim, cancelar", key=f"sim_{estacao['device_id']}", type="primary"):
                    try:
                        requests.post(f"{api_base()}/estacao/{estacao['device_id']}/cancelar", timeout=5)
                        st.session_state[confirmar_key] = False
                        st.rerun()
                    except requests.RequestException:
                        st.error("Não consegui cancelar; tente de novo.")
                if col_nao.button("Não", key=f"nao_{estacao['device_id']}"):
                    st.session_state[confirmar_key] = False
                    st.rerun()
            else:
                if st.button("Cancelar / pular esta pessoa", key=f"cancelar_{estacao['device_id']}"):
                    st.session_state[confirmar_key] = True
                    st.rerun()

    if ultima:
        with st.container(border=True):
            section_heading(f"Última concluída: {ultima['nome']} (#{ultima['id']})", "checklist", PALETTE["post"], 2)
            render_etapas(6 if ultima["analise_pronta"] else 5)

    with st.container(border=True):
        section_heading(f"Fila de espera: {len(fila)}", "clock", PALETTE["pre"], 2)
        if fila:
            frame = pd.DataFrame(
                [{"Número": f"#{item['id']}", "Nome": item["nome"], "Atividade": item.get("atividade") or "Simples"} for item in fila]
            )
            st.dataframe(frame, hide_index=True, width="stretch", alt="Pessoas aguardando a estação de medição")
        else:
            st.caption("Ninguém aguardando.")


render_dashboard()
