# MOVE 30

Estação de avaliação física da feira de ciências. Um cadastro só no totem, com a escolha do tipo de teste:

- **Com corrida**: a estação (ESP32-S3) mede peso → FC de repouso → corrida → FC depois.
- **Simples**: a estação mede peso → 1 FC de repouso, e termina (sem corrida).

Nos dois casos: ao terminar o cadastro, o totem mostra a **senha da estação** e o **QR Code** do resultado pessoal (`/dash/<token>`). Quando as medições acabam, a IA analisa e o resultado aparece no totem e no celular da pessoa.
A altura vem do cadastro. Se ela passar a ser medida pelo hardware (o firmware já tem `sensor_altura`), a fila da estação precisa deixar de exigir altura no cadastro.

## Endereços em produção

| O quê | URL |
|---|---|
| Totem (cadastro + senha + QR) | https://ia-frontend-seven.vercel.app |
| Painel geral (TV) | https://ia-frontend-seven.vercel.app/geral |
| Resultado pessoal (QR) | https://ia-frontend-seven.vercel.app/dash/TOKEN |
| Back-end público (Funnel) | https://notebooklucca.tail5c65a2.ts.net |

Projeto Vercel: `ia-frontend` (Root Directory `frontend`, preset Other, variável `MOVE30_API_URL`).
A URL da Vercel já está em `CORS_ORIGINS` no `.env` do PC.

## Arquitetura

```
            INTERNET                                  │            PC DO EVENTO (rede local)
                                                      │
 Celular / TV ──► Vercel (front estático)             │
                  /         cadastro + senha + QR     │
                  /dash/TOKEN  resultado de 1 pessoa  │
                  /geral    painel só com médias      │
                     │                                │
                     │ fetch https://PC.tailXXXX.ts.net/public/...
                     ▼                                │
              Tailscale Funnel ───────────────────────┼──► App público  127.0.0.1:8003  (backend.public_app)
              (só a porta 8003)                       │        │  só rotas /public/*
                                                      │        ▼
                                                      │    PostgreSQL :5432 ◄── API interna :8002 (backend.main)
                                                      │        ▲                  ▲   ▲
                                                      │        │                  │   └── ESP32 (Wi-Fi local)
                                                      │    n8n :5678 ──► Ollama :11434 (llama3.2)
                                                      │                           └── Streamlit :8501 (equipe/TV local)
```

**O que fica exposto na internet:** só o app público (porta 8003), com 4 rotas:

| Rota | O que faz |
|---|---|
| `GET /public/health` | teste de vida |
| `POST /public/cadastro` | cadastro do totem (com corrida ou simples); devolve `token` (link do QR) e `numero` (senha da estação) |
| `GET /public/resultado/{token}` | resultado de UMA pessoa (primeiro nome, medidas, análise). Sem e-mail nem ID |
| `GET /public/coletivo` | médias e contagens do grupo (escondidas com menos de 3 pessoas) |

**Nunca expostos:** PostgreSQL, Ollama, n8n, API interna (`/participantes`, hardware, estação) e Streamlit.
O token do QR é um UUID aleatório: não dá pra chutar o link de outra pessoa (o ID sequencial não aparece em lugar nenhum público).

| Peça | Onde roda | Papel |
|---|---|---|
| `frontend/index.html`, `dash.html`, `geral.html` | Vercel | cadastro do totem + QR, resultado pessoal, painel geral |
| `backend.public_app` (8003) | PC, só 127.0.0.1 | API pública, atrás do Funnel |
| `backend.main` (8002) | PC, rede local | API interna: ESP32, Streamlit, workers de backup e de retry da IA |
| Streamlit (8501) | PC, rede local | ferramenta da equipe: estação, dash com nomes, reprocessar IA |
| n8n + Ollama | PC | análise da IA (prompt em [docs/prompt-ia-n8n.md](docs/prompt-ia-n8n.md)) |

