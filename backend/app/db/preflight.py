"""Runtime preflight: prove SQLite + sqlite-vec work before serving.

Why this exists
---------------
sqlite-vec is a loadable C extension, so it needs a SQLite runtime that supports
loadable extensions. The stdlib ``sqlite3`` module only exposes
``Connection.enable_load_extension()`` when CPython is built with
``--enable-loadable-sqlite-extensions`` (off by default and absent in Render's
Python 3.13 image). The app therefore drives SQLAlchemy with ``pysqlite3`` (see
app/db/dbapi.py). This module verifies the whole chain at startup on an
in-memory database - no writes to the real database:

    DB-API connection -> enable_load_extension -> sqlite-vec -> vec0 KNN

Run manually from the backend/ directory::

    python -m app.db.preflight
"""

import logging
import uuid

import sqlite_vec
from sqlalchemy import create_engine

from app.db.dbapi import dbapi

logger = logging.getLogger(__name__)


class PreflightError(RuntimeError):
    """Raised when the SQLite + sqlite-vec runtime capability check fails."""


def run_preflight() -> dict[str, str]:
    """Run every preflight check; raise PreflightError on the first failure.

    Returns a small dict of label -> human-readable result on success.
    """
    report: dict[str, str] = {}

    def require(ok: bool, message: str) -> None:
        if not ok:
            raise PreflightError(message)

    connection = dbapi.connect(":memory:")
    try:
        # 1. The selected DB-API must support loadable extensions.
        require(
            hasattr(connection, "enable_load_extension"),
            "The active SQLite DB-API has no Connection.enable_load_extension. "
            "sqlite-vec is a loadable C extension and cannot load. Install "
            "pysqlite3-binary (it is in requirements.txt) or run a Python built "
            f"with --enable-loadable-sqlite-extensions. Active driver: {dbapi!r}.",
        )

        # 2. sqlite-vec must actually load and expose vec_version().
        try:
            connection.enable_load_extension(True)
            sqlite_vec.load(connection)
            vec_version = connection.execute("select vec_version()").fetchone()[0]
            vector = sqlite_vec.serialize_float32([1.0, 0.0, 0.0])
        finally:
            connection.enable_load_extension(False)
        report["dbapi"] = f"{dbapi.__name__} (bundled SQLite {dbapi.sqlite_version})"
        report["extension_loading"] = "available"
        report["sqlite_vec"] = str(vec_version)

        # 3. vec0 (virtual table + cosine KNN) round trip.
        table = f"preflight_vec0_{uuid.uuid4().hex[:8]}"
        connection.execute(
            f"create virtual table {table} using vec0("
            "candidate_id text primary key, embedding float[3] "
            "distance_metric=cosine)"
        )
        connection.execute(
            f"insert into {table}(candidate_id, embedding) values ('a', ?)",
            (vector,),
        )
        row = connection.execute(
            f"select candidate_id, distance from {table} "
            "where embedding match ? and k = 3 order by distance",
            (vector,),
        ).fetchone()
        require(
            row is not None and row[1] == 0.0,
            f"vec0 KNN round trip failed: expected a match at distance 0.0, "
            f"got {row!r}.",
        )
        report["vec0"] = "usable (cosine KNN round trip, distance 0.0)"
    finally:
        connection.close()

    # 4. SQLAlchemy must connect through the same DB-API the app uses.
    engine = create_engine("sqlite://", module=dbapi)
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("select 1").scalar_one()
        report["sqlalchemy"] = (
            f"connection OK (in-memory, module={dbapi.__name__})"
        )
    finally:
        engine.dispose()

    return report


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    try:
        report = run_preflight()
    except Exception as exc:
        logger.error("Preflight FAILED: %s", exc)
        return 1
    logger.info("Preflight passed: SQLite + sqlite-vec (vec0) are functional.")
    for key, value in report.items():
        logger.info("  %-18s %s", key + ":", value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())