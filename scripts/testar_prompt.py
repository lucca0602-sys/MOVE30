"""Testa o prompt de docs/prompt-ia-n8n.md direto no Ollama local, com 5 perfis.

Usa o MESMO texto que vai no n8n e o MESMO payload que o back-end envia, então o resultado
aqui é o que o participante verá. Não toca no banco.

    .\\.venv\\Scripts\\python.exe -m scripts.testar_prompt
Saída: docs/prompt-ia-testes.md (respostas lado a lado) e tempo de cada chamada.
"""
import json
import re
import time
from pathlib import Path

import requests

from backend.models.participant import AnalysisResponse
from backend.services.coerencia_ia import ajustar_resposta, problemas_de_coerencia
from backend.services.analytics_service import calcular_imc
from backend.services.n8n_service import montar_payload_n8n

RAIZ = Path(__file__).resolve().parent.parent
PROMPT_MD = RAIZ / "docs" / "prompt-ia-n8n.md"
SAIDA = RAIZ / "docs" / "prompt-ia-testes.md"
OLLAMA = "http://127.0.0.1:11434/api/generate"
EXPRESSAO = re.compile(r"\{\{\s*\$json\.body\.indicadores\.(\w+)(?:\s*\?\?\s*'([^']*)')?\s*\}\}")

PERFIS = [
    ("Magro", "Júlia", 16, 45.0, 1.68, 74),
    ("Normal", "Rafael", 17, 66.0, 1.75, 70),
    ("Acima do peso", "Carla", 34, 84.0, 1.65, 82),
    ("Batimento alto", "Diego", 19, 70.0, 1.78, 108),
    ("Batimento baixo", "Marina", 22, 58.0, 1.66, 52),
]


def ler_prompt() -> str:
    texto = PROMPT_MD.read_text(encoding="utf-8")
    return texto.split("<!-- PROMPT:INICIO -->", 1)[1].split("<!-- PROMPT:FIM -->", 1)[0].strip()


def preencher(prompt: str, indicadores: dict) -> str:
    def trocar(m):
        valor = indicadores.get(m.group(1))
        if valor is None:
            return m.group(2) if m.group(2) is not None else ""
        return str(valor)

    return EXPRESSAO.sub(trocar, prompt)


def payload_do_perfil(i, nome, idade, peso, altura, fc):
    participante = {
        "id": i, "nome": f"{nome} Exemplo", "idade": idade, "peso": peso, "altura": altura,
        "fas": None, "fc_pre_teste": fc, "fc_pos_teste": None, "tipo_teste": None,
        "velocidade_teste": None, "imc": calcular_imc(peso, altura), "resistencia": None,
        "tipo_avaliacao": "simples",
    }
    return montar_payload_n8n(participante)


def chamar_ollama(prompt: str, indicadores: dict) -> tuple[dict, float]:
    # Igual ao back-end: até 3 tentativas, reprovando respostas incoerentes.
    inicio = time.monotonic()
    for tentativa in range(1, 4):
        try:
            dados, _ = _chamar_ollama(prompt)
            problemas = problemas_de_coerencia(dados, indicadores)
            if problemas:
                raise ValueError(f"incoerente: {problemas}")
            dados = ajustar_resposta(dados, indicadores)
            dados["_tentativas"] = tentativa
            return dados, time.monotonic() - inicio
        except Exception as erro:
            print(f"      tentativa {tentativa} reprovada: {str(erro)[:120]}", flush=True)
            if tentativa == 3:
                raise


def _chamar_ollama(prompt: str) -> tuple[dict, float]:
    inicio = time.monotonic()
    r = requests.post(OLLAMA, json={
        "model": "llama3.2", "prompt": prompt, "stream": False, "format": "json",
        "options": {"temperature": 0.8},
    }, timeout=600)
    r.raise_for_status()
    dados = json.loads(r.json()["response"])
    AnalysisResponse.model_validate(dados)  # mesmo contrato que o back-end exige
    if any(not str(dados.get(k) or "").strip() for k in ("perfil", "destaque", "oportunidade", "mensagem")):
        raise ValueError("campo vazio")
    return dados, time.monotonic() - inicio


def main():
    prompt = ler_prompt()
    resultados = []
    for i, (rotulo, nome, idade, peso, altura, fc) in enumerate(PERFIS, start=1):
        payload = payload_do_perfil(i, nome, idade, peso, altura, fc)
        print(f"[{i}/5] {rotulo}...", flush=True)
        try:
            resposta, segundos = chamar_ollama(preencher(prompt, payload["indicadores"]), payload["indicadores"])
        except Exception as erro:  # registra e segue para o próximo perfil
            resposta, segundos = {"erro": str(erro)}, 0.0
        print(f"      {segundos:.0f}s", flush=True)
        resultados.append((rotulo, nome, idade, peso, altura, fc, payload["indicadores"], resposta, segundos))

    linhas = ["# Teste do prompt — 5 perfis (llama3.2 local, temperature 0.8)", ""]
    linhas.append("| | " + " | ".join(f"**{r[0]}**" for r in resultados) + " |")
    linhas.append("|---|" + "---|" * len(resultados))
    linhas.append("| Dados | " + " | ".join(
        f"{r[1]}, {r[2]} anos, {r[3]:g} kg, {r[4]:g} m, IMC {r[6]['imc']:.1f}, FC {r[5]} bpm" for r in resultados) + " |")
    linhas.append("| Tempo | " + " | ".join(f"{r[8]:.0f} s ({r[7].get('_tentativas', '-')} tentativa(s))" for r in resultados) + " |")
    for campo in ("perfil", "destaque", "oportunidade", "mensagem"):
        celulas = [str(r[7].get(campo, r[7].get("erro", ""))).replace("\n", "<br>").replace("|", "/") for r in resultados]
        linhas.append(f"| **{campo}** | " + " | ".join(celulas) + " |")
    SAIDA.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"Salvo em {SAIDA}")


if __name__ == "__main__":
    main()
