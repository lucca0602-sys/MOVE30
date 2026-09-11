
# Documentação Projeto SETOR DE IA

## Objetivo

Construir um agente local para projetos acadêmicos usando FastAPI como API de entrada, n8n self-hosted como orquestrador e Ollama como modelo de inteligência artificial local.

A documentação será ampliada conforme novas funcionalidades, testes e integrações forem desenvolvidos.

---

## Histórico de desenvolvimento e validações

Esta seção registra quando cada etapa foi realizada para que a evolução do projeto possa ser compreendida por pessoas técnicas e não técnicas.

Os registros históricos são mantidos mesmo após a evolução do projeto, permitindo visualizar como a arquitetura, os testes e o entendimento das tecnologias evoluíram ao longo do desenvolvimento.

### 23/08/2026 - Infraestrutura e teste de conexão

Atividades realizadas:

- configuração do Docker Desktop com WSL 2 no Windows;
- instalação e inicialização do n8n self-hosted em container Docker;
- criação do volume persistente `n8n_data`;
- instalação do Ollama local;
- download do modelo `llama3.2:latest`;
- criação do workflow inicial com Webhook e Respond to Webhook;
- configuração do FastAPI para envio de requisições ao webhook;
- teste de comunicação entre FastAPI e n8n.

Validação concluída:

```text
FastAPI -> Webhook n8n -> Respond to Webhook -> FastAPI

Resultado:
answer = Teste recebido pelo n8n
status = success
```

Problemas encontrados e resolvidos:

- virtualização e componentes do WSL 2 precisaram ser habilitados;
- o n8n precisa ser executado pelo Docker Desktop;
- comandos `cd /d` foram substituídos por `Set-Location` no PowerShell;
- conflitos de porta foram tratados mantendo uma única instância do servidor;
- o caminho do módulo FastAPI foi corrigido com `--app-dir`.

Encerramento da etapa:

- infraestrutura local validada;
- comunicação básica validada;
- pendência: conectar o AI Agent ao Ollama e definir o contrato dos indicadores.

---

### 27/08/2026 - Primeiro MVP de indicadores

Atividades realizadas:

- definição do modelo `ParticipantIndicators`;
- validação de tipos e limites dos indicadores com Pydantic;
- criação do prompt especializado em interpretação de indicadores;
- implementação do endpoint `POST /analyze`;
- substituição da simulação por uma chamada ao webhook do n8n;
- conexão do AI Agent ao Ollama com o modelo Llama 3.2;
- definição da resposta estruturada com quatro campos;
- normalização de respostas JSON puras, em Markdown ou acompanhadas de texto;
- teste com indicadores válidos e teste com valores extremos dentro dos limites.

Contrato validado:

```json
{
  "perfil": "...",
  "destaque": "...",
  "oportunidade": "...",
  "mensagem": "..."
}
```

Resultado da validação:

- o FastAPI recebeu os indicadores;
- o prompt e os indicadores foram enviados ao n8n;
- o n8n encaminhou a solicitação ao AI Agent;
- o Ollama gerou a resposta;
- o FastAPI validou o JSON recebido.

Pendências definidas ao final da etapa:

- adicionar testes automatizados ao diretório `tests`;
- revisar o contrato final de entrada e saída;
- definir regras de interpretação e classificação dos indicadores;
- revisar o workflow e documentar sua versão de produção.

---

## MVP implementado em 27/08/2026

O primeiro MVP recebe os indicadores de um participante, cria um prompt especializado, envia os dados ao n8n, solicita uma interpretação ao AI Agent conectado ao Ollama/Llama 3.2 e devolve uma resposta estruturada em JSON.

Contrato da resposta:

```json
{
  "perfil": "...",
  "destaque": "...",
  "oportunidade": "...",
  "mensagem": "..."
}
```

---

## Arquitetura registrada em 27/08/2026

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

Esta arquitetura representa o estágio do MVP em 27/08/2026 e foi mantida na documentação para registrar a evolução técnica do projeto.

---

## Componentes do primeiro MVP

### FastAPI

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

Executa o n8n em um container Linux no Windows utilizando WSL 2.

### n8n self-hosted

O n8n foi instalado localmente utilizando Docker.

Endereço:

```text
http://localhost:5678
```

O container utiliza o volume persistente:

```text
n8n_data
```

### Ollama

O Ollama executa o modelo de IA localmente e disponibiliza uma API local.

```text
http://localhost:11434
```

Modelo instalado:

```text
llama3.2:latest
```

Não foi necessária chave de API para utilização local do Ollama.

---

## Workflow n8n registrado no primeiro MVP

O workflow utilizado durante a construção inicial do agente foi:

