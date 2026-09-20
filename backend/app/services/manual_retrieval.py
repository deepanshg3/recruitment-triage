"""Developer-only manual retrieval check (NOT a REST endpoint).

Usage (from backend/):
    python -m app.services.manual_retrieval "job description text..." [top_k]

Embeds the JD via Gemini and prints the top-K candidates by cosine distance.
Requires candidates to have been embedded first (see app/db/embed_candidates.py).
"""

import argparse
import logging
import sys

from app.db.database import SessionLocal, engine, init_db
from app.services.embedding_service import GeminiEmbeddingService
from app.services.errors import (
    EmbeddingConfigurationError,
    EmbeddingError,
    VectorIndexError,
)
from app.services.retrieval import DEFAULT_TOP_K, search_candidates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_description", nargs="?", help="Sample job description")
    parser.add_argument("top_k", type=int, nargs="?", default=DEFAULT_TOP_K)
    args = parser.parse_args()

    if not args.job_description:
        print("Usage: python -m app.services.manual_retrieval \"<JD text>\" [top_k]")
        sys.exit(2)

    logging.basicConfig(level=logging.WARNING)
    init_db()

    embed_service = GeminiEmbeddingService()
    db = SessionLocal()
    try:
        results = search_candidates(
            db,
            engine=engine,
            embed_service=embed_service,
            job_description=args.job_description,
            top_k=args.top_k,
        )
    except EmbeddingConfigurationError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    except VectorIndexError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    except EmbeddingError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    finally:
        db.close()

    print(f"JD:\n{args.job_description}\n")
    print("Retrieved candidates:")
    for index, item in enumerate(results, start=1):
        c = item.candidate
        print(
            f"{index}. {c.id} - {c.name} - distance: {item.distance:.4f}"
        )


if __name__ == "__main__":
    main()