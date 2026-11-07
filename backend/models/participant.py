from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal

class ParticipantIndicators(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    email: str = Field(max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    idade: int = Field(ge=1, le=120)
    peso: float | None = Field(default=None, ge=10, le=200)
    altura: float = Field(ge=1, le=2.2)
    fas: int = Field(ge=1, le=7)
    fc_pre_teste: int | None = Field(default=None, ge=30, le=220)
    fc_pos_teste: int | None = Field(default=None, ge=30, le=220)
    # "simples": sem corrida, a estação mede peso e 1 batimento. "completa": com corrida.
    tipo_avaliacao: Literal["completa", "simples"] = "completa"
    tipo_teste: Literal["light", "moderate", "hard"] | None = None

    @model_validator(mode="after")
    def regras_do_tipo(self):
        if self.tipo_avaliacao == "completa" and self.tipo_teste is None:
            raise ValueError("Selecione o nível do teste com corrida.")
        if self.tipo_avaliacao == "simples":
            if self.fc_pos_teste is not None:
                raise ValueError("O teste simples não tem batimento depois da corrida.")
            self.tipo_teste = None
        return self

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("nome", mode="before")
    @classmethod
    def normalize_nome(cls, value):
        return " ".join(value.split()) if isinstance(value, str) else value


class ManualMeasurements(BaseModel):
    peso: float | None = Field(default=None, ge=10, le=200)
    altura: float | None = Field(default=None, ge=1, le=2.2)
    fc_pre_teste: int | None = Field(default=None, ge=30, le=220)
    fc_pos_teste: int | None = Field(default=None, ge=30, le=220)

    @model_validator(mode="after")
    def at_least_one_measurement(self):
        if all(value is None for value in self.model_dump().values()):
            raise ValueError("Informe ao menos uma medição.")
        return self

    
class AnalysisResponse(BaseModel):
    perfil: str = Field(min_length=1)
    destaque: str = Field(min_length=1)
    oportunidade: str = Field(min_length=1)
    mensagem: str = Field(min_length=1)


def classificar_imc(imc: float) -> str:

    if imc < 18.5:
        return "Abaixo do peso"

    elif imc < 25:
        return "Peso considerado normal"

    elif imc < 30:
        return "Sobrepeso"

    elif imc < 35:
        return "Obesidade grau I"

    elif imc < 40:
        return "Obesidade grau II"

    else:
        return "Obesidade grau III"
    