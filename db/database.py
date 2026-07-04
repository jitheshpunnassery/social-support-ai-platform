import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()


def _build_engine():
    """Try PostgreSQL first (production target); fall back to local SQLite
    so the prototype is runnable with zero infra for grading/demo purposes."""
    try:
        engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Connected to PostgreSQL at %s", settings.POSTGRES_HOST)
        return engine
    except Exception as e:  # noqa: BLE001
        logger.warning("PostgreSQL unavailable (%s) — falling back to local SQLite.", e)
        return create_engine(settings.SQLITE_FALLBACK_URL, connect_args={"check_same_thread": False})


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from db import models  # noqa: F401  (ensure models are registered)
    Base.metadata.create_all(bind=engine)