```text
Webhook -> AI Agent -> Respond to Webhook
             ^
             |
      Ollama Chat Model
```

### Webhook

Configuração utilizada:

```text
HTTP Method: POST
Path: agente
Respond: Using Respond to Webhook Node
Authentication: None
```

URL utilizada durante os testes:

```text
http://localhost:5678/webhook-test/agente
```

Para utilizar a URL de teste, era necessário executar o workflow antes de enviar uma requisição.

Para uso contínuo com o workflow ativo:

```text
/webhook/agente
```

### Agente de IA

O AI Agent recebia a mensagem e o contexto enviados pelo Webhook e solicitava uma resposta ao modelo conectado.

Prompt inicial utilizado:

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

Configuração:

```text
Model: llama3.2:latest
Base URL: http://host.docker.internal:11434
```

O endereço `host.docker.internal` permite que o container do n8n acesse o Ollama executado diretamente no Windows.

Dentro do container, `localhost` apontaria para o próprio container.

### Respond to Webhook

Responsável por devolver a resposta do workflow ao FastAPI.

No primeiro teste foi utilizada uma resposta fixa:

```json
{
  "answer": "Teste recebido pelo n8n"
}
```

Esse teste confirmou inicialmente a comunicação:

```text
FastAPI -> Webhook -> Respond to Webhook -> FastAPI
```

Posteriormente, a resposta passou a utilizar os campos:

```text
perfil
destaque
oportunidade
mensagem
```

---

# Registro do estado do projeto em 27/08/2026

Esta seção é mantida como **registro histórico** e representa o estado do projeto naquele momento.

Ela não deve ser interpretada como o estado atual do MOVE30.

## Concluído em 27/08/2026

- Docker Desktop instalado e funcionando;
- n8n self-hosted no Docker;
- Ollama instalado;
- modelo `llama3.2:latest` baixado;
- FastAPI funcionando na porta `8002`;
- endpoint `/analyze` estruturado para receber indicadores;
- integração real com o webhook do n8n;
- resposta da IA validada pelo modelo `AnalysisResponse`;
- validador preparado para JSON puro, Markdown ou texto ao redor do JSON;
- comunicação FastAPI -> n8n testada com sucesso em 23/08/2026;
- fluxo com resposta fixa validado em 23/08/2026;
- MVP de indicadores implementado em 27/08/2026;
- integração do `ai_service.py` com o webhook;
- teste de contrato HTTP da integração concluído com sucesso.

## Em andamento em 27/08/2026

- repetir e registrar o teste ponta a ponta do `/analyze` com o workflow real do n8n;
- evoluir a documentação junto com o projeto bruto.

## Próximos passos definidos em 27/08/2026

1. Confirmar o teste ponta a ponta do `/analyze` com o n8n real.
2. Padronizar e versionar o JSON de entrada e saída.
3. Definir as regras de interpretação dos indicadores.
4. Criar testes automatizados para modelos, prompt, validador e rota.
5. Melhorar o tratamento de erros e logs.
6. Desenvolver uma interface web.
7. Adicionar persistência de dados, se necessário.
8. Revisar segurança, organização e desempenho.
9. Fazer testes completos com os participantes.
10. Preparar a apresentação e a documentação acadêmica final.

---

# Evolução experimental do MOVE30

As etapas seguintes registram os testes realizados após o primeiro MVP.

Esses testes **não substituíram o trabalho bruto desenvolvido anteriormente**.

O objetivo foi utilizar o ecossistema como ambiente experimental para compreender como as tecnologias planejadas para o MOVE30 podem se comunicar, como os dados percorrem o sistema e quais responsabilidades devem pertencer ao backend, à camada de processamento e à inteligência artificial.

---

## 02/09/2026 - Início da fase de integração e refinamento do MOVE30

A partir de 02/09/2026 foi iniciada uma nova fase experimental do MOVE30, com foco em aproximar o MVP do fluxo previsto para o projeto final.

O objetivo deixou de ser apenas comprovar a comunicação entre FastAPI, n8n e IA e passou a incluir cadastro de participantes, persistência dos dados, visualização no frontend e análise do comportamento da IA diante dos indicadores.

Objetivos desta fase:

- compreender o fluxo completo dos dados entre as camadas do sistema;
- observar como os indicadores chegavam ao modelo de IA;
- identificar interpretações incorretas ou não definidas pelo projeto;
- analisar a separação entre cálculos e classificações determinísticas e interpretação pela IA;
- experimentar a utilização conjunta das tecnologias previstas para o projeto;
- preparar o ecossistema para futuras integrações com dados provenientes do IoT.

---

## 05/09/2026 - Teste ponta a ponta do ecossistema MOVE30

Foi realizado um teste completo para validar a integração entre as principais partes do protótipo.