## Variáveis de ambiente

### `.env` (PC) — modelo em `.env.example`

| Variável | Exemplo | Para quê |
|---|---|---|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | `localhost`, `5432`… | PostgreSQL |
| `N8N_WEBHOOK_URL` | `http://localhost:5678/webhook/...` | webhook da IA |
| `ESP32_API_KEY` | | chave do hardware |
| `CORS_ORIGINS` | `http://localhost:5500,https://move30.vercel.app` | quem pode chamar as APIs (sem barra no fim) |
| `CORS_ORIGIN_REGEX` | `^https://move30(-[a-z0-9-]+)?\.vercel\.app$` | opcional: previews da Vercel |
| `IA_TIMEOUT_S` | `180` | tempo máximo de uma chamada à IA |
| `IA_INTERVALO_S` | `600` | espera antes de tentar a IA de novo |
| `ARQUIVO_DATABASE_URL` | `postgresql://...neon.tech/neondb?sslmode=require` | Neon do arquivo pós-feira (usuário dono; só o `publicar_resultados` usa) |

### Vercel

| Variável | Valor |
|---|---|
| `MOVE30_API_URL` | URL do Funnel, ex.: `https://meu-pc.tail1234.ts.net` (sem barra no fim) |
| `ARQUIVO_DATABASE_URL` | connection string do Neon com o usuário **só-leitura** (ver "Depois da feira") |

O build (`frontend/build-config.mjs`) grava essa URL em `js/config.js`. **Mudou a variável → faça Redeploy.**

## Configuração única (antes do evento)

### 1. Banco
Aplique em ordem as migrations de `backend/migrations/` que faltam (a `006` já foi aplicada no banco real em 07/11).

### 2. Tailscale Funnel (URL fixa, grátis, sem domínio)
1. Instale: https://tailscale.com/download/windows e faça login (Google/GitHub servem).
2. No painel https://login.tailscale.com/admin/dns ative **MagicDNS** e **HTTPS Certificates**.
3. Em https://login.tailscale.com/admin/acls habilite o Funnel para o seu PC (o próprio `tailscale funnel` mostra um link para isso na primeira vez).
4. Com o app público rodando: `.\scripts\funnel.ps1`. Ele mostra a URL `https://NOME-DO-PC.tailXXXX.ts.net`, **que não muda entre reinícios**.
5. Teste no celular com o Wi-Fi desligado (4G): `https://NOME-DO-PC.tailXXXX.ts.net/public/health` → `{"status":"ok"}`.

> O Funnel publica **só a porta 8003**. O script roda `tailscale funnel reset` antes, para não sobrar nenhuma publicação antiga.

### 3. Vercel
1. https://vercel.com → **Add New → Project** → importe o repositório `lucca0602-sys/IA` (branch `melhorias-final` ou `main` depois do merge).
2. **Root Directory:** `frontend`. Framework: **Other**. O resto vem do `frontend/vercel.json`.
3. **Environment Variables:** `MOVE30_API_URL` = URL do Funnel.
4. Deploy. Anote a URL `https://SEU-PROJETO.vercel.app` e coloque em `CORS_ORIGINS` no `.env` do PC. Reinicie as APIs.

## Dia do evento

**Banco limpo (sábado 14/11, 9h):** os testes ficam guardados no banco atual e o evento começa vazio, sem apagar nada.
```powershell
.\.venv\Scripts\python.exe -m scripts.preparar_evento --ativar   # troca DB_NAME para move30_evento (faz backup do .env)
.\.venv\Scripts\python.exe -m scripts.preparar_evento            # confere: banco em uso e quantas avaliações tem
```
O banco `move30_evento` já foi criado vazio em 07/11. Para voltar aos testes: `--voltar`. O `subir_evento.ps1` avisa em amarelo se ainda estiver no banco de testes.

