"""Job-description retrieval: JD text -> embedding -> vec0 KNN -> top-K candidates.

Terminology is intentionally precise: sqlite-vec returns a DISTANCE (cosine
distance with `distance_metric=cosine`, i.e. 1 - cosine similarity). Lower is
more similar. We do NOT relabel it as similarity or invent percentages.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.services.embedding_service import GeminiEmbeddingService
from app.services.errors import RetrievalInputError, VectorIndexError
from app.services.vector_repository import VectorRepository

DEFAULT_TOP_K = 5


@dataclass
class RankedCandidate:
    candidate: Candidate
    distance: float


def _validate_input(job_description: str, top_k: int) -> None:
    if not job_description or not job_description.strip():
        raise RetrievalInputError("Job description must not be empty.")
    if not isinstance(top_k, int) or isinstance(top_k, bool):
        raise RetrievalInputError(f"top_k must be an integer, got {top_k!r}.")
    if top_k < 1:
        raise RetrievalInputError(
            f"top_k must be a positive integer, got {top_k}."
        )


def search_candidates(
    db: Session,
    *,
    engine: Engine,
    embed_service: GeminiEmbeddingService,
    job_description: str,
    top_k: int = DEFAULT_TOP_K,
) -> list[RankedCandidate]:
    """Return the top-K candidates for a JD, ranked by cosine distance (asc).

    - Empty/whitespace-only JD -> RetrievalInputError
    - top_k <= 0 -> RetrievalInputError
    - top_k > indexed count -> capped to the number of indexed candidates
    - no embeddings yet -> VectorIndexError with a hint to run embed_candidates
    - candidate deleted after its embedding was stored -> embedding is ignored
    """
    _validate_input(job_description, top_k)

    repo = VectorRepository(engine)
    indexed = repo.count()
    if indexed == 0:
        raise VectorIndexError(
            "No candidate embeddings are indexed. Run "
            "`python -m app.db.embed_candidates` first."
        )

    effective_k = min(top_k, indexed)
    query_vector = embed_service.embed(job_description)

    results = repo.search(query_vector, effective_k)

    ids = [r.candidate_id for r in results]
    candidates = {
        c.id: c
        for c in db.execute(
            select(Candidate).where(Candidate.id.in_(ids))
        ).scalars().all()
        if c.id in ids
    }
    return [
        RankedCandidate(candidate=candidates[r.candidate_id], distance=r.distance)
        for r in results
        if r.candidate_id in candidates
    ]