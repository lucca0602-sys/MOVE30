-- Cadastro no totem aceita apenas nome, idade, FAS e nível do teste.
-- Aplicar uma vez no mesmo banco configurado para a API.
ALTER TABLE participantes
    ALTER COLUMN peso DROP NOT NULL,
    ALTER COLUMN altura DROP NOT NULL,
    ALTER COLUMN fc_pre_teste DROP NOT NULL,
    ALTER COLUMN fc_pos_teste DROP NOT NULL,
    ALTER COLUMN imc DROP NOT NULL;
