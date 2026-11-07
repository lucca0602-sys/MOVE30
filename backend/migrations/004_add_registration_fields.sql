-- E-mail do cadastro, data de criação e cancelamento da avaliação.
-- Registros existentes ficam com email e criado_em nulos; nada é apagado.
ALTER TABLE participantes
    ADD COLUMN IF NOT EXISTS email VARCHAR(254),
    ADD COLUMN IF NOT EXISTS criado_em TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS cancelada_em TIMESTAMPTZ;

ALTER TABLE participantes
    ALTER COLUMN criado_em SET DEFAULT NOW();
