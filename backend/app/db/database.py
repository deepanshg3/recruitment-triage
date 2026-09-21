from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings
from app.db.dbapi import dbapi, load_vec0_extension

# SQLAlchemy is told to use pysqlite3 instead of the stdlib sqlite3 module:
# the stdlib module as built on Render (Python 3.13) exposes no
# enable_load_extension(), so sqlite-vec could never load there. pysqlite3
# bundles a self-contained SQLite with loadable-extension support enabled.
# On machines without pysqlite3 the app falls back to stdlib sqlite3, so local
# development keeps working either way (see app/db/dbapi.py).
engine = create_engine(
    settings.database_url,
    module=dbapi,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def register_vec_extension(engine: object) -> None:
    """Load the sqlite-vec extension on every new DB connection.

    sqlite-vec ships as a loadable C extension, so the SQLite runtime must
    support loadable extensions. SQLAlchemy opens its own connections, so we
    hook the extension load into each new connection.
    """

    def _load(dbapi_connection, _record) -> None:
        load_vec0_extension(dbapi_connection)

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