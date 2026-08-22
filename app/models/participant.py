from pydantic import BaseModel, Field


class ParticipantIndicators(BaseModel):
	idade: int = Field(ge=1, le=120)
	imc: float = Field(gt=0, le=100)
	fc_repouso: int = Field(ge=20, le=250)
	atividade_score: float = Field(ge=0, le=100)
	resistencia_score: float = Field(ge=0, le=100)
	fc_score: float = Field(ge=0, le=100)
	habitos_score: float = Field(ge=0, le=100)
	indice_move: float = Field(ge=0, le=100)
