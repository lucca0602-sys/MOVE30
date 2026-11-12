-- A esteira saiu. O teste com esforço (tipo_avaliacao = 'completa') agora é:
--   bike: por tempo, nível leve/médio/pesado (tipo_teste light/moderate/hard = 1/2/3 min);
--   agachamento, abdominal ou flexão: 20 repetições, sem nível.
-- Linhas antigas 'completa' sem modalidade foram feitas na esteira (corrida).
ALTER TABLE participantes ADD COLUMN IF NOT EXISTS modalidade VARCHAR(20);
ALTER TABLE participantes DROP CONSTRAINT IF EXISTS participantes_modalidade_check;
ALTER TABLE participantes ADD CONSTRAINT participantes_modalidade_check
    CHECK (modalidade IS NULL OR modalidade IN ('bike', 'agachamento', 'abdominal', 'flexao'));
