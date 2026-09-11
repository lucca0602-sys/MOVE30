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


### 02/09/2026 - Início da fase de integração e refinamento do MOVE30

A partir de 02/09/2026 foi iniciada uma nova fase experimental do MOVE30, com foco em aproximar o MVP do fluxo previsto para o projeto final.

O objetivo deixou de ser apenas comprovar a comunicação entre FastAPI, n8n e IA e passou a incluir o cadastro de participantes, persistência dos dados, visualização no frontend e análise do comportamento da IA diante dos indicadores.

Objetivos desta fase:

- compreender o fluxo completo dos dados entre as camadas do sistema;
- observar como os indicadores chegavam ao modelo de IA;
- identificar conclusões incorretas ou não definidas pelo projeto;
- separar cálculos e classificações determinísticas da interpretação feita pela IA;
- preparar o ecossistema para futuras integrações com os dados reais provenientes do IoT.

Esta fase foi utilizada como ambiente de experimentação da **Mark I**, recebendo novas validações nos dias 05/09 e 10/09.


### 05/09/2026 - Teste ponta a ponta do ecossistema MOVE30

Foi realizado um teste completo para validar a integração entre as principais partes do protótipo.

Fluxo testado:

```text
Frontend -> FastAPI -> PostgreSQL -> n8n -> Ollama/Llama 3.2
         -> validação da resposta -> Frontend
```

Atividades realizadas:

- cadastro do participante pelo frontend;
- envio dos dados ao FastAPI;
- persistência dos dados no PostgreSQL;
- recuperação dos indicadores pelo backend;
- montagem do payload enviado ao n8n;
- envio dos indicadores para processamento pela IA;
- chamada ao modelo local Llama 3.2 pelo Ollama;
- retorno estruturado nos campos `perfil`, `destaque`, `oportunidade` e `mensagem`;
- validação da resposta no backend com Pydantic;
- exibição da análise no frontend.

Resultado:

- o teste ponta a ponta funcionou;
- o frontend conseguiu cadastrar o participante e apresentar posteriormente sua análise;
- a integração entre frontend, backend, banco de dados, n8n e IA foi comprovada;
- a estrutura de resposta definida para a Mark I foi mantida.

#### Problemas identificados durante os testes de interpretação

Apesar do funcionamento correto da integração, os testes mostraram que a IA estava realizando classificações e inferências sem regras determinísticas suficientes.

Entre os problemas observados:

- IMC `19` foi interpretado como acima do peso;
- IMC `22` foi interpretado como acima do peso;
- IMC `20` foi interpretado como abaixo do peso;
- `fc_repouso` recebeu interpretações semânticas que não estavam definidas pelo projeto;
- alguns scores foram transformados em conclusões que não estavam explicitamente presentes nos dados enviados.

Esses testes mostraram uma diferença importante entre **calcular/classificar dados** e **interpretar dados**.

Conclusão técnica da etapa:

> O fluxo de integração estava funcional, porém a IA não deveria ser responsável por calcular ou decidir classificações objetivas que podem ser determinadas pelo próprio sistema.

A partir dessa conclusão, foi definida como próxima ação a criação de regras no backend para tratar determinados indicadores antes de enviá-los à IA.


### 10/09/2026 - Tratamento determinístico do IMC e validação da Mark I

Após analisar os erros encontrados nos testes anteriores, foi decidido retirar da IA a responsabilidade de classificar o IMC.

A classificação passou a ser realizada diretamente pelo backend, utilizando uma regra determinística em Python.

Foi criada a função:

```python
def classificar_imc(imc: float) -> str:

    if imc < 18.5:
        return "Abaixo do peso"

    elif imc < 25:
        return "Peso considerado normal"

    elif imc < 30:
        return "Sobrepeso"

    elif imc < 35:
        return "Obesidade grau I"

    elif imc < 40:
        return "Obesidade grau II"

    else:
        return "Obesidade grau III"
```

A classificação calculada pelo backend passou a ser adicionada ao payload enviado ao n8n:

```python
"classificacao_imc": classificar_imc(participant["imc"])
```

Dessa forma, o fluxo passou a seguir o princípio:

```text
Valor do IMC
      |
      v
Classificação no backend
      |
      v
Payload com classificação pronta
      |
      v
n8n / IA
      |
      v
Interpretação
```

A IA deixa de decidir qual é a classificação do IMC e passa a receber essa informação já tratada pelo sistema.

#### Erro encontrado durante a implementação

Durante o primeiro teste após a alteração foi retornado:

```text
NameError: name 'classificar_imc' is not defined
```

O problema ocorreu porque o arquivo `n8n_service.py` utilizava a função `classificar_imc()`, porém ela ainda não havia sido importada.

A correção realizada foi:

```python
from backend.models.participant import classificar_imc
```

Após a correção, o backend voltou a montar o payload normalmente e os testes puderam continuar.

