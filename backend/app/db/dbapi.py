"""SQLite DB-API selection shared by the whole app.

SQLite loadable extensions - and therefore sqlite-vec - require
``Connection.enable_load_extension()``. That method only exists when CPython is
built with ``--enable-loadable-sqlite-extensions`` (which is OFF by default), so
several runtime images - including Render's Python 3.13 build - crash with::

    AttributeError: 'sqlite3.Connection' object has no attribute
    'enable_load_extension'

``pysqlite3`` is a drop-in, self-contained sqlite3 DB-API whose bundled SQLite
is compiled with extension loading enabled (and a much newer SQLite, which
sqlite-vec needs). We prefer it and fall back to the stdlib ``sqlite3`` module
when it is not installed yet (e.g. before ``pip install -r requirements.txt``),
so local development keeps working in both cases.
"""

import logging

logger = logging.getLogger(__name__)

try:
    from pysqlite3 import dbapi2 as _dbapi  # type: ignore[import-not-found]
    DRIVER = "pysqlite3"
except ImportError:
    import sqlite3 as _dbapi

    DRIVER = "stdlib sqlite3"

dbapi = _dbapi


def load_vec0_extension(connection) -> None:
    """Enable loadable extensions and register sqlite-vec on a raw DB-API
    connection.

    Must run for every connection before any vec0 query is attempted
    (SQLAlchemy hook: ``event.listen(engine, "connect", ...)``).
    """
    if not hasattr(connection, "enable_load_extension"):
        raise RuntimeError(
            "The active SQLite DB-API does not support loadable extensions "
            f"(driver: {DRIVER!r}). sqlite-vec cannot load. Install "
            "pysqlite3-binary (pip install pysqlite3-binary) or run a Python "
            "built with --enable-loadable-sqlite-extensions."
        )
    import sqlite_vec

    connection.enable_load_extension(True)
    sqlite_vec.load(connection)
    connection.enable_load_extension(False)