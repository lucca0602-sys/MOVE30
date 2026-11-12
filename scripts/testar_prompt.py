"""Testa o prompt de docs/prompt-ia-n8n.md direto no Ollama local, com 5 perfis.

Usa o MESMO texto que vai no n8n e o MESMO payload que o back-end envia, então o resultado
aqui é o que o participante verá. Não toca no banco.

    .\\.venv\\Scripts\\python.exe -m scripts.testar_prompt
Saída: docs/prompt-ia-testes.md (respostas lado a lado) e tempo de cada chamada.
"""
import json
import subprocess
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
OLLAMA = "http://127.0.0.1:11434/api/chat"

PERFIS = [
    ("Magro", "Júlia", 16, 45.0, 1.68, 74),
    ("Normal", "Rafael", 17, 66.0, 1.75, 70),
    ("Acima do peso", "Carla", 34, 84.0, 1.65, 82),
    ("Batimento alto", "Diego", 19, 70.0, 1.78, 108),
    ("Batimento baixo", "Marina", 22, 58.0, 1.66, 52),
]
# Completas (com atividade): FC depois, modalidade e nível. O 1º é o caso real que a IA errou.
COMPLETAS = {
    "Sobrepeso + FC alta + bike": ("Caio", 16, 80.7, 1.75, 108, (139, "bike", "moderate")),
    "Sobrepeso + flexão": ("Paula", 40, 75.0, 1.62, 78, (112, "flexao", None)),
}
PERFIS += [(rotulo, *dados[:5]) for rotulo, dados in COMPLETAS.items()]


def ler_prompt() -> str:
    texto = PROMPT_MD.read_text(encoding="utf-8")
    return texto.split("<!-- PROMPT:INICIO -->", 1)[1].split("<!-- PROMPT:FIM -->", 1)[0].strip()


def corpo_do_n8n(expressao: str, payload: dict) -> dict:
    """Executa a expressão {{ ... }} do nó HTTP Request no Node, como o n8n faz: mesmo corpo JSON."""
    codigo = expressao.strip()
    assert codigo.startswith("{{") and codigo.endswith("}}"), "bloco do prompt deve ser {{ ... }}"
    js = "const $json = { body: " + json.dumps(payload) + " };\nprocess.stdout.write(" + codigo[2:-2] + ");"
    saida = subprocess.run(["node", "-e", js], capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(saida.stdout)


def payload_do_perfil(i, nome, idade, peso, altura, fc, rotulo=None):
    fc_pos, modalidade, tipo_teste = COMPLETAS[rotulo][5] if rotulo in COMPLETAS else (None, None, None)
    participante = {
        "id": i, "nome": f"{nome} Exemplo", "idade": idade, "peso": peso, "altura": altura,
        "fas": None, "fc_pre_teste": fc, "fc_pos_teste": fc_pos, "tipo_teste": tipo_teste,
        "modalidade": modalidade, "velocidade_teste": None, "imc": calcular_imc(peso, altura),
        "resistencia": None, "tipo_avaliacao": "completa" if fc_pos else "simples",
    }
    return montar_payload_n8n(participante)


def chamar_ollama(corpo: dict, indicadores: dict) -> tuple[dict, float]:
    # Igual ao back-end: até 3 tentativas, reprovando respostas incoerentes.
    inicio = time.monotonic()
    for tentativa in range(1, 4):
        try:
            dados, _ = _chamar_ollama(corpo)
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


def _chamar_ollama(corpo: dict) -> tuple[dict, float]:
    inicio = time.monotonic()
    r = requests.post(OLLAMA, json=corpo, timeout=600)
    r.raise_for_status()
    dados = json.loads(r.json()["message"]["content"])
    AnalysisResponse.model_validate(dados)  # mesmo contrato que o back-end exige
    if any(not str(dados.get(k) or "").strip() for k in ("perfil", "destaque", "oportunidade", "mensagem")):
        raise ValueError("campo vazio")
    return dados, time.monotonic() - inicio


def main():
    prompt = ler_prompt()
    resultados = []
    for i, (rotulo, nome, idade, peso, altura, fc) in enumerate(PERFIS, start=1):
        payload = payload_do_perfil(i, nome, idade, peso, altura, fc, rotulo)
        print(f"[{i}/{len(PERFIS)}] {rotulo}...", flush=True)
        try:
            resposta, segundos = chamar_ollama(corpo_do_n8n(prompt, payload), payload["indicadores"])
        except Exception as erro:  # registra e segue para o próximo perfil
            resposta, segundos = {"erro": str(erro)}, 0.0
        print(f"      {segundos:.0f}s", flush=True)
        resultados.append((rotulo, nome, idade, peso, altura, fc, payload["indicadores"], resposta, segundos))

    linhas = [f"# Teste do prompt — {len(PERFIS)} perfis (mesmo corpo do nó HTTP Request do n8n)", ""]
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
