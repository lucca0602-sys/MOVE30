import os
import time
import requests


CAMPOS_IA = {"perfil", "destaque", "oportunidade", "mensagem"}


def enviar_para_n8n(payload: dict) -> dict:
    url = os.getenv("N8N_WEBHOOK_URL")
    if not url:
        raise RuntimeError("N8N_WEBHOOK_URL não definida no .env")

    ultimo_erro = None
    for tentativa in range(2):  # 1 retry
        try:
            r = requests.post(url, json=payload, timeout=90)
            r.raise_for_status()

            if not r.text.strip():
                raise ValueError("n8n respondeu 200 com corpo vazio")

            dados = r.json()
            if isinstance(dados, list):  # n8n às vezes devolve lista
                dados = dados[0]

            faltando = CAMPOS_IA - set(dados.keys())
            if faltando:
                raise ValueError(f"campos ausentes na resposta da IA: {faltando}")

            return {campo: dados[campo] for campo in CAMPOS_IA}

        except (requests.RequestException, ValueError) as e:
            ultimo_erro = e
            print(f"[n8n] tentativa {tentativa + 1} falhou: {e}")
            time.sleep(2)

    raise RuntimeError(f"IA indisponível: {ultimo_erro}")