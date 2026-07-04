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
    MODEL_PATH = os.path.join(BASE_DIR, "ml", "eligibility_model.pkl")  # Phase 4

    # --- Phase 7: PostgreSQL + MongoDB ---
    POSTGRES_HOST = _get("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = _get("POSTGRES_PORT", "5432")
    POSTGRES_DB = _get("POSTGRES_DB", "social_support")
    POSTGRES_USER = _get("POSTGRES_USER", "ssuser")
    POSTGRES_PASSWORD = _get("POSTGRES_PASSWORD", "sspass")

    @property
    def POSTGRES_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    SQLITE_FALLBACK_URL = "sqlite:///./local.db"

    MONGO_URI = _get("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB = _get("MONGO_DB", "social_support_docs")


settings = Settings()
