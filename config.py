"""Environment-backed BrandPilot configuration."""

from __future__ import annotations

import os
from pathlib import Path

from ai_provider import get_ai_provider_settings


BASE_DIR = Path(__file__).resolve().parent
ENVIRONMENT = os.getenv("BRANDPILOT_ENV", "development")
DB_PATH = Path(os.getenv("BRANDPILOT_DB_PATH", str(BASE_DIR / "data" / "brandpilot.db")))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
AI_SETTINGS = get_ai_provider_settings()
AI_PROVIDER = AI_SETTINGS.provider
MODEL_NAME = AI_SETTINGS.model
KNOWLEDGE_DIR = BASE_DIR / "knowledge"

