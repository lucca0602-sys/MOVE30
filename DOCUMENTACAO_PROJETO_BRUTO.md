# Documentacao Bruta do Projeto

## Objetivo

Construir um agente local para projetos academicos usando FastAPI como API de entrada, n8n self-hosted como orquestrador e Ollama como modelo de inteligencia artificial local.

A documentacao sera ampliada conforme novas funcionalidades e integracoes forem implementadas.

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

- receber `message` e `context` na rota `POST /agent`;
- enviar os dados em JSON ao webhook do n8n;
- receber o retorno do n8n;
- devolver uma resposta padronizada ao cliente.

Rotas:

```text
GET  http://127.0.0.1:8002/health
POST http://127.0.0.1:8002/agent
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

Mensagem do usuario:
{{$json.body.message}}

Contexto:
{{JSON.stringify($json.body.context)}}
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

Na versao com IA, o retorno deve ser a saida do AI Agent. Dependendo da versao do n8n, o resultado pode aparecer em `text` ou `output`.

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
& "C:\Users\lucca\AppData\Local\Programs\Python\Python314\python.exe" -m uvicorn app:app --app-dir "C:\Users\lucca\PYprjectVSC" --host 127.0.0.1 --port 8002
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

### Testar o fluxo completo

No n8n, clicar em **Execute workflow**. Em outro PowerShell:

```powershell
$body = '{"message":"Preciso de ajuda com atendimento","context":{"cliente_id":"123","canal":"whatsapp"}}'
```

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8002/agent" -ContentType "application/json" -Body $body
```

Retorno do teste inicial:

```text
answer  : Teste recebido pelo n8n
status  : success
```

Retorno esperado com o Ollama:

```text
answer  : resposta gerada pelo llama3.2
status  : success
```

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

## Estado atual

Concluido:

- Docker Desktop instalado e funcionando;
- n8n self-hosted executando no Docker;
- Ollama instalado;
- modelo `llama3.2:latest` baixado;
- FastAPI funcionando na porta `8002`;
- comunicacao FastAPI -> n8n testada com sucesso;
- fluxo com resposta fixa validado.

Em andamento:

- validar e documentar a resposta real do AI Agent com o Ollama;
- evoluir a documentacao junto com o projeto bruto.

## Proximas etapas

1. Validar a resposta real do AI Agent com o Ollama.
2. Padronizar o JSON de resposta.
3. Adicionar validacoes de entrada e erros especificos.
4. Implementar as regras de negocio do projeto academico.
5. Criar a interface web.
6. Adicionar testes automatizados.
7. Atualizar esta documentacao a cada nova etapa.
