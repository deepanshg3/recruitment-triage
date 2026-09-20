import sqlite_vec
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.candidate import Candidate
from app.services.errors import EmbeddingResponseError


def register_vec_extension(engine) -> None:
    """Attach the sqlite-vec extension loader to a test engine."""

    @event.listens_for(engine, "connect")
    def _load(dbapi_connection, _record) -> None:
        dbapi_connection.enable_load_extension(True)
        sqlite_vec.load(dbapi_connection)
        dbapi_connection.enable_load_extension(False)


@pytest.fixture
def tmp_engine(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    register_vec_extension(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def candidate_factory():
    def make(**overrides):
        from datetime import date

        base = dict(
            id="cand_001",
            name="Ada Lovelace",
            target_role="Backend Engineer",
            years_experience=4,
            source="Naukri",
            skills=["Python", "SQL", "FastAPI"],
            notes="Strong backend background; shipped several production APIs.",
            applied_date=date(2026, 9, 1),
            is_shortlisted=False,
        )
        base.update(overrides)
        return Candidate(**base)

    return make


@pytest.fixture
def job_description():
    return (
        "Backend Engineer - Build production REST APIs with Python and FastAPI, "
        "own PostgreSQL schema design, require 2+ years of experience, "
        "comfortable with Docker and working in a startup."
    )


@pytest.fixture
def seeded_db(tmp_engine, candidate_factory):
    """Session with the candidates table created, ready for vector tests."""
    Base.metadata.create_all(tmp_engine)
    Session = sessionmaker(bind=tmp_engine)
    return Session()


@pytest.fixture
def fake_embedder():
    """Deterministic embedder that never touches the network."""

    class FakeEmbedder:
        def __init__(self, dim=4, fail_on=()):
            self.dim = dim
            self.fail_on = tuple(fail_on)
            self.expected_dimension = None
            self.calls = []

        def embed(self, text: str):
            self.calls.append(text)
            for marker in self.fail_on:
                if marker in text:
                    raise EmbeddingResponseError(
                        f"simulated embedding failure ({marker})"
                    )
            return [0.01 * (i + 1) for i in range(self.dim)]

    return FakeEmbedder()


@pytest.fixture
def api_candidates(candidate_factory):
    """Deterministic candidate set used by REST API tests."""
    from datetime import date

    return [
        candidate_factory(
            id="cand_a",
            name="Alice",
            target_role="Backend Engineer",
            years_experience=5,
            source="Naukri",
            skills=["Python", "FastAPI", "Docker"],
            notes="Built production APIs at a startup.",
            applied_date=date(2026, 9, 1),
            is_shortlisted=True,
        ),
        candidate_factory(
            id="cand_b",
            name="bob",
            target_role="Frontend Engineer",
            years_experience=2,
            source="LinkedIn",
            skills=["JavaScript", "React"],
            notes="Builds React dashboards.",
            applied_date=date(2025, 1, 15),
            is_shortlisted=False,
        ),
        candidate_factory(
            id="cand_c",
            name="Carol",
            target_role="Backend Engineer",
            years_experience=8,
            source="Naukri",
            skills=["Python", "PostgreSQL"],
            notes="Deep backend ops experience.",
            applied_date=date(2026, 8, 20),
            is_shortlisted=False,
        ),
        candidate_factory(
            id="cand_d",
            name="Dave",
            target_role="Data Engineer",
            years_experience=3,
            source="AngelList",
            skills=["Python", "Spark", "SQL"],
            notes="Builds data pipelines.",
            applied_date=date(2024, 6, 5),
            is_shortlisted=False,
        ),
        candidate_factory(
            id="cand_e",
            name="Erika",
            target_role="Backend Engineer",
            years_experience=2,
            source="Naukri",
            skills=["Python", "FastAPI"],
            notes="Shipped a few small services.",
            applied_date=date(2026, 7, 10),
            is_shortlisted=False,
        ),
    ]


@pytest.fixture
def api_client(tmp_engine, api_candidates):
    """TestClient with `get_db` overridden to a fresh seeded temp database."""
    from fastapi.testclient import TestClient

    from app.db.database import Base, get_db
    from app.main import app

    Base.metadata.create_all(tmp_engine)
    Session = sessionmaker(bind=tmp_engine)
    with Session() as seed_session:
        seed_session.add_all(api_candidates)
        seed_session.commit()

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()