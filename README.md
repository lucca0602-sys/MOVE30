# MOVE30

**Estação de avaliação física com IoT + IA local, construída para uma feira de ciências e usada ao vivo por mais de 100 pessoas em um dia.**

A pessoa se cadastra num totem, sobe numa estação com ESP32 que mede **peso, altura e frequência cardíaca**, faz um esforço curto (bike ou exercício) e recebe no celular, via QR Code, uma **análise escrita por um modelo de IA rodando localmente**. Uma TV mostra o painel do grupo em tempo real.

![Python](https://img.shields.io/badge/Python-FastAPI-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-banco-336791)
![ESP32](https://img.shields.io/badge/ESP32--S3-firmware%20C%2B%2B-E7352C)
![Ollama](https://img.shields.io/badge/IA-Ollama%20llama3.2%20%2B%20n8n-black)
![Vercel](https://img.shields.io/badge/front-Vercel-000)
![Tests](https://img.shields.io/badge/testes-100%20pytest-brightgreen)

**Demo (arquivo pós-feira):** [painel geral](https://ia-frontend-seven.vercel.app/geral) · [totem](https://ia-frontend-seven.vercel.app)

---

## O evento em números (14/11/2026)

| | |
|---|---|
| Cadastros no dia | **~114** |
| Avaliações completas (com esforço) | **85+** |
| Ritmo da estação | 8 a 12 pessoas/hora, uma por vez |
| Infra | 1 notebook de 8 GB sem GPU rodando banco, APIs, n8n e IA |

## Como funciona

```
 Celular / Totem / TV ──► Vercel (HTML/JS estático + Vercel Functions)
                               │  HTTPS
                               ▼
                       Tailscale Funnel  (expõe SÓ a porta 8003)
                               │
 ┌──────────────── PC do evento ─┼───────────────────────────────────────┐
 │                               ▼                                       │
 │   App público FastAPI :8003  (4 rotas /public/*)                      │
 │                               │                                       │
 │   ESP32-S3 ──Wi-Fi──► API interna FastAPI :8002 ──► PostgreSQL        │
 │   (HX711, VL53L0X,             │      ▲                               │
 │    MAX30102)                   ▼      │ workers: backup + retry da IA │
 │                     n8n ──► Ollama (llama3.2, CPU)                    │
 │                                                                       │
 │   Streamlit :8501 — ferramenta da equipe (fila da estação, dados)     │
 └───────────────────────────────────────────────────────────────────────┘
          │ depois da feira
          ▼
   Neon (Postgres na nuvem) ◄── Vercel Functions: links continuam no ar com o PC desligado
```

1. **Totem** (`frontend/`): cadastro (nome, idade, nível de atividade, tipo de teste). Devolve a senha da estação e um QR com link pessoal (`/dash/<token>`, UUID aleatório).
2. **Estação** (`linha_medicao/`): firmware C++ na ESP32-S3 consulta o back-end para saber a etapa da pessoa da vez e mede peso → altura → FC de repouso → esforço → FC depois.
3. **Back-end** (`backend/`): FastAPI + PostgreSQL. Grava cada leitura assim que chega, calcula IMC, FC Score e o Índice MOVE de forma determinística e manda os números para a IA.
4. **IA** (n8n + Ollama): gera a análise em linguagem simples. O back-end **valida a resposta** e reprova texto incoerente com os números (ex.: chamar IMC fora da faixa de "normal").
5. **Resultados**: celular da pessoa (`/dash`), painel da TV (`/geral`, só médias, mínimo 3 pessoas) e Streamlit interno.

## Destaques técnicos

- **Hardware de verdade, problemas de verdade.** Balança com célula de carga + HX711 (o "peso fantasma" era o HX711 devolvendo `-1` em leituras inválidas, que entrava na tara), sensor de distância VL53L0X a 2 m do chão para altura, MAX30102 para batimentos. Firmware modular (`sensor_peso`, `sensor_altura`, `sensor_fc`, `sessao`, `api_client`).
- **IA local e "sincera".** Sem API paga: Ollama em CPU. Os números são calculados no back-end (a IA não faz conta), e `backend/services/coerencia_ia.py` checa a resposta antes de mostrar; se reprovar, a IA é chamada de novo. Se a IA falhar, as medidas ficam salvas e um worker tenta de novo.
- **Superfície pública mínima.** Na internet só existe o app público com 4 rotas. Banco, IA, n8n e API interna nunca saem da rede local. Link pessoal por UUID (sem ID sequencial), e-mail nunca sai do banco, para a IA vai só o primeiro nome.
- **Dados protegidos no banco.** Gatilhos no PostgreSQL recusam sobrescrever medição/análise e apagar participante; backup automático a cada mudança, com script de restauração.
- **Pronto para o dia ruim.** Plano B sem internet (front servido pelo próprio PC na rede local), scripts que sobem e religam os serviços sozinhos, banco de evento separado do banco de testes.
- **Vive depois da feira.** `scripts/publicar_resultados.py` copia para o Neon só o que o link já mostrava; as Vercel Functions servem `/dash/<token>` e `/geral` com o PC desligado, sem mudar os QRs.
- **Testado.** Suíte pytest com banco descartável e IA simulada cobrindo fluxo do hardware, teste simples, proteção de dados, coerência da IA, dashboards e publicação.

## Stack

| Camada | Tecnologias |
|---|---|
| Hardware | ESP32-S3, HX711 + célula de carga, VL53L0X, MAX30102, Arduino/C++ |
| Back-end | Python, FastAPI, Pydantic, psycopg 3, PostgreSQL (migrations SQL + triggers) |
| IA | n8n (orquestração), Ollama `llama3.2` local |
| Front | HTML/CSS/JS puro, Chart.js, QR Code, Vercel (+ Functions em Node) |
| Interno | Streamlit, Plotly, pandas |
| Infra | Tailscale Funnel, Neon, Docker (n8n), PowerShell |
| Qualidade | pytest |

## Estrutura

```
backend/          FastAPI: API interna (main.py), app público (public_app.py), serviços e migrations
frontend/         Totem, /dash e /geral + Vercel Functions do arquivo pós-feira
linha_medicao/    Firmware da ESP32-S3 (+ sketch isolado para testar o sensor de altura)
Dashboard/        Streamlit da equipe (estação, dashboard pessoal, coletivo)
scripts/          Subir o evento, Funnel, preparar banco, publicar resultados, backup
tests/            Suíte pytest
docs/             Operação, API do hardware, fluxo de cadastro, prompt da IA, histórico
```

## Rodar localmente

Pré-requisitos: Python 3.11+, PostgreSQL, e (para a IA) n8n + Ollama com `llama3.2`.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
copy .env.example .env      # preencha banco, webhook do n8n e chave da ESP32
# aplique as migrations de backend/migrations/ em ordem

.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8002
.\.venv\Scripts\python.exe -m uvicorn backend.public_app:app --host 127.0.0.1 --port 8003
.\.venv\Scripts\python.exe -m scripts.servir_front          # http://127.0.0.1:8080
.\.venv\Scripts\python.exe -m streamlit run Dashboard\app.py

.\.venv\Scripts\python.exe -m pytest tests                  # cria e apaga o banco move30_test
```

Firmware: abra `linha_medicao/linha_medicao/linha_medicao.ino` na Arduino IDE, copie `secrets.example.h` para `secrets.h` (Wi-Fi e chave) e ajuste `API_URL` em `config.h`.

## Documentação

- [Operação (runbook)](docs/operacao.md): deploy, dia do evento, plano B, pós-feira
- [API do hardware](docs/hardware-api.md): contrato ESP32 ↔ back-end
- [Fluxo de cadastro](docs/registration-flow.md)
- [Prompt da IA](docs/prompt-ia-n8n.md) e [testes do prompt](docs/prompt-ia-testes.md)
- [Histórico de desenvolvimento](docs/historico-desenvolvimento.md): diário do projeto, de agosto à feira

## O que aprendemos (e o que faria diferente)

- **A leitura de FC não ficou confiável.** No dia, a FC de repouso média foi 97 bpm e em boa parte das avaliações a FC depois do esforço saiu *menor* que a de repouso: o detector de batimentos provavelmente conta batida a mais e a medição pós-esforço demora. Próximo passo: validar contra oxímetro e trocar o algoritmo de detecção de picos.
- **8 GB de RAM é o limite.** Ollama + Docker/n8n + Postgres + Streamlit no mesmo notebook exigiu fechar todo o resto. Evolução natural: back-end na nuvem (Render/Fly + Neon) e LLM por API.
- **Hardware pede ferramentas de diagnóstico.** Logs no Serial, comandos de tara pelo Monitor e um sketch isolado por sensor economizaram horas na véspera.
- **Separar teste de produção salvou o dia.** Banco do evento limpo, banco de testes preservado, backup automático.

## Autor

Desenvolvido por **Lucca** ([@lucca0602-sys](https://github.com/lucca0602-sys)), estudante do Técnico em Informática para Internet, como projeto da feira de ciências de 2026.

## Licença

[MIT](LICENSE)
