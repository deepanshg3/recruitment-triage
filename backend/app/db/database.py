from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

import sqlite_vec

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def register_vec_extension(engine: object) -> None:
    """Load the sqlite-vec extension on every new DB connection.

    sqlite-vec ships as a loadable C extension (an `ENABLE_LOAD_EXTENSION`
    build of the stdlib sqlite3 module is required). SQLAlchemy opens its own
    sqlite3 connections, so we hook the extension load into each new connection.
    """

    def _load(dbapi_connection, _record) -> None:
        dbapi_connection.enable_load_extension(True)
        sqlite_vec.load(dbapi_connection)
        dbapi_connection.enable_load_extension(False)

    event.listen(engine, "connect", _load)


register_vec_extension(engine)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db() -> Session:
    """FastAPI dependency that yields a session and closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables if they do not already exist."""
    # Import models so they are registered on Base.metadata before create_all.
    from app.models.candidate import Candidate  # noqa: F401

    Base.metadata.create_all(bind=engine)