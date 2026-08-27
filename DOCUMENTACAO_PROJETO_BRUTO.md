# Documentacao Projeto SETOR DE IA

## Objetivo

Construir um agente local para projetos academicos usando FastAPI como API de entrada, n8n self-hosted como orquestrador e Ollama como modelo de inteligencia artificial local.

A documentacao sera ampliada conforme novas funcionalidades e integracoes forem implementadas.

## Historico de desenvolvimento e validacoes

Esta secao registra quando cada etapa foi realizada para que a evolucao do projeto possa ser compreendida por pessoas tecnicas e nao tecnicas. As datas distinguem a validacao da infraestrutura, o teste de conexao e a implementacao do MVP.

### 23/08/2026 - Infraestrutura e teste de conexao

Atividades realizadas:

- configuracao do Docker Desktop com WSL 2 no Windows;
- instalacao e inicializacao do n8n self-hosted em container Docker;
- criacao do volume persistente `n8n_data`;
- instalacao do Ollama local;
- download do modelo `llama3.2:latest`;
- criacao do workflow inicial com Webhook e Respond to Webhook;
- configuracao do FastAPI para enviar requisicoes ao webhook;
- teste de comunicacao entre FastAPI e n8n.

Validacao concluida:

```text
FastAPI -> Webhook n8n -> Respond to Webhook -> FastAPI
Resultado: answer = Teste recebido pelo n8n; status = success
```

Problemas encontrados e resolvidos:

- virtualizacao e componentes do WSL 2 precisaram ser habilitados;
- o n8n precisou ser executado pelo Docker Desktop;
- comandos `cd /d` foram substituidos por `Set-Location` no PowerShell;
- conflitos de porta foram tratados mantendo uma unica instancia do servidor;
- o caminho do modulo FastAPI foi corrigido com `--app-dir`.

Encerramento da etapa:

- infraestrutura local validada;
- comunicacao basica validada;
- pendencias: conectar o AI Agent ao Ollama e definir o contrato dos indicadores.

### 27/08/2026 - Primeiro MVP de indicadores

Atividades realizadas:

- definicao do modelo `ParticipantIndicators`;
- validacao de tipos e limites dos indicadores com Pydantic;
- criacao do prompt especializado em interpretacao de indicadores;
- implementacao do endpoint `POST /analyze`;
- substituicao da simulacao por uma chamada ao webhook do n8n;
- conexao do AI Agent ao Ollama com o modelo Llama 3.2;
- definicao da resposta estruturada com quatro campos;
- normalizacao de respostas JSON puras, em Markdown ou acompanhadas de texto;
- teste com indicadores validos e teste com valores extremos dentro dos limites.

Contrato validado:

```json
{
        "perfil": "...",
        "destaque": "...",
        "oportunidade": "...",
        "mensagem": "..."
}
```

Resultado da validacao:

- o FastAPI recebeu os indicadores;
- o prompt e os indicadores foram enviados ao n8n;
- o n8n encaminhou a solicitacao ao AI Agent;
- o Ollama gerou a resposta;
- o FastAPI validou o JSON recebido.

Pendencias definidas ao final da etapa:

- adicionar testes automatizados ao diretorio `tests`;
- revisar o contrato final de entrada e saida;
- definir regras de negocio e classificacao dos indicadores;
- revisar o workflow e documentar sua versao de producao.

## MVP implementado em 27/08/2026

O primeiro MVP recebe os indicadores de um participante, cria um prompt especializado, envia os dados ao n8n, solicita uma interpretacao ao AI Agent conectado ao Ollama/Llama 3.2 e devolve uma resposta estruturada em JSON.

Contrato da resposta:

```json
{
        "perfil": "...",
        "destaque": "...",
        "oportunidade": "...",
        "mensagem": "..."
}
```

## Arquitetura atual

```text
Cliente ou sistema web
        |
        v
FastAPI - http://127.0.0.1:8002
        |
        v
Webhook n8n - http://localhost:5678
        |
        v
AI Agent
        |
        v
Ollama - http://host.docker.internal:11434
        |
        v
llama3.2:latest
        |
        v
Respond to Webhook
        |
        v
FastAPI retorna o resultado
```

## Componentes

### FastAPI

Arquivo: `app.py`

