"""
Centralized configuration. Reads from .env (via python-dotenv) with sane
local-dev defaults. Kept intentionally minimal in Phase 1 -- database, LLM,
and observability settings are appended in Phases 7, 8, and 10 respectively,
so this file grows alongside the features that need it.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default)


class Settings:
    # App
    API_BASE_URL = _get("API_BASE_URL", "http://localhost:8000")
    AUTO_APPROVE_THRESHOLD = float(_get("AUTO_APPROVE_THRESHOLD", "0.80"))
    AUTO_DECLINE_THRESHOLD = float(_get("AUTO_DECLINE_THRESHOLD", "0.35"))

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))


settings = Settings()