#### Testes de validação da classificação

Foram realizados testes com participantes contendo valores de IMC em diferentes faixas.

| IMC | Classificação esperada | Resultado |
|---:|---|---|
| 17.2 | Abaixo do peso | Aprovado |
| 22.0 | Peso considerado normal | Aprovado |
| 27.4 | Sobrepeso | Aprovado |
| 32.8 | Obesidade grau I | Aprovado |
| 42.3 | Obesidade grau III | Aprovado |

O teste com IMC `22.0` foi especialmente importante, pois valores dessa faixa haviam sido interpretados incorretamente nos testes anteriores.

Após o tratamento no backend, a resposta passou a utilizar corretamente a classificação recebida no payload.

Com isso, a regra de classificação do IMC foi considerada **validada para a Mark I**.

#### Limitações observadas após a correção do IMC

A classificação do IMC foi corrigida, porém os testes também revelaram problemas semânticos em outros indicadores.

Entre os exemplos observados:

- `fc_repouso` foi interpretado em alguns testes como porcentagem ou tempo de repouso;
- `fc_score` recebeu interpretações e nomes incorretos;
- nomes internos de alguns scores apareceram diretamente no texto;
- a IA realizou algumas inferências além do que os indicadores isoladamente permitem afirmar.

Esses pontos foram mantidos como **limitações conhecidas da Mark I**.

O refinamento desses indicadores será realizado posteriormente, quando as regras de processamento e a integração com os dados reais provenientes do IoT estiverem mais definidas.

#### Aprendizado obtido com os testes

A bateria de testes realizada entre 02/09 e 10/09 permitiu compreender melhor como os dados devem ser tratados antes de chegarem à IA.

Foi estabelecido o seguinte princípio para a evolução do MOVE30:

```text
Sensores / dados
      |
      v
Sistema calcula e classifica
      |
      v
Backend estrutura e valida
      |
      v
IA interpreta e comunica
```

Portanto:

**cálculos e classificações objetivas ficam sob responsabilidade do sistema, enquanto a IA trabalha sobre dados já tratados para produzir uma interpretação estruturada.**

## Estado atual em 10/09/2026

### Concluído

- Docker Desktop instalado e funcionando;
- n8n self-hosted funcionando localmente;
- Ollama instalado e modelo `llama3.2:latest` disponível;
- FastAPI integrado ao ecossistema;
- PostgreSQL integrado ao protótipo;
- frontend para cadastro e visualização da análise funcionando;
- participantes sendo cadastrados e armazenados no banco;
- comunicação entre FastAPI e n8n validada;
- integração com Ollama/Llama 3.2 funcionando;
- resposta estruturada com `perfil`, `destaque`, `oportunidade` e `mensagem`;
- validação da resposta da IA no backend;
- teste ponta a ponta do ecossistema realizado em 05/09/2026;
- fluxo `Frontend -> FastAPI -> PostgreSQL -> n8n -> IA -> validação -> Frontend` validado;
- erros de interpretação da IA identificados por meio dos testes;
- classificação do IMC transferida para uma regra determinística no backend;
- `classificacao_imc` adicionada ao payload enviado ao n8n;
- erro de importação da função `classificar_imc` identificado e corrigido;
- classificação do IMC validada em diferentes faixas em 10/09/2026;
- funcionamento da Mark I confirmado pelo Swagger e pelo frontend utilizando Live Server.

### Em andamento

- consolidar a documentação técnica e as evidências dos testes da Mark I;
- manter o registro de testes, erros encontrados, causas e correções;
- definir gradualmente as regras determinísticas dos demais indicadores;
- alinhar o significado e as unidades dos indicadores com a futura etapa de IoT;
- revisar o contrato final de entrada, payload interno e saída;
- preparar o ecossistema para receber futuramente os dados reais das estações e sensores.

## Próximos passos do projeto final

1. Consolidar a documentação e as evidências dos testes da Mark I.
2. Padronizar e versionar o JSON de entrada, payload interno e resposta.
3. Definir as regras oficiais de cálculo e classificação dos demais indicadores antes da interpretação pela IA.
4. Integrar os indicadores calculados a partir dos dados reais do IoT quando essa etapa estiver disponível.
5. Refinar as instruções da IA com o significado e a unidade correta de cada indicador.
6. Impedir que a IA invente unidades, classificações ou conclusões não sustentadas pelos dados.
7. Criar testes automatizados para modelos, regras determinísticas, payload, validação e rotas.
8. Melhorar o tratamento de erros, logs e rastreabilidade das chamadas entre FastAPI, PostgreSQL, n8n e IA.
9. Revisar segurança, organização do código e desempenho antes da versão de apresentação.
10. Executar testes completos utilizando os participantes e dados definidos pelo projeto.
11. Preparar a apresentação e a documentação acadêmica final.
