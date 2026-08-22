from fastapi import APIRouter

from app.models.participant import ParticipantIndicators


router = APIRouter()


@router.post("/analyze")
def analyze_indicators(indicators: ParticipantIndicators) -> dict:
	return {
		"status": "received",
		"indicators": indicators.model_dump(),
	}
