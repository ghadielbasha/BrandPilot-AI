"""Environment-backed BrandPilot configuration."""

from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ENVIRONMENT = os.getenv("BRANDPILOT_ENV", "development")
DB_PATH = Path(os.getenv("BRANDPILOT_DB_PATH", str(BASE_DIR / "data" / "brandpilot.db")))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
MODEL_NAME = os.getenv("BRANDPILOT_MODEL", "qwen3:4b")
KNOWLEDGE_DIR = BASE_DIR / "knowledge"

