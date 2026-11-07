-- O teste simples agora é uma opção do cadastro e é medido na estação (peso + 1 batimento),
-- então nasce sem medidas. Remove a regra da 006 que exigia as medidas já no cadastro.
ALTER TABLE participantes DROP CONSTRAINT IF EXISTS participantes_simples_completo_check;
