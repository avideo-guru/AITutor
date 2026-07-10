from fastapi import APIRouter

from ..config import settings

router = APIRouter()


@router.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "llm_provider": settings.llm_provider}
