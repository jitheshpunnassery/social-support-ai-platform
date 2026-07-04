"""
Centralized configuration. Reads from .env (via python-dotenv) with sane
local-dev defaults so the prototype runs even when no external services
(Postgres/Mongo/Qdrant/Neo4j/Ollama) are reachable.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default)


class Settings:
    # Postgres
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

    # Mongo
    MONGO_URI = _get("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB = _get("MONGO_DB", "social_support_docs")

    # Qdrant
    QDRANT_HOST = _get("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(_get("QDRANT_PORT", "6333"))
    QDRANT_COLLECTION = _get("QDRANT_COLLECTION", "policy_precedents")

    # Neo4j
    NEO4J_URI = _get("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = _get("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = _get("NEO4J_PASSWORD", "neo4jpass")

    # Ollama (local LLM, OpenAI-compatible)
    OLLAMA_BASE_URL = _get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    OLLAMA_API_KEY = _get("OLLAMA_API_KEY", "ollama")
    OLLAMA_MODEL = _get("OLLAMA_MODEL", "llama3.1:8b-instruct-q4_K_M")
    OLLAMA_VISION_MODEL = _get("OLLAMA_VISION_MODEL", "llava:13b")

    # Langfuse
    LANGFUSE_PUBLIC_KEY = _get("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_SECRET_KEY = _get("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_HOST = _get("LANGFUSE_HOST", "http://localhost:3000")

    # App
    API_BASE_URL = _get("API_BASE_URL", "http://localhost:8000")
    AUTO_APPROVE_THRESHOLD = float(_get("AUTO_APPROVE_THRESHOLD", "0.80"))
    AUTO_DECLINE_THRESHOLD = float(_get("AUTO_DECLINE_THRESHOLD", "0.35"))

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    MODEL_PATH = os.path.join(BASE_DIR, "ml", "eligibility_model.pkl")


settings = Settings()
