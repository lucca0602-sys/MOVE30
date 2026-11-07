import os
import time
import requests

from backend.services.coerencia_ia import ajustar_resposta, problemas_de_coerencia


CAMPOS_IA = {"perfil", "destaque", "oportunidade", "mensagem"}


def enviar_para_n8n(payload: dict) -> dict:
    url = os.getenv("N8N_WEBHOOK_URL")
    if not url:
        raise RuntimeError("N8N_WEBHOOK_URL não definida no .env")

    # O Ollama roda na CPU: uma análise leva cerca de 1 minuto, e mais com a máquina ocupada.
    tempo_limite = float(os.getenv("IA_TIMEOUT_S", "180"))
    ultimo_erro = None
    # 3 tentativas por padrão: a checagem de coerência reprova algumas respostas do modelo pequeno.
    # Mantenha IA_INTERVALO_S maior que IA_TENTATIVAS x IA_TIMEOUT_S (padrão 3 x 180 < 600).
    for tentativa in range(int(os.getenv("IA_TENTATIVAS", "3"))):
        try:
            r = requests.post(url, json=payload, timeout=tempo_limite)
            r.raise_for_status()

            if not r.text.strip():
                raise ValueError("n8n respondeu 200 com corpo vazio")

            dados = r.json()
            if isinstance(dados, list) and dados:  # n8n às vezes devolve lista
                dados = dados[0]
            if not isinstance(dados, dict):
                raise ValueError("resposta da IA não é um objeto JSON")

            faltando = CAMPOS_IA - set(dados.keys())
            if faltando:
                raise ValueError(f"campos ausentes na resposta da IA: {faltando}")
            # O modelo pequeno às vezes devolve um campo vazio: conta como falha e tenta de novo.
            vazios = {campo for campo in CAMPOS_IA if not str(dados[campo] or "").strip()}
            if vazios:
                raise ValueError(f"campos vazios na resposta da IA: {vazios}")
            indicadores = payload.get("indicadores") or {}
            problemas = problemas_de_coerencia(dados, indicadores)
            if problemas:
                raise ValueError(f"resposta incoerente com os dados: {problemas}")

            return ajustar_resposta({campo: dados[campo] for campo in CAMPOS_IA}, indicadores)

        except (requests.RequestException, ValueError) as e:
            ultimo_erro = e
            print(f"[n8n] tentativa {tentativa + 1} falhou: {e}")
            time.sleep(2)

    raise RuntimeError(f"IA indisponível: {ultimo_erro}")