Responsabilidades:

- receber indicadores na rota `POST /analyze`;
- validar tipos e limites dos indicadores;
- criar o prompt especializado;
- enviar prompt e indicadores em JSON ao webhook do n8n;
- receber o retorno do n8n;
- validar a resposta da IA;
- devolver uma resposta padronizada ao cliente.

Rotas:

```text
GET  http://127.0.0.1:8002/health
POST http://127.0.0.1:8002/analyze
```

### Docker Desktop

Executa o n8n em um container Linux no Windows, usando WSL 2.

Validacao realizada:

```text
Docker Client 29.7.2
Docker Server 29.7.2
Docker Desktop 4.87.0
Context: desktop-linux
```

### n8n self-hosted

O n8n esta instalado localmente no Docker e acessivel em:

```text
http://localhost:5678
```

Versao observada: `2.35.7`.

O container utiliza o volume persistente `n8n_data`.

### Ollama

O Ollama executa a IA no proprio computador e disponibiliza uma API local:

```text
http://localhost:11434
```

Modelo instalado:

```text
llama3.2:latest
```

Nao e usada chave de API para o Ollama local.

## Workflow n8n

```text
Webhook -> AI Agent -> Respond to Webhook
             ^
             |
     Ollama Chat Model
```

### Webhook

Configuracao:

```text
HTTP Method: POST
Path: agente
Respond: Using Respond to Webhook Node
Authentication: None
```

URL de teste:

```text
http://localhost:5678/webhook-test/agente
```

Para o teste, e necessario clicar em **Execute workflow** antes de enviar a requisicao. Para uso continuo, ativar o workflow e utilizar `/webhook/agente`.

### AI Agent

Recebe a mensagem e o contexto do Webhook e solicita uma resposta ao modelo conectado.

Prompt inicial:

```text
Voce e um assistente util e objetivo.

Prompt recebido pelo FastAPI:
{{$json.prompt}}

Indicadores recebidos pelo FastAPI:
{{JSON.stringify($json.indicadores)}}

Retorne somente um JSON valido, sem markdown, usando exatamente os campos
perfil, destaque, oportunidade e mensagem.
```

### Ollama Chat Model

Configuracao:

```text
Model: llama3.2:latest
Base URL: http://host.docker.internal:11434
```

O endereco `host.docker.internal` permite que o container n8n acesse o Ollama que roda no Windows. Dentro do container, `localhost` aponta para o proprio container.

### Respond to Webhook

Devolve a resposta do workflow ao FastAPI.

No primeiro teste foi utilizada uma resposta fixa:

```json
{"answer":"Teste recebido pelo n8n"}
```

O teste confirmou a comunicacao entre FastAPI, Webhook e Respond to Webhook.

No MVP, o no deve usar `First Incoming Item` para devolver a saida do AI Agent. A resposta deve conter `perfil`, `destaque`, `oportunidade` e `mensagem`.

O validador do FastAPI aceita JSON puro ou JSON retornado dentro de texto/Markdown, desde que o objeto contenha os quatro campos obrigatorios.

## Comandos principais

### Verificar Docker

```powershell
docker --version
docker version
docker ps
```

### Verificar Ollama

```powershell
ollama --version
ollama list
```

Se o terminal antigo nao reconhecer `ollama`, abrir um PowerShell novo. O executavel foi instalado em:

```text
C:\Users\lucca\AppData\Local\Programs\Ollama\ollama.exe
```

### Verificar API do Ollama

```powershell
Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing
```

### Iniciar FastAPI

Executar no mesmo PowerShell, uma linha por vez:

```powershell
$env:N8N_WEBHOOK_URL = "http://localhost:5678/webhook-test/agente"
```

```powershell
& "C:\Users\lucca\Projetos(PY,JAVA)\agente-ia-indicadores\.venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir "C:\Users\lucca\Projetos(PY,JAVA)\agente-ia-indicadores" --host 127.0.0.1 --port 8002
```

O terminal do Uvicorn deve permanecer aberto.

### Testar FastAPI