Fluxo testado:

```text
Frontend
   |
   v
FastAPI
   |
   v
PostgreSQL
   |
   v
n8n
   |
   v
IA
   |
   v
Validação da resposta
   |
   v
Frontend
```

De forma resumida:

```text
Frontend -> FastAPI -> PostgreSQL -> n8n -> IA
         -> validação -> Frontend
```

### Atividades realizadas

- cadastro do participante pelo frontend;
- envio dos dados ao FastAPI;
- persistência dos dados no PostgreSQL;
- recuperação dos indicadores pelo backend;
- montagem do payload enviado ao n8n;
- envio dos indicadores para processamento pela IA;
- retorno estruturado nos campos `perfil`, `destaque`, `oportunidade` e `mensagem`;
- validação da resposta no backend com Pydantic;
- exibição da análise no frontend.

### Resultado

- o teste ponta a ponta funcionou;
- o frontend conseguiu cadastrar o participante;
- os dados puderam ser armazenados no PostgreSQL;
- o backend conseguiu recuperar e preparar os indicadores;
- a integração entre frontend, backend, banco de dados, n8n e IA foi comprovada;
- a resposta retornou ao sistema;
- a análise foi exibida no frontend;
- a estrutura de resposta definida para o protótipo foi mantida.

### Problemas identificados durante os testes de interpretação

Apesar do funcionamento da integração, os testes demonstraram que a IA estava realizando classificações e inferências sem regras determinísticas suficientes.

Entre os problemas observados:

- em participantes menores de idade, a IA atribuiu classificações de IMC sem que o sistema tivesse implementado critérios específicos por idade e sexo;
- em participante adulto, IMC `20` foi interpretado como abaixo do peso;
- `fc_repouso` recebeu interpretações semânticas que não estavam definidas pelo projeto;
- alguns scores foram transformados em conclusões que não estavam explicitamente presentes nos dados enviados.

Esses testes mostraram uma diferença importante entre:

**calcular/classificar dados** e **interpretar dados**.

### Conclusão técnica da etapa

> O fluxo de integração estava funcional, porém a IA não deveria ser responsável por calcular ou decidir classificações objetivas que podem ser determinadas pelo próprio sistema.

A partir dessa conclusão, foi definida como próxima ação a criação de regras no backend para tratar determinados indicadores antes de enviá-los à IA.

O teste não alterou a finalidade do projeto bruto.

Ele permitiu compreender melhor **como o projeto deverá evoluir e como as tecnologias poderão ser aplicadas na arquitetura final**.

---

## 10/09/2026 - Tratamento determinístico do IMC e validação do protótipo experimental

Após analisar os erros encontrados nos testes anteriores, foi decidido retirar da IA a responsabilidade de classificar o IMC nos casos tratados pela regra implementada no protótipo.

A classificação passou a ser realizada diretamente pelo backend utilizando uma regra determinística em Python.

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

A IA deixa de decidir livremente a classificação do IMC e passa a trabalhar com a informação previamente tratada pelo sistema.

### Erro encontrado durante a implementação

Durante o primeiro teste após a alteração foi retornado:

```text
NameError: name 'classificar_imc' is not defined
```

O problema ocorreu porque o arquivo `n8n_service.py` utilizava a função `classificar_imc()`, porém ela ainda não havia sido importada.

Correção:

```python
from backend.models.participant import classificar_imc
```

Após a correção, o backend voltou a montar o payload normalmente e os testes puderam continuar.

### Testes de validação da classificação

Foram realizados testes com participantes contendo valores de IMC em diferentes faixas.

| IMC | Classificação esperada | Resultado |
|---:|---|---|
| 17.2 | Abaixo do peso | Aprovado |
| 22.0 | Peso considerado normal | Aprovado |
| 27.4 | Sobrepeso | Aprovado |
| 32.8 | Obesidade grau I | Aprovado |
| 42.3 | Obesidade grau III | Aprovado |

Após o tratamento no backend, a resposta passou a utilizar corretamente a classificação recebida no payload.

Com isso, a regra implementada para classificação do IMC foi considerada **validada no protótipo experimental**.

### Limitações observadas após a correção do IMC

A classificação do IMC foi corrigida, porém os testes também revelaram problemas semânticos em outros indicadores.

Entre os exemplos observados:

- `fc_repouso` foi interpretado em alguns testes como porcentagem ou tempo de repouso;
- `fc_score` recebeu interpretações e nomes incorretos;
- nomes internos de alguns scores apareceram diretamente no texto;
- a IA realizou algumas inferências além do que os indicadores isoladamente permitem afirmar.

Esses pontos foram mantidos como **limitações conhecidas do protótipo**.