**Ligar (nesta ordem):**
1. PostgreSQL (serviço do Windows). O Ollama abre sozinho com o Windows.
2. `.\scripts\subir_evento.ps1` abre o Docker e o n8n (`scriptsbrir_docker.ps1`), depois 3 janelas (API interna, app público, Streamlit) que religam sozinhas se caírem, e testa cada serviço.
3. `.\scripts\funnel.ps1`
4. Num celular no 4G: abra `https://SEU-PROJETO.vercel.app`, faça um teste com o nome "TESTE EQUIPE" e confira se o QR abre o resultado.

**Telas:**
- Totem (cadastro): `https://SEU-PROJETO.vercel.app`. No fim aparece a senha da estação e o QR do resultado.
- TV: `https://SEU-PROJETO.vercel.app/geral` (atualiza a cada 5 s) ou, sem internet, `http://IP-DO-PC:8501` (Streamlit, rede local).
- Equipe: Streamlit em `http://IP-DO-PC:8501` (estação, dados completos, reprocessar IA).
- O PC fica livre para o Serial Monitor do Arduino: nenhum desses serviços precisa da tela dele.

**Memória (PC com 8 GB):** Ollama (~2,5 GB) + Docker/n8n + Postgres + Streamlit + Arduino IDE é apertado. Feche navegador, VS Code e o resto. Se ficar lento, feche o Streamlit (o `/geral` da Vercel cobre a TV).

**A IA demora** (~1-2 min por pessoa na CPU). A tela mostra "Analisando..." e o QR já aparece antes; a pessoa pode ir embora e ver depois no link. Se a IA falhar, a API interna tenta de novo a cada 10 min (`IA_INTERVALO_S`).

**Desligar:** `.\scripts\funnel.ps1 -Desligar` e feche as janelas.

## Depois da feira — links no ar com o PC desligado

O `/dash/<token>` e o `/geral` tentam primeiro o backend ao vivo (Funnel). Se ele não responder,
leem o **arquivo** publicado na Vercel (`frontend/api/`, Vercel Functions) a partir de um Postgres
grátis no Neon. Os QRs não mudam. O arquivo só tem o que o link já mostrava (primeiro nome, idade,
medidas, análise da IA, data) e os agregados do `/geral`: nada de e-mail, nome completo ou ID, e
se a IA escreveu o nome completo no texto ele vira só o primeiro nome. Nenhum dado vai para o git.

**Uma vez só:**
1. https://neon.tech → crie um projeto (plano Free; não apaga projeto parado, só "dorme" e acorda em ~1 s).
2. Copie a connection string do usuário dono para `ARQUIVO_DATABASE_URL` no `.env` do PC.
3. No SQL Editor do Neon, crie um usuário só-leitura para a Vercel (rode **depois** da primeira publicação, que cria as tabelas):
   ```sql
   CREATE ROLE move30_leitura LOGIN PASSWORD 'troque-esta-senha';
   GRANT USAGE ON SCHEMA public TO move30_leitura;
   GRANT SELECT ON resultados_publicos, painel_publico TO move30_leitura;
   ```
4. Vercel → Settings → Environment Variables: `ARQUIVO_DATABASE_URL` = connection string com `move30_leitura` (a mesma do Neon trocando usuário e senha). Redeploy.

**Publicar (depois da feira, e de novo quando quiser atualizar):**
```powershell
.\.venv\Scripts\python.exe -m scripts.publicar_resultados             # só mostra quantos iria publicar
.\.venv\Scripts\python.exe -m scripts.publicar_resultados --publicar  # manda para o Neon
```
Lê do `move30_evento` (troque com `--banco`), publica só avaliações com análise pronta e pode rodar
quantas vezes quiser: atualiza por token e tira da nuvem o que foi cancelado. Publique só depois da
feira: com o arquivo publicado, um token que ele não tem vira "não encontrado" quando o Funnel falha.

**Conferir:** desligue as APIs e o Funnel, abra um `/dash/<token>` real e o `/geral` no 4G. O `/geral`
mostra "Resultado final do evento". Depois disso dá para tirar `MOVE30_API_URL` da Vercel.

