"""Non-sensitive application dependency health checks."""

from __future__ import annotations

import json
import urllib.request

from config import MODEL_NAME, OLLAMA_HOST
from database import connect
from grounding_engine import SUPPORTED_BRANDS, build_grounding_context


def check_health(db_path=None, check_model: bool = True) -> dict[str, str]:
    result = {"database": "Unhealthy", "knowledge": "Unhealthy", "ai_model": "Not checked"}
    try:
        with connect(db_path) as db: db.execute("SELECT 1").fetchone()
        result["database"] = "Healthy"
    except Exception: pass
    try:
        for brand in SUPPORTED_BRANDS: build_grounding_context(brand)
        result["knowledge"] = "Healthy"
    except Exception: pass
    if check_model:
        try:
            with urllib.request.urlopen(f"{OLLAMA_HOST.rstrip('/')}/api/tags", timeout=3) as response:
                models = json.load(response).get("models", [])
            result["ai_model"] = "Healthy" if any(item.get("name", "").split(":")[0] == MODEL_NAME.split(":")[0] for item in models) else "Model unavailable"
        except Exception:
            result["ai_model"] = "Unreachable"
    return result