O refinamento desses indicadores será realizado posteriormente, quando as regras de processamento e a integração com os dados reais provenientes do IoT estiverem mais definidas.

### Aprendizado obtido com os testes

A bateria de testes realizada entre 02/09 e 10/09 permitiu compreender melhor como os dados devem ser tratados antes de chegarem à IA.

Foi estabelecido como referência para a evolução do MOVE30:

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

Esse aprendizado será utilizado na evolução do projeto quando as tecnologias forem integradas aos dados reais das estações e sensores.

---

## Workflow n8n utilizado no protótipo experimental

Na configuração atual do protótipo, o fluxo do n8n foi simplificado para:

```text
Webhook -> HTTP Request -> Respond to Webhook
```

O `HTTP Request` é utilizado como etapa de integração com o serviço configurado para processamento da requisição.

Essa mudança faz parte da evolução experimental e não altera o registro histórico do workflow utilizado em 27/08/2026.

---

# Estado atual do protótipo experimental em 10/09/2026

Este estado representa o ecossistema utilizado nos testes e **não substitui o registro histórico do MVP de 27/08**.

## Concluído nesta fase experimental

- FastAPI integrado ao ecossistema de testes;
- PostgreSQL integrado ao protótipo;
- frontend para cadastro e visualização da análise funcionando;
- participantes sendo cadastrados e armazenados no banco;
- comunicação entre FastAPI e n8n validada;
- integração com o serviço de IA utilizada nos testes;
- resposta estruturada com `perfil`, `destaque`, `oportunidade` e `mensagem`;
- validação da resposta da IA no backend;
- teste ponta a ponta do ecossistema realizado em 05/09/2026;
- fluxo experimental entre frontend, backend, banco, n8n e IA validado;
- erros de interpretação da IA identificados por meio dos testes;
- classificação do IMC transferida para uma regra determinística no backend;
- `classificacao_imc` adicionada ao payload enviado ao n8n;
- erro de importação da função `classificar_imc` identificado e corrigido;
- classificação do IMC validada em diferentes faixas em 10/09/2026;
- funcionamento do protótipo confirmado pelo Swagger e pelo frontend utilizando Live Server.

## Em andamento

- consolidar a documentação técnica e as evidências dos testes do protótipo;
- manter o registro de testes, erros encontrados, causas e correções;
- estudar quais outros indicadores precisam de regras determinísticas;
- alinhar o significado e as unidades dos indicadores com a futura etapa de IoT;
- revisar gradualmente o contrato de entrada, payload interno e saída;
- estudar como os dados reais das estações e sensores serão integrados ao ecossistema;
- utilizar os resultados do protótipo como referência para a evolução da arquitetura do projeto final.

---

# Próximos passos do projeto

1. Consolidar a documentação e as evidências dos testes do protótipo experimental.
2. Padronizar e versionar o JSON de entrada, payload interno e resposta.
3. Definir as regras oficiais de cálculo e classificação dos indicadores conforme as especificações do projeto.
4. Integrar futuramente os indicadores calculados a partir dos dados reais do IoT.
5. Refinar as instruções fornecidas à IA com o significado e a unidade correta de cada indicador.
6. Reduzir interpretações não sustentadas pelos dados e impedir que a IA invente unidades ou classificações.
7. Criar testes automatizados para modelos, regras determinísticas, payload, validação e rotas.
8. Melhorar tratamento de erros, logs e rastreabilidade das chamadas entre as diferentes partes do ecossistema.
9. Revisar segurança, organização do código e desempenho antes da versão de apresentação.
10. Executar testes completos utilizando os participantes e dados definidos pelo projeto.
11. Evoluir o protótipo conforme as definições das equipes responsáveis por IoT, banco de dados e processamento.
12. Preparar a apresentação e a documentação acadêmica final.

---

# Conclusão da fase atual

O protótipo experimental cumpriu seu objetivo como ambiente de testes.

O desenvolvimento iniciado com a comunicação entre FastAPI, n8n e Ollama evoluiu para um teste envolvendo frontend, backend, persistência de dados e interpretação por IA.

Os testes não tiveram como objetivo substituir a arquitetura ou o planejamento original do MOVE30.

Eles permitiram compreender, na prática, **como as tecnologias podem ser conectadas, como os dados percorrem o ecossistema e quais responsabilidades devem ser atribuídas a cada camada do sistema**.

O principal aprendizado desta fase foi a separação entre processamento determinístico e interpretação por inteligência artificial.

A experiência com a classificação do IMC demonstrou que regras objetivas devem ser tratadas pelo sistema antes que os dados sejam enviados ao modelo de IA.

A partir desses resultados, os testes do protótipo passam a servir como referência técnica para as próximas etapas de desenvolvimento e integração do MOVE30.

---
