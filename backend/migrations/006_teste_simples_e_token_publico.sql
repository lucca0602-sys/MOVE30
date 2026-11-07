-- Teste simples (peso, altura e FC de repouso, sem corrida) e link público por participante.
-- token_publico vai no QR Code (/dash/<token>): aleatório, então não dá para chutar o de outra pessoa.
-- Registros existentes recebem 'completa' e um token novo cada; nada é apagado.
ALTER TABLE participantes
    ADD COLUMN IF NOT EXISTS tipo_avaliacao VARCHAR(10) NOT NULL DEFAULT 'completa',
    ADD COLUMN IF NOT EXISTS token_publico UUID NOT NULL DEFAULT gen_random_uuid();

-- O teste simples não pergunta FAS.
ALTER TABLE participantes ALTER COLUMN fas DROP NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS participantes_token_publico_idx ON participantes (token_publico);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'participantes_tipo_avaliacao_check') THEN
        ALTER TABLE participantes ADD CONSTRAINT participantes_tipo_avaliacao_check
            CHECK (tipo_avaliacao IN ('completa', 'simples'));
    END IF;
    -- Teste simples sempre nasce com as três medidas preenchidas.
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'participantes_simples_completo_check') THEN
        ALTER TABLE participantes ADD CONSTRAINT participantes_simples_completo_check
            CHECK (tipo_avaliacao <> 'simples'
                   OR (peso IS NOT NULL AND altura IS NOT NULL AND fc_pre_teste IS NOT NULL));
    END IF;
END $$;

-- Token e tipo da avaliação não mudam depois de criados (o QR impresso continua valendo).
CREATE OR REPLACE FUNCTION proteger_token_publico() RETURNS trigger AS $$
BEGIN
    IF NEW.token_publico IS DISTINCT FROM OLD.token_publico
        OR NEW.tipo_avaliacao IS DISTINCT FROM OLD.tipo_avaliacao THEN
        RAISE EXCEPTION 'Token e tipo da avaliação % não podem ser alterados.', OLD.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS proteger_token_publico ON participantes;
CREATE TRIGGER proteger_token_publico
    BEFORE UPDATE ON participantes
    FOR EACH ROW EXECUTE FUNCTION proteger_token_publico();
