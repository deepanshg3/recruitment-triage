"""POST /match: JD -> retrieval -> top-K -> AI screening.

Thin route. AI logic lives in `app.services.orchestration`; this file only
validates the request, wires the service dependencies, calls the orchestrator,
and transforms its result into the API schema.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import engine, get_db
from app.schemas.api import MatchRequest, MatchResponse, MatchResultItem, CandidateResponse
from app.services.embedding_service import GeminiEmbeddingService
from app.services.llm_client import GeminiLLMClient
from app.services.orchestration import (
    MatchAndScreenResult,
    match_and_screen_candidates,
)
from app.services.screening_service import ScreeningSuccess

router = APIRouter(prefix="/match", tags=["Matching"])


def _build_match_response(result: MatchAndScreenResult) -> MatchResponse:
    """Transform orchestrator output into API schema (distance stays distance)."""
    items: list[MatchResultItem] = []
    for ranked, outcome in zip(result.retrieved, result.outcomes):
        screening = None
        screening_error = None
        if isinstance(outcome, ScreeningSuccess):
            screening = outcome.report
        else:
            screening_error = f"{outcome.error_type}: {outcome.message}"
        items.append(
            MatchResultItem(
                candidate=CandidateResponse.model_validate(ranked.candidate),
                retrieval_distance=ranked.distance,
                screening=screening,
                screening_error=screening_error,
            )
        )
    return MatchResponse(
        job_description=result.job_description,
        top_k_requested=result.top_k_requested,
        results=items,
    )


@router.post(
    "",
    response_model=MatchResponse,
    summary="Retrieve top-K candidates for a JD and AI-screen them",
    description=(
        "Embeds the JD once, retrieves the top-K candidates with sqlite-vec, "
        "then LLM-screens each retrieved candidate (one Gemini call per "
        "candidate). `retrieval_distance` is the raw cosine distance (lower = "
        "more similar); it is never converted into a percentage or score. "
        "Requires configured Gemini credentials and indexed embeddings."
    ),
)
def run_match_endpoint(
    payload: MatchRequest,
    db: Session = Depends(get_db),
) -> MatchResponse:
    result = match_and_screen_candidates(
        db,
        engine=engine,
        embed_service=GeminiEmbeddingService(),
        llm_client=GeminiLLMClient(),
        job_description=payload.job_description,
        top_k=payload.top_k,
    )
    return _build_match_response(result)