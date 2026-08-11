"""SQLAlchemy engine / session management for SQLite."""

from __future__ import annotations

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import PROJECT_ROOT, get_settings

settings = get_settings()


def _resolve_sqlite_url(url: str) -> str:
    """Resolve relative sqlite paths against the project root so the app works
    regardless of the process working directory."""
    if url.startswith("sqlite:///"):
        raw = url[len("sqlite:///"):]
        if raw and raw != ":memory:" and not Path(raw).is_absolute():
            abs_path = PROJECT_ROOT / raw
            return f"sqlite:///{abs_path.as_posix()}"
    return url


DATABASE_URL = _resolve_sqlite_url(settings.database_url)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # noqa: ANN001
    """Enable foreign keys and WAL for SQLite."""
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Imported models must be registered first."""
    from app.db import models  # noqa: F401  (registers ORM models on Base)

    Base.metadata.create_all(bind=engine)
