"""Tests for the SQLite + sqlite-vec runtime preflight (Render deployment fix).

These assert the whole chain that broke on Render: a SQLite DB-API that exposes
loadable-extension support, sqlite-vec loading, vec0 (KNN) usability, and the
application engine connecting through the same DB-API.
"""

from sqlalchemy import create_engine

from app.db.dbapi import dbapi
from app.db.database import engine, register_vec_extension
from app.db.preflight import run_preflight
from app.services.vector_repository import VectorRepository

EXPECTED_REPORT_KEYS = {
    "dbapi",
    "extension_loading",
    "sqlite_vec",
    "vec0",
    "sqlalchemy",
}


def test_selected_dbapi_exposes_loadable_extensions():
    connection = dbapi.connect(":memory:")
    try:
        assert hasattr(connection, "enable_load_extension")
    finally:
        connection.close()


def test_run_preflight_passes():
    report = run_preflight()
    assert set(report) == EXPECTED_REPORT_KEYS
    assert report["extension_loading"] == "available"
    assert report["sqlite_vec"].startswith("v")
    assert "cosine KNN round trip" in report["vec0"]


def test_production_engine_connects(tmp_path):
    """The exact engine object used by the app must open a connection."""
    with engine.connect() as conn:
        version = conn.exec_driver_sql("select sqlite_version()").scalar_one()
    assert isinstance(version, str) and version


def test_engine_with_vec_extension_supports_knn(tmp_path):
    """A fresh engine created exactly like the app's supports vec0 KNN."""
    test_engine = create_engine(
        f"sqlite:///{tmp_path / 'vec.db'}",
        module=dbapi,
        connect_args={"check_same_thread": False},
    )
    register_vec_extension(test_engine)
    try:
        repo = VectorRepository(test_engine)
        repo.ensure_index(3)
        repo.save("a", [1.0, 0.0, 0.0])
        results = repo.search([1.0, 0.0, 0.0], 5)
        assert results[0].candidate_id == "a"
        assert results[0].distance == 0.0
    finally:
        test_engine.dispose()