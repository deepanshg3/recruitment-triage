"""High-level orchestration: JD -> retrieval (vec0) -> LLM screening.

This is the only place that *composes* the two services. It itself performs no
vector math and no LLM calls of its own:

  1. embed the JD once and run the existing vec0 `search_candidates` (top-K)
  2. screen the retrieved candidates with the LLM service

Distance and screening stay semantically separate: cosine distance (lower =
more similar) is a retrieval signal only and is never converted into a match
percentage, score, or confidence, and is never sent to the LLM.

Cost: 1 JD embedding call + K LLM calls for K screened candidates (default
top_k=5 => 1 + 5 LLM calls for screening; embedding is a separate API call).
"""

from dataclasses import dataclass

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.errors import ScreeningInputError
from app.services.llm_client import GeminiLLMClient
from app.services.retrieval import (
    DEFAULT_TOP_K,
    RankedCandidate,
    search_candidates,
)
from app.services.screening_service import (
    ScreeningOutcome,
    ScreeningService,
)
from app.services.embedding_service import GeminiEmbeddingService


@dataclass
class MatchAndScreenResult:
    """Result of one match-and-screen run."""

    job_description: str
    top_k_requested: int
    retrieved: list[RankedCandidate]
    outcomes: list[ScreeningOutcome]


def _validate_input(job_description: str, top_k: int) -> None:
    if not job_description or not job_description.strip():
        raise ScreeningInputError("Job description must not be empty.")
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        raise ScreeningInputError(
            f"top_k must be a positive integer, got {top_k!r}."
        )


def match_and_screen_candidates(
    db: Session,
    *,
    engine: Engine,
    embed_service: GeminiEmbeddingService,
    llm_client: GeminiLLMClient,
    job_description: str,
    top_k: int = DEFAULT_TOP_K,
) -> MatchAndScreenResult:
    """Retrieve the top-K candidates for a JD and screen each with the LLM.

    Retrieval errors (e.g. no embeddings indexed) propagate. Each candidate's
    screening is handled by the batch semantics of ScreeningService: one
    explicit outcome per candidate, order preserved, failures never faked.
    """
    _validate_input(job_description, top_k)

    screening_service = ScreeningService(llm_client)

    ranked = search_candidates(
        db,
        engine=engine,
        embed_service=embed_service,
        job_description=job_description.strip(),
        top_k=top_k,
    )

    candidates = [rc.candidate for rc in ranked]
    outcomes = screening_service.screen_candidates(
        job_description=job_description.strip(), candidates=candidates
    )

    return MatchAndScreenResult(
        job_description=job_description.strip(),
        top_k_requested=top_k,
        retrieved=ranked,
        outcomes=outcomes,
    )


def main(*, api_key: str | None = None) -> None:
    """CLI entry point (`python -m app.services.orchestration`)."""
    import argparse
    import sys

    from app.db.database import SessionLocal, init_db, engine as db_engine
    from app.services.embedding_service import GeminiEmbeddingService

    parser = argparse.ArgumentParser(
        description=(
            "Match a job description against indexed candidates and LLM-screen "
            "the top-K. NOTE: requires a configured GEMINI_API_KEY."
        )
    )
    parser.add_argument("-j", "--jd", required=True, help="Job description text (or file path if prefixed with '@')")
    parser.add_argument(
        "-k", "--top-k", type=int, default=DEFAULT_TOP_K, help="Number of candidates to screen"
    )
    args = parser.parse_args()

    if api_key is None:
        api_key = settings.gemini_api_key
    if not api_key:
        print(
            "ERROR: GEMINI_API_KEY is not configured. Add it to the .env file "
            "and re-run.",
            file=sys.stderr,
        )
        sys.exit(1)

    jd = args.jd
    if jd.startswith("@"):
        import pathlib

        jd = pathlib.Path(jd[1:]).read_text().strip()

    init_db()
    embed_service = GeminiEmbeddingService()
    llm_client = GeminiLLMClient(api_key=api_key)

    with SessionLocal() as db:
        result = match_and_screen_candidates(
            db,
            engine=db_engine,
            embed_service=embed_service,
            llm_client=llm_client,
            job_description=jd,
            top_k=args.top_k,
        )

    print(f"\nTop-{args.top_k} screening for job description:")
    print(f"  {jd[:120]}{'...' if len(jd) > 120 else ''}\n")
    for ranked, outcome in zip(result.retrieved, result.outcomes):
        label = f"[{ranked.distance:.4f}] {ranked.candidate.name} ({ranked.candidate.id})"
        if hasattr(outcome, "report"):
            report = outcome.report
            print(f"OK     {label}")
            print(f"       strengths: {', '.join(report.strengths)}")
            print(f"       gaps:      {', '.join(report.gaps)}")
            questions = report.interview_questions or []
            print(f"       questions: {', '.join(questions[:3])}")
        else:
            print(
                f"ERROR  {label}: ({outcome.error_type}) {outcome.message}"
            )
    print("\nScreening is evidence-only; hiring decisions remain with the recruiter.")


if __name__ == "__main__":
    main()