## Plano B — internet caiu

O banco, a IA e as APIs são locais e continuam funcionando. Só o caminho Vercel/Funnel para.

1. Conecte o PC e os celulares/totem **no mesmo Wi-Fi local** (roteador próprio ou celular roteando; o ESP32 só pega 2,4 GHz).
2. Rode o front direto do PC, com as mesmas páginas e rotas:
   ```powershell
   .\.venv\Scripts\python.exe -m scripts.servir_front --rede
   ```
3. Descubra o IP do PC (`ipconfig` → IPv4, ex.: `192.168.0.10`) e use `http://192.168.0.10:8080` no totem/celulares. O QR gerado aponta para esse endereço e funciona na rede local.
4. TV: `http://192.168.0.10:8080/geral` ou o Streamlit em `:8501`.
5. Se o Windows perguntar, **permita** o Python na rede privada (firewall).
6. Plano C (sem rede nenhuma): o totem roda no próprio PC em `http://127.0.0.1:8080`, e a pessoa fotografa a tela com a análise.

Os resultados feitos no plano B ficam no mesmo banco. Quando a internet voltar, os links `/dash/TOKEN` da Vercel também abrem esses resultados.

## Fluxo da estação (hardware)

A estação atende uma pessoa por vez, na ordem do cadastro (com corrida e simples dividem a mesma fila). A página **Estação de medição** do Streamlit mostra quem deve estar na balança; a senha é o número que aparece no totem.

No teste **simples** a estação para depois do passo 2: o servidor responde `complete` e o firmware não pede corrida (ele só pede corrida quando a etapa é `heart_rate_post`). Nenhuma mudança na ESP32.

1. Peso: a pessoa sobe e fica parada por cerca de 1 s.
2. FC de repouso: dedo no sensor por cerca de 15 s.
3. Corrida: a pessoa tira o dedo e corre.
4. FC depois: dedo no sensor de novo, no mínimo 60 s depois da FC de repouso.

O botão de emergência cancela a pessoa atual sem apagar o que já foi medido. Para refazer a tara, envie `t` no Monitor Serial com a balança vazia. Firmware: `linha_medicao/linha_medicao/linha_medicao.ino` (confira `secrets.h` e `API_URL` em `config.h`; o IP do PC pode mudar).

## Proteção dos dados

- Cada leitura é gravada assim que chega, ligada ao ID do participante. O banco recusa sobrescrever medição/análise e recusa apagar participante (gatilhos `proteger_participante` e `proteger_token_publico`).
- Público vê só agregados (`/geral`, com mínimo de 3 pessoas) ou o resultado do próprio token. E-mail nunca sai do banco. Para a IA (local) vai só o primeiro nome.
- Se a IA falhar, as medidas continuam salvas e a análise é tentada de novo.
- A API interna grava em `backups/` um arquivo novo sempre que os dados mudam (pasta fora do Git, tem dados pessoais). Restaurar: `.\.venv\Scripts\python.exe -m scripts.restaurar_backup backups\arquivo.json`.

## Rodar localmente (desenvolvimento)

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8002
.\.venv\Scripts\python.exe -m uvicorn backend.public_app:app --host 127.0.0.1 --port 8003
.\.venv\Scripts\python.exe -m scripts.servir_front          # http://127.0.0.1:8080 (teste, /dash, /geral)
.\.venv\Scripts\python.exe -m streamlit run Dashboard\app.py
```

## Testes

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests
.\.venv\Scripts\python.exe -m scripts.testar_prompt        # prompt da IA com 5 perfis no Ollama local
```

Os testes criam e apagam um banco separado (`move30_test`) e usam uma IA simulada. Mais detalhes em [docs/hardware-api.md](docs/hardware-api.md) e [docs/registration-flow.md](docs/registration-flow.md).
