# Fluxo de cadastro e avaliação MOVE 30

## Totem

O cadastro público sempre solicita `nome`, `email`, `altura` (1,00–2,20 m), `idade`, `fas` (1–7) e `tipo_teste` (`light`, `moderate` ou `hard`). Uma seção opcional permite informar peso e FC pré/pós manualmente; ela aceita os três indicadores ou nenhum. A tela confirma o cadastro e não exibe a análise. O e-mail fica só no banco: não é devolvido pela API nem enviado à IA.

## Dashboard pessoal

O dashboard atualiza os dados a cada 3 segundos e mostra em qual etapa a pessoa está. Se os quatro indicadores manuais forem informados no cadastro, a API solicita a análise após salvar; a resposta nunca é exibida na tela do totem. O dashboard mostra a análise e permite tentar novamente se a solicitação falhar. Sem medições manuais, o cadastro fica pendente até que o hardware esteja associado à avaliação. O FC Score continua sendo calculado como a média das duas frequências, e o IMC é recalculado quando peso e altura estão disponíveis.

## Preparar o banco existente

Antes de cadastrar avaliações sem medições, aplique uma vez os arquivos `backend/migrations/002_allow_pending_manual_measurements.sql` e `backend/migrations/004_add_registration_fields.sql` no banco configurado para a API. A `002` apenas permite `NULL` nos campos que serão preenchidos depois, e a `004` adiciona `email`, `criado_em` e `cancelada_em`; nenhuma altera os valores existentes.

## Hardware

A ESP32 reserva o cadastro pendente mais antigo e envia as leituras para ele; veja `docs/hardware-api.md`.
