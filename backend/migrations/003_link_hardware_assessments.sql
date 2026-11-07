ALTER TABLE hardware_measurement_batches
    ADD COLUMN IF NOT EXISTS assessment_id INTEGER REFERENCES participantes(id);

CREATE TABLE IF NOT EXISTS hardware_assessment_assignments (
    device_id TEXT PRIMARY KEY,
    assessment_id INTEGER UNIQUE REFERENCES participantes(id),
    assigned_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS hardware_assessment_assignments_assessment_idx
    ON hardware_assessment_assignments (assessment_id)
    WHERE assessment_id IS NOT NULL;
