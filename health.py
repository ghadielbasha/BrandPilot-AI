"""Non-sensitive application dependency and provider health checks."""

from __future__ import annotations

from datetime import datetime, timezone

from ai_provider import check_ai_provider_health, get_ai_provider_settings
from config import OLLAMA_HOST
from database import connect
from grounding_engine import SUPPORTED_BRANDS, build_grounding_context


def check_health(db_path=None, check_model: bool = True) -> dict[str, str]:
    settings = get_ai_provider_settings()
    result = {
        "database": "Unhealthy",
        "knowledge": "Unhealthy",
        "provider": settings.provider,
        "model": settings.model,
        "provider_status": "Not checked",
        "last_probe_time": None,
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
        result["provider_status"] = check_ai_provider_health(OLLAMA_HOST)
        result["last_probe_time"] = datetime.now(timezone.utc).isoformat()
    return result
