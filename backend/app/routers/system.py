from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["System"])
settings = get_settings()


@router.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "llm": settings.llm_enabled}


@router.get("/ping")
def ping():
    """Tiny endpoint for uptime monitors / frontend keep-alive (keeps Render free tier awake)."""
    return {"pong": True}
