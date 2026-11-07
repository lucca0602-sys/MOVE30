-- Controle das novas tentativas da IA e proteção contra perda de dados.
ALTER TABLE participantes
    ADD COLUMN IF NOT EXISTS ia_tentativas INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS ia_proxima_tentativa TIMESTAMPTZ;

-- Medição e análise gravadas não mudam, e participante não é apagado.
-- Para uma correção deliberada, um administrador desliga o gatilho no banco.
CREATE OR REPLACE FUNCTION proteger_participante() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Participante % não pode ser apagado.', OLD.id;
    END IF;
    IF (OLD.peso IS NOT NULL AND NEW.peso IS DISTINCT FROM OLD.peso)
        OR (OLD.altura IS NOT NULL AND NEW.altura IS DISTINCT FROM OLD.altura)
        OR (OLD.fc_pre_teste IS NOT NULL AND NEW.fc_pre_teste IS DISTINCT FROM OLD.fc_pre_teste)
        OR (OLD.fc_pos_teste IS NOT NULL AND NEW.fc_pos_teste IS DISTINCT FROM OLD.fc_pos_teste)
        OR (OLD.perfil IS NOT NULL AND NEW.perfil IS DISTINCT FROM OLD.perfil)
        OR (OLD.mensagem IS NOT NULL AND NEW.mensagem IS DISTINCT FROM OLD.mensagem) THEN
        RAISE EXCEPTION 'Dado já gravado do participante % não pode ser sobrescrito.', OLD.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS proteger_participante ON participantes;
CREATE TRIGGER proteger_participante
    BEFORE UPDATE OR DELETE ON participantes
    FOR EACH ROW EXECUTE FUNCTION proteger_participante();

CREATE OR REPLACE FUNCTION proteger_lote_hardware() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Leitura bruta do hardware não pode ser alterada nem apagada.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS proteger_lote_hardware ON hardware_measurement_batches;
CREATE TRIGGER proteger_lote_hardware
    BEFORE UPDATE OR DELETE ON hardware_measurement_batches
    FOR EACH ROW EXECUTE FUNCTION proteger_lote_hardware();
