import pytest

from app.services.errors import VectorDimensionMismatchError, VectorIndexError
from app.services.vector_repository import SearchResult, VectorRepository


def test_create_and_store_and_search(tmp_engine):
    repo = VectorRepository(tmp_engine)
    assert repo.has_index() is False

    repo.ensure_index(3)
    assert repo.has_index() is True
    assert repo.index_dimension() == 3

    repo.save("a", [1.0, 0.0, 0.0])
    repo.save("b", [0.0, 1.0, 0.0])
    assert repo.count() == 2
    assert repo.has("a") is True
    assert repo.has("missing") is False

    # cosine distance, ascending: a is identical to the query
    results = repo.search([1.0, 0.0, 0.0], 5)
    assert results[0] == SearchResult(candidate_id="a", distance=0.0)
    assert results[1].candidate_id == "b"
    assert results[0].distance <= results[1].distance


def test_upsert_is_idempotent(tmp_engine):
    repo = VectorRepository(tmp_engine)
    repo.ensure_index(3)
    repo.save("a", [1.0, 0.0, 0.0])
    repo.save("a", [0.5, 0.5, 0.5])
    repo.save("b", [1.0, 0.0, 0.0])
    repo.save("b", [1.0, 0.0, 0.0])
    assert repo.count() == 2


def test_delete(tmp_engine):
    repo = VectorRepository(tmp_engine)
    repo.ensure_index(3)
    repo.save("a", [1.0, 0.0, 0.0])
    repo.delete("a")
    assert repo.has("a") is False
    assert repo.count() == 0


def test_search_empty_index_returns_empty(tmp_engine):
    repo = VectorRepository(tmp_engine)
    repo.ensure_index(3)
    assert repo.search([1.0, 0.0, 0.0], 5) == []


def test_search_without_index_raises(tmp_engine):
    repo = VectorRepository(tmp_engine)
    with pytest.raises(VectorIndexError, match="embed_candidates"):
        repo.search([1.0, 0.0, 0.0], 5)


def test_save_without_index_raises(tmp_engine):
    repo = VectorRepository(tmp_engine)
    with pytest.raises(VectorIndexError):
        repo.save("a", [1.0, 0.0, 0.0])


def test_wrong_dimension_insert_fails_clearly(tmp_engine):
    repo = VectorRepository(tmp_engine)
    repo.ensure_index(3)
    with pytest.raises(VectorDimensionMismatchError, match="dimension"):
        repo.save("bad", [1.0, 2.0])


def test_wrong_dimension_query_fails_clearly(tmp_engine):
    repo = VectorRepository(tmp_engine)
    repo.ensure_index(3)
    repo.save("a", [1.0, 0.0, 0.0])
    with pytest.raises(VectorDimensionMismatchError, match="dimension"):
        repo.search([1.0, 2.0], 5)


def test_existing_index_with_different_dimension_fails_clearly(tmp_engine):
    repo = VectorRepository(tmp_engine)
    repo.ensure_index(3)
    with pytest.raises(
        VectorDimensionMismatchError, match="dimension 3"
    ):
        repo.ensure_index(5)


def test_invalid_dimension_rejected(tmp_engine):
    repo = VectorRepository(tmp_engine)
    with pytest.raises(VectorIndexError, match="positive"):
        repo.ensure_index(0)


def test_drop_index(tmp_engine):
    repo = VectorRepository(tmp_engine)
    repo.ensure_index(3)
    repo.save("a", [1.0, 0.0, 0.0])
    repo.drop_index()
    assert repo.has_index() is False
    assert repo.count() == 0