import pytest

from app.db.database import Base
from app.services.errors import RetrievalInputError, VectorIndexError
from app.services.retrieval import search_candidates
from app.services.vector_repository import VectorRepository


class StubEmbedder:
    def __init__(self, vector):
        self._vector = list(vector)
        self.expected_dimension = None

    def embed(self, text):
        return list(self._vector)


def _seed(tmp_engine, session, candidates, vectors):
    Base.metadata.create_all(tmp_engine)
    for c in candidates:
        session.add(c)
    session.commit()

    repo = VectorRepository(tmp_engine)
    repo.ensure_index(3)
    for candidate_id, vector in vectors:
        repo.save(candidate_id, vector)
    return repo


def test_a_ranks_above_b_when_closer(tmp_engine, seeded_db, candidate_factory):
    a = candidate_factory(id="cand_a", name="Ann", target_role="Backend")
    b = candidate_factory(id="cand_b", name="Bob", target_role="Frontend")
    _seed(tmp_engine, seeded_db, [a, b], [("cand_a", [1.0, 0.0, 0.0]), ("cand_b", [0.0, 1.0, 0.0])])

    results = search_candidates(
        seeded_db,
        engine=tmp_engine,
        embed_service=StubEmbedder([1.0, 0.0, 0.0]),
        job_description="backend systems work",
        top_k=5,
    )
    assert [r.candidate.id for r in results] == ["cand_a", "cand_b"]
    assert results[0].distance <= results[1].distance


def test_top_k_limits_results(tmp_engine, seeded_db, candidate_factory):
    candidates = [
        candidate_factory(id=f"cand_{i}", name=f"N{i}", target_role="R")
        for i in range(3)
    ]
    vectors = [(f"cand_{i}", [1.0, i, 0.0]) for i in range(3)]
    _seed(tmp_engine, seeded_db, candidates, vectors)

    results = search_candidates(
        seeded_db,
        engine=tmp_engine,
        embed_service=StubEmbedder([1.0, 0.0, 0.0]),
        job_description="some JD",
        top_k=1,
    )
    assert len(results) == 1


def test_top_k_greater_than_indexed_returns_all(tmp_engine, seeded_db, candidate_factory):
    candidates = [
        candidate_factory(id=f"cand_{i}", name=f"N{i}", target_role="R")
        for i in range(2)
    ]
    _seed(
        tmp_engine,
        seeded_db,
        candidates,
        [("cand_0", [1.0, 0.0, 0.0]), ("cand_1", [0.0, 1.0, 0.0])],
    )

    results = search_candidates(
        seeded_db,
        engine=tmp_engine,
        embed_service=StubEmbedder([1.0, 0.0, 0.0]),
        job_description="JD",
        top_k=50,
    )
    assert len(results) == 2


@pytest.mark.parametrize("bad_k", [0, -1])
def test_top_k_must_be_positive(tmp_engine, seeded_db, candidate_factory, bad_k):
    c = candidate_factory(id="cand_a", name="A", target_role="R")
    _seed(tmp_engine, seeded_db, [c], [("cand_a", [1.0, 0.0, 0.0])])
    with pytest.raises(RetrievalInputError, match="positive"):
        search_candidates(
            seeded_db,
            engine=tmp_engine,
            embed_service=StubEmbedder([1.0, 0.0, 0.0]),
            job_description="JD",
            top_k=bad_k,
        )


@pytest.mark.parametrize("jd", ["", "   \n\t  "])
def test_empty_job_description_rejected(tmp_engine, seeded_db, jd):
    with pytest.raises(RetrievalInputError, match="empty"):
        search_candidates(
            seeded_db,
            engine=tmp_engine,
            embed_service=StubEmbedder([1.0, 0.0, 0.0]),
            job_description=jd,
        )


def test_no_embeddings_raises(tmp_engine, seeded_db, candidate_factory):
    Base.metadata.create_all(tmp_engine)
    seeded_db.add(candidate_factory(id="cand_a", name="A", target_role="R"))
    seeded_db.commit()

    with pytest.raises(VectorIndexError, match="embed_candidates"):
        search_candidates(
            seeded_db,
            engine=tmp_engine,
            embed_service=StubEmbedder([1.0, 0.0, 0.0]),
            job_description="JD",
        )


def test_candidate_deleted_after_embedding_is_ignored(
    tmp_engine, seeded_db, candidate_factory
):
    a = candidate_factory(id="cand_a", name="A", target_role="R")
    _seed(
        tmp_engine,
        seeded_db,
        [a],
        [("cand_a", [1.0, 0.0, 0.0]), ("ghost_candidate", [0.0, 0.0, 1.0])],
    )
    results = search_candidates(
        seeded_db,
        engine=tmp_engine,
        embed_service=StubEmbedder([1.0, 0.0, 0.0]),
        job_description="JD",
        top_k=5,
    )
    assert [r.candidate.id for r in results] == ["cand_a"]