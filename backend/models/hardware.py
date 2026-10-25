from datetime import datetime, timezone
from math import isfinite
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HardwareMeasurement(BaseModel):
    """One raw measurement emitted by a device; names and units are hardware-defined."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    value: float = Field(allow_inf_nan=False)
    unit: str = Field(min_length=1, max_length=24)

    @field_validator("name", "unit")
    @classmethod
    def trim_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O campo não pode ficar vazio.")
        return value

    @field_validator("value")
    @classmethod
    def finite_value(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("A leitura deve ser um número finito.")
        return value


class HardwareMeasurementBatch(BaseModel):
    """Transport envelope for one idempotent batch sent by a hardware device."""

    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=1, max_length=100)
    message_id: UUID
    measured_at: datetime
    measurements: list[HardwareMeasurement] = Field(min_length=1, max_length=100)

    @field_validator("device_id")
    @classmethod
    def trim_device_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("device_id não pode ficar vazio.")
        return value

    @field_validator("measured_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("measured_at deve incluir fuso horário, preferencialmente UTC.")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def unique_measurement_names(self):
        names = [measurement.name for measurement in self.measurements]
        if len(names) != len(set(names)):
            raise ValueError("Cada nome de medição deve aparecer uma única vez por lote.")
        return self


class HardwareMeasurementAccepted(BaseModel):
    accepted: bool = True
    duplicate: bool = False
    device_id: str
    message_id: UUID
