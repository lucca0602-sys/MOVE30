# Fluxo de avaliação com hardware MOVE 30

A ESP32-S3 agora trabalha com **uma pessoa por vez**, porque o equipamento atual não identifica pessoas por QR, código ou leitor. Isso evita atribuir a leitura de uma pessoa a outra.

## Sequência operacional

1. A pessoa conclui o cadastro no totem: nome, idade, FAS e tipo de teste. Altura, peso e FC são opcionais (seção manual); o que for preenchido é preservado e pulado pelo hardware.
2. A ESP32 chama `GET /api/v1/hardware/assessments/next`, autenticada com `X-Device-Key` e identificada por `X-Device-ID`.
3. O backend reserva para aquele dispositivo a avaliação pendente de menor ID, ignorando as canceladas, e devolve a próxima etapa. A reserva persiste se a placa reiniciar.
4. O firmware conduz as etapas pendentes na ordem: **peso, altura (VL53L0X), FC de repouso e FC pós-teste**. A altura vem logo depois do peso: a pessoa desce da balança e fica embaixo do sensor. O esforço cadastrado (45 s de bike ou 20 repetições) ocorre entre as duas leituras de FC, conduzido pela equipe; a ESP32 não controla a bike. A FC pós-teste só começa depois de o dedo sair do sensor e passar `FC_POS_ESPERA_MS` (60 s).
5. Cada leitura é enviada para `POST /api/v1/hardware/measurements` com `assessment_id`, nome/unidade do sensor, horário UTC e UUID. O backend valida que a etapa pertence à avaliação reservada, grava o lote bruto e atualiza a coluna do participante na mesma transação.
6. A resposta informa a próxima etapa. Após a última leitura, a reserva é liberada e a análise da IA é tentada em segundo plano. Se o serviço de IA falhar, os dados continuam salvos, a API tenta de novo a cada `IA_INTERVALO_S` (10 minutos) e o dashboard pessoal também permite tentar. O dashboard pessoal atualiza a cada 3 segundos e o geral a cada 5. A página **Estação de medição** (`GET /estacao/status`) mostra a cada 2 segundos quem está na estação, em qual etapa, e quem aguarda. A etapa vem dos dados já salvos; o sistema não detecta a corrida em si, então "Corrida e FC depois" é uma única etapa.

## Contrato da API

### Consultar/reservar avaliação

`GET /api/v1/hardware/assessments/next`

Cabeçalhos: `X-Device-Key` e `X-Device-ID`.

Sem fila, retorna `{"status":"waiting"}`. Quando encontra uma avaliação, retorna `status: active`, `assessment_id`, `next_measurement` e `tipo_teste`. Repetir a consulta do mesmo dispositivo retoma sua reserva ativa.

### Enviar leitura

`POST /api/v1/hardware/measurements`

Cabeçalhos: `X-Device-Key` e `X-Device-ID`. O identificador do cabeçalho precisa corresponder a `device_id` no JSON.



| Etapa | Nome no lote | Unidade | Campo atualizado |
|---|---|---|---|
| Peso | `weight` | `kg` | `peso` |
| Altura (VL53L0X) | `height` | `m` | `altura` |
| FC de repouso | `heart_rate_rest` | `bpm` | `fc_pre_teste` |
| FC pós-teste | `heart_rate_post` | `bpm` | `fc_pos_teste` |

O servidor calcula/recalcula IMC quando altura e peso estão disponíveis. FC Score já é calculado pelo serviço de analytics como a média entre FC pré e pós. Nenhum outro indicador ou fórmula é alterado pelo firmware.

- `202`: leitura gravada ou repetição idempotente confirmada; a resposta inclui `next_measurement` ou `complete: true`.
- `401`: chave inválida/ausente.
- `409`: dispositivo, reserva, etapa ou UUID incompatível.
- `422`: leitura, unidade ou faixa inválida. Faixas aceitas: peso de 10 a 200 kg e FC de 30 a 220 bpm.
- `503`: chave ou banco/migração indisponível.

O firmware persiste UUID, hora e leitura antes de enviar. Se perder a resposta, repete o mesmo evento a cada `API_REENVIO_MS`; a chave `(device_id, message_id)` impede duplicação. Em `409` ou `422`, descarta a leitura e consulta a etapa atual de novo. O evento bruto fica em `hardware_measurement_batches`, agora associado a `assessment_id`.

### Cancelar avaliação atual

`POST /api/v1/hardware/assessments/current/cancel` com `X-Device-Key` e `X-Device-ID`. O botão de emergência usa essa rota quando não há leitura aguardando confirmação. A avaliação recebe `cancelada_em`, sai da fila e some da lista dos dashboards; as leituras recebidas permanecem no banco. Quem desistiu precisa de um novo cadastro para voltar à fila.

## Preparação para operar

1. Aplique na ordem as migrações de `001` a `005` em `backend/migrations/` no banco do projeto, pulando as que já foram aplicadas.
2. Configure `ESP32_API_KEY` no processo FastAPI e copie `secrets.example.h` para `secrets.h`, preenchendo a mesma chave e o Wi-Fi. `secrets.h` está ignorado pelo Git.
3. Configure `API_URL` com um endereço acessível pela ESP32 e `DEVICE_ID` estável em `linha_medicao/linha_medicao/config.h`.
4. O relógio deve sincronizar por NTP para que `measured_at` seja real. Sem horário sincronizado, uma nova leitura não é travada para envio.
5. Confirme `FATOR_BALANCA` (contagens por kg) em `config.h`. Mantenha a balança vazia ao ligar a placa; para refazer a tara, envie `t` no Monitor Serial com a balança vazia.
6. Cadastre uma pessoa no totem. A ESP32 reservará automaticamente a avaliação pendente mais antiga, pelo ID. Após a conclusão ou o cancelamento, buscará a próxima.

O firmware em uso é o de `linha_medicao/linha_medicao/`. A subpasta `linha_medicao/linha_medicao/linha_medicao/` é uma cópia antiga e desatualizada.


