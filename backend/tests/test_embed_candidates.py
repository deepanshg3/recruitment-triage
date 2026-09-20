from app.db.database import Base
from app.db.embed_candidates import generate_candidate_embeddings
from app.services.vector_repository import VectorRepository


def _seed_candidates(session, candidate_factory, count=3):
    for i in range(count):
        session.add(
            candidate_factory(
                id=f"cand_{i:03d}",
                name=f"Engineer {i}",
                target_role="Backend Engineer",
                skills=["Python", "FastAPI"],
                notes="Solid backend experience.",
            )
        )
    session.commit()


def _run(session, engine, embedder, **kwargs):
    return generate_candidate_embeddings(
        session, engine_=engine, embed_service=embedder, **kwargs
    )


def test_running_twice_creates_no_duplicates(tmp_engine, seeded_db, candidate_factory, fake_embedder):
    _seed_candidates(seeded_db, candidate_factory)
    repo = VectorRepository(tmp_engine)

    first = _run(seeded_db, tmp_engine, fake_embedder)
    assert first.embedded == 3
    assert first.failed == 0
    assert repo.count() == 3

    second = _run(seeded_db, tmp_engine, fake_embedder)
    assert second.skipped == 3
    assert second.embedded == 0
    assert repo.count() == 3  # still 3, no duplicates


def test_partial_failure_keeps_successes(tmp_engine, seeded_db, candidate_factory, fake_embedder):
    _seed_candidates(seeded_db, candidate_factory)
    fake_embedder.fail_on = ["Name: Engineer 1"]
    repo = VectorRepository(tmp_engine)

    summary = _run(seeded_db, tmp_engine, fake_embedder)
    assert summary.embedded == 2
    assert summary.failed == 1
    assert repo.count() == 2
    assert summary.failures[0][0] == "cand_001"
    assert "simulated embedding failure" in summary.failures[0][1]


def test_skips_candidates_that_already_have_embeddings(tmp_engine, seeded_db, candidate_factory, fake_embedder):
    _seed_candidates(seeded_db, candidate_factory)
    repo = VectorRepository(tmp_engine)
    repo.ensure_index(4)
    repo.save("cand_000", [0.1, 0.2, 0.3, 0.4])

    summary = _run(seeded_db, tmp_engine, fake_embedder)
    assert summary.skipped == 1  # cand_000 already embedded
    assert summary.embedded == 2
    assert repo.count() == 3


def test_rebuild_regenerates_all(tmp_engine, seeded_db, candidate_factory, fake_embedder):
    _seed_candidates(seeded_db, candidate_factory)
    repo = VectorRepository(tmp_engine)
    _run(seeded_db, tmp_engine, fake_embedder)
    fake_embedder.calls.clear()

    summary = _run(seeded_db, tmp_engine, fake_embedder, rebuild=True)
    assert summary.skipped == 0
    assert summary.embedded == 3
    assert len(fake_embedder.calls) == 3  # every candidate re-embedded
    assert repo.count() == 3


def test_rebuild_prunes_stale_embeddings(tmp_engine, seeded_db, candidate_factory, fake_embedder):
    _seed_candidates(seeded_db, candidate_factory)
    repo = VectorRepository(tmp_engine)
    _run(seeded_db, tmp_engine, fake_embedder)
    repo.save("deleted_candidate", [0.9, 0.9, 0.9, 0.9])
    assert repo.count() == 4

    _run(seeded_db, tmp_engine, fake_embedder, rebuild=True)
    assert repo.count() == 3
    assert repo.has("deleted_candidate") is False