"""Non-sensitive application dependency and provider health checks."""

from __future__ import annotations

from ai_provider import check_ai_provider_health, get_ai_provider_settings
from config import OLLAMA_HOST
from database import connect
from grounding_engine import SUPPORTED_BRANDS, build_grounding_context


def check_health(db_path=None, check_model: bool = True) -> dict[str, str]:
    settings = get_ai_provider_settings()
    result = {
        "database": "Unhealthy",
        "knowledge": "Unhealthy",
        "ai_provider": settings.provider,
        "configured_model": settings.model,
        "ai_model": "Not checked",
    }
    try:
        with connect(db_path) as db: db.execute("SELECT 1").fetchone()
        result["database"] = "Healthy"
    except Exception: pass
    try:
        for brand in SUPPORTED_BRANDS: build_grounding_context(brand)
        result["knowledge"] = "Healthy"
    except Exception: pass
    if check_model:
        result["ai_model"] = check_ai_provider_health(OLLAMA_HOST)
    return result
