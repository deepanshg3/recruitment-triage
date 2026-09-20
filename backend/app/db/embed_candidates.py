"""Generate and store candidate embeddings (explicit setup operation).

This is the ONLY place candidate embeddings are created. It is intentionally a
manual/setup script — the application never embeds candidates on startup, so no
external API calls are made just by running the service (cost/rate awareness).

Idempotent by design: candidate_id is the stable identity and embeddings are
upserted (DELETE + INSERT), so running it twice never duplicates vectors.

Usage:
    python -m app.db.embed_candidates                  # embed only missing candidates
    python -m app.db.embed_candidates --rebuild        # regenerate all, prune stale
    python -m app.db.embed_candidates --recreate-index # drop vec0 index, re-embed everything

The embedding dimension is resolved in this order:
  1. EMBEDDING_DIMENSION (configured in .env), else
  2. the dimension of an existing vec0 index, else
  3. detected from the first real Gemini response (index created with it).
A mismatch between the configured/index dimension and the model output is a hard
error: the application fails clearly instead of storing incompatible vectors.
"""

import argparse
import logging
import time
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal, engine, init_db
from app.models.candidate import Candidate
from app.services.candidate_document import build_candidate_document
from app.services.embedding_service import GeminiEmbeddingService
from app.services.errors import (
    EmbeddingApiError,
    EmbeddingConfigurationError,
    EmbeddingError,
)
from app.services.vector_repository import VectorRepository

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingRunSummary:
    embedded: int = 0
    skipped: int = 0
    failed: int = 0
    failures: list[tuple[str, str]] = field(default_factory=list)


def _embed_with_retry(
    embed_service: GeminiEmbeddingService,
    text: str,
    retries: int = 2,
    sleep_func=time.sleep,
) -> list[float]:
    """Embed `text`, retrying transient API failures a couple of times."""
    attempt = 0
    while True:
        try:
            return embed_service.embed(text)
        except EmbeddingApiError:
            attempt += 1
            if attempt > retries:
                raise
            sleep_func(1.0 * attempt)


def generate_candidate_embeddings(
    db: Session,
    *,
    engine_: Engine,
    embed_service: GeminiEmbeddingService,
    rebuild: bool = False,
    retries: int = 2,
    sleep_func=time.sleep,
) -> EmbeddingRunSummary:
    """Embed every candidate not already embedded (or all if `rebuild`).

    Partial failures are recorded per candidate and do not roll back the
    embeddings already stored. A total API outage at bootstrap (no index and
    first embed fails) aborts fast rather than hammering a dead endpoint.
    """
    repo = VectorRepository(engine_)
    summary = EmbeddingRunSummary()

    candidates = db.execute(
        select(Candidate).order_by(Candidate.id)
    ).scalars().all()
    if not candidates:
        return summary

    # Resolve the target dimension before the loop when we can.
    dim: int | None
    if settings.embedding_dimension is not None:
        dim = int(settings.embedding_dimension)
        repo.ensure_index(dim)
        embed_service.expected_dimension = dim
    else:
        dim = repo.index_dimension()
        if dim is not None:
            embed_service.expected_dimension = dim

    for candidate in candidates:
        if not rebuild and dim is not None and repo.has(candidate.id):
            summary.skipped += 1
            continue

        document = build_candidate_document(candidate)
        try:
            vector = _embed_with_retry(
                embed_service, document, retries=retries, sleep_func=sleep_func
            )
        except EmbeddingConfigurationError as exc:
            raise
        except EmbeddingApiError as exc:
            if dim is None:
                # Cannot bootstrap the index without a successful embed.
                raise
            summary.failed += 1
            summary.failures.append((candidate.id, str(exc)))
            continue
        except EmbeddingError as exc:
            summary.failed += 1
            summary.failures.append((candidate.id, str(exc)))
            continue

        if dim is None:
            dim = len(vector)
            repo.ensure_index(dim)
            embed_service.expected_dimension = dim
        elif len(vector) != dim:
            summary.failed += 1
            summary.failures.append(
                (
                    candidate.id,
                    f"embedding dimension {len(vector)} does not match index "
                    f"dimension {dim}; the embedding model changed. Re-run with "
                    "--recreate-index after confirming the model.",
                )
            )
            continue

        repo.save(candidate.id, vector)
        summary.embedded += 1

    if rebuild:
        repo.prune({c.id for c in candidates})

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Regenerate embeddings for every candidate and prune stale ones.",
    )
    parser.add_argument(
        "--recreate-index",
        action="store_true",
        help="Drop the vec0 index first, then embed every candidate from scratch.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    try:
        embed_service = GeminiEmbeddingService()
        embed_service.check_configured()
    except EmbeddingConfigurationError as exc:
        logging.error("%s", exc)
        raise SystemExit(1)

    init_db()
    if args.recreate_index:
        VectorRepository(engine).drop_index()

    db = SessionLocal()
    try:
        summary = generate_candidate_embeddings(
            db, engine_=engine, embed_service=embed_service, rebuild=args.rebuild
        )
    except EmbeddingConfigurationError as exc:
        logging.error("%s", exc)
        raise SystemExit(1)
    except EmbeddingError as exc:
        logging.error("Embedding run aborted: %s", exc)
        raise SystemExit(1)
    finally:
        db.close()

    print(f"Embedded: {summary.embedded}")
    print(f"Skipped:  {summary.skipped}")
    print(f"Failed:   {summary.failed}")
    for candidate_id, reason in summary.failures:
        print(f"  - {candidate_id}: {reason}")

    if summary.failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()