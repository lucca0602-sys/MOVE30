from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal

class ParticipantIndicators(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    # Opcional: o cadastro do totem não pede e-mail.
    email: str | None = Field(default=None, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    idade: int = Field(ge=1, le=120)
    peso: float | None = Field(default=None, ge=10, le=200)
    # Opcional: vazia, o sensor da estação mede logo depois do peso.
    altura: float | None = Field(default=None, ge=1, le=2.2)
    fas: int = Field(ge=1, le=7)
    fc_pre_teste: int | None = Field(default=None, ge=30, le=220)
    fc_pos_teste: int | None = Field(default=None, ge=30, le=220)
    # "simples": sem esforço, a estação mede peso e 1 batimento.
    # "completa": com esforço (bike ou 20 repetições), FC antes e depois.
    tipo_avaliacao: Literal["completa", "simples"] = "completa"
    modalidade: Literal["bike", "agachamento", "abdominal", "flexao"] | None = None
    # Nível da bike (leve/médio/pesado = 1/2/3 min). Os exercícios não têm nível.
    tipo_teste: Literal["light", "moderate", "hard"] | None = None

    @model_validator(mode="after")
    def regras_do_tipo(self):
        if self.tipo_avaliacao == "simples":
            if self.fc_pos_teste is not None:
                raise ValueError("O teste simples não tem batimento depois do esforço.")
            self.modalidade = None
            self.tipo_teste = None
            return self
        if self.modalidade is None:
            self.modalidade = "bike"  # a esteira saiu; o teste com nível agora é a bike
        if self.modalidade == "bike" and self.tipo_teste is None:
            raise ValueError("Selecione o nível da bike.")
        if self.modalidade != "bike":
            self.tipo_teste = None
        return self

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        if isinstance(value, str):
            value = value.strip().lower()
            return value or None
        return value

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
    