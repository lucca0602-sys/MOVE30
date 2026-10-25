CREATE TABLE IF NOT EXISTS hardware_measurement_batches (
    device_id TEXT NOT NULL,
    message_id UUID NOT NULL,
    measured_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    measurements JSONB NOT NULL,
    CONSTRAINT hardware_measurement_batches_measurements_array
        CHECK (jsonb_typeof(measurements) = 'array'),
    CONSTRAINT hardware_measurement_batches_pk
        PRIMARY KEY (device_id, message_id)
);

CREATE INDEX IF NOT EXISTS hardware_measurement_batches_measured_at_idx
    ON hardware_measurement_batches (measured_at DESC);