Em outro PowerShell:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8002/health"
```

Retorno esperado:

```text
status
------
ok
```

### Testar o MVP completo

No n8n, clicar em **Execute workflow**. Em outro PowerShell:

```powershell
$body = @'
{
        "idade": 25,
        "imc": 23.4,
        "fc_repouso": 68,
        "atividade_score": 80,
        "resistencia_score": 75,
        "fc_score": 70,
        "habitos_score": 65,
        "indice_move": 74
}
'@
```

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8002/analyze" -ContentType "application/json" -Body $body
```

Retorno do teste inicial:

```text
answer  : Teste recebido pelo n8n
status  : success
```

Retorno esperado com o Ollama:

```text
perfil        : resposta gerada pelo llama3.2
destaque      : ...
oportunidade  : ...
mensagem      : ...
```

Valores fora dos limites definidos em `ParticipantIndicators` devem retornar `422 Unprocessable Entity` antes de chamar o n8n.

## Problemas encontrados

### Porta 8002 ocupada

O erro `[WinError 10048]` significa que outra instancia do Uvicorn ja esta usando a porta. Verificar antes de iniciar:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8002/health"
```

Se necessario, localizar e encerrar o processo:

```powershell
Get-NetTCPConnection -LocalPort 8002 -State Listen
Stop-Process -Id NUMERO_DO_PID -Force
```

### Uso de `cd /d`

`cd /d` pertence ao Prompt de Comando. No PowerShell, usar:

```powershell
Set-Location "C:\Users\lucca\PYprjectVSC"
```

### Modulo `app` nao encontrado

Usar `--app-dir` para indicar explicitamente onde esta o arquivo:

```powershell
--app-dir "C:\Users\lucca\PYprjectVSC"
```

### Webhook 404

Causas possiveis:

- workflow nao esta em **Execute workflow**;
- caminho do Webhook nao e `agente`;
- URL de teste foi digitada incorretamente;
- foi usada URL `/webhook/agente` sem ativar o workflow.

### Respond to Webhook ausente

Quando o Webhook esta configurado para responder por um no separado, o workflow precisa conter:

```text
Webhook -> Respond to Webhook
```

### Timeout

A primeira resposta do modelo local pode demorar enquanto o modelo e carregado na memoria. O timeout da chamada ao n8n no `app.py` foi ajustado para 120 segundos.

## Custos

Para o uso academico local planejado:

- n8n self-hosted: sem assinatura do n8n Cloud;
- Ollama e modelo local: sem custo por requisicao;
- FastAPI: software gratuito;
- Docker Desktop: observar os termos de uso conforme o tipo de uso;
- hardware, energia e espaco em disco continuam sendo recursos necessarios.

## Estado atual em 27/08/2026

Concluido:

- Docker Desktop instalado e funcionando;
- n8n self-hosted executando no Docker;
- Ollama instalado;
- modelo `llama3.2:latest` baixado;
- FastAPI funcionando na porta `8002`;
- endpoint `/analyze` estruturado para receber indicadores;
- integracao real com o webhook do n8n implementada;
- resposta da IA validada pelo modelo `AnalysisResponse`;
- validador preparado para JSON puro, Markdown ou texto ao redor do JSON;
- comunicacao FastAPI -> n8n testada com sucesso em 23/08/2026;
- fluxo com resposta fixa validado em 23/08/2026;
- MVP de indicadores implementado em 27/08/2026;
- integracao do `ai_service.py` com o webhook implementada;
- resposta estruturada validada pelo modelo `AnalysisResponse`;
- validador preparado para respostas JSON puras, Markdown ou texto ao redor do JSON;
- teste de contrato HTTP da integracao concluido com sucesso;
- documentacao atualizada para separar as etapas por data.

Em andamento:

- repetir e registrar o teste ponta a ponta do `/analyze` com o workflow real do n8n;
- evoluir a documentacao junto com o projeto bruto.

**Próximos passos do projeto final**

1. Confirmar o teste ponta a ponta do `/analyze` com o n8n real.
2. Padronizar e versionar o JSON de entrada e saída.
3. Definir as regras de interpretação dos indicadores.
4. Criar testes automatizados para modelos, prompt, validador e rota.
5. Melhorar o tratamento de erros e logs.
6. Desenvolver a interface web.
7. Adicionar persistência de dados, se necessário.
8. Revisar segurança, organização e desempenho.
9. Fazer testes completos com todos os participantes.
10. Preparar a apresentação e a documentação acadêmica final.
