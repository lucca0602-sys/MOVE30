from fastapi import APIRouter

router = APIRouter(prefix="/public", tags=["público"])


@router.get("/health")
def health():
    return {"status": "ok"}
