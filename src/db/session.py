"""
SQLAlchemy engine/session factory for the Python backend.

Replaces the hand-rolled psycopg2 connection pool in the old
core/profile_manager.py. One engine per process, pooled connections,
sessions handed out per-request via FastAPI's dependency system.
"""

import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from src.core.config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # avoids handing out dead connections after e.g. DB restarts
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def get_db():
    """FastAPI dependency: yields a session, always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    """Context manager for use outside FastAPI (scripts, tests). Commits on
    success, rolls back and re-raises on any exception — no silent partial
    writes."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@event.listens_for(engine, "connect")
def _log_connect(dbapi_connection, connection_record):  # pragma: no cover - logging only
    logger.debug("New DB connection established")
