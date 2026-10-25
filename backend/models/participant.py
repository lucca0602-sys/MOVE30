from pydantic import BaseModel, Field, model_validator
from typing import Literal

class ParticipantIndicators(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    idade: int = Field(ge=1, le=120)
    peso: float | None = Field(default=None, gt=0, le=500)
    altura: float | None = Field(default=None, gt=0, le=3)
    fas: int = Field(ge=1, le=7)
    fc_pre_teste: int | None = Field(default=None, ge=20, le=250)
    fc_pos_teste: int | None = Field(default=None, ge=20, le=250)
    tipo_teste: Literal["light", "moderate", "hard"]
class ManualMeasurements(BaseModel):
    peso: float | None = Field(default=None, gt=0, le=500)
    altura: float | None = Field(default=None, gt=0, le=3)
    fc_pre_teste: int | None = Field(default=None, ge=20, le=250)
    fc_pos_teste: int | None = Field(default=None, ge=20, le=250)

    @model_validator(mode="after")
    def at_least_one_measurement(self):
        if all(value is None for value in self.model_dump().values()):
            raise ValueError("Informe ao menos uma medição.")
        return self

    
class AnalysisResponse(BaseModel):
    perfil: str
    destaque: str
    oportunidade: str
    mensagem: str


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
    