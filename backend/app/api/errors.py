"""HTTP error mapping for the REST API.

Service-layer errors are translated to stable HTTP statuses. Responses never
include API keys, stack traces, or raw SDK internals; useful context is logged.

Mapping:
- 400 InvalidQueryError, RetrievalInputError, ScreeningInputError
      (invalid request params / invalid top_k caught here)
- 404 CandidateNotFoundError
- 422 Pydantic/FastAPI request validation (automatic, includes body shape)
- 502 malformed upstream Gemini responses (EmbeddingResponseError,
      ScreeningResponseError)
- 503 AI service unavailable / not configured (missing GEMINI_API_KEY,
      no embeddings indexed, Gemini API/network errors)
- 500 unexpected internal errors (logged with stack, generic response)

Embedding(vector) and LLM roots are NOT exposed; only exception type names are
surfaced in messages where useful.
"""

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.services.errors import (
    CandidateNotFoundError,
    EmbeddingApiError,
    EmbeddingConfigurationError,
    EmbeddingResponseError,
    InvalidQueryError,
    RetrievalInputError,
    ScreeningApiError,
    ScreeningConfigurationError,
    ScreeningInputError,
    ScreeningResponseError,
    VectorIndexError,
)

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all HTTP exception handlers to `app`."""

    def _json(status: int, detail: str):
        return JSONResponse(status_code=status, content={"detail": detail})

    # --- 400: invalid client-supplied values -------------------------------
    @app.exception_handler(InvalidQueryError)
    def invalid_query(request, exc: InvalidQueryError):
        logger.info("Invalid query: %s", exc)
        return _json(400, str(exc))

    @app.exception_handler(RetrievalInputError)
    def retrieval_input(request, exc: RetrievalInputError):
        logger.info("Invalid retrieval input: %s", exc)
        return _json(400, str(exc))

    @app.exception_handler(ScreeningInputError)
    def screening_input(request, exc: ScreeningInputError):
        logger.info("Invalid screening input: %s", exc)
        return _json(400, str(exc))

    # --- 404: missing resource ----------------------------------------------
    @app.exception_handler(CandidateNotFoundError)
    def candidate_not_found(request, exc: CandidateNotFoundError):
        logger.info("Candidate not found: %s", exc)
        return _json(404, str(exc))

    # --- 502: upstream returned an unusable response -------------------------
    @app.exception_handler(EmbeddingResponseError)
    def embedding_response(request, exc: EmbeddingResponseError):
        logger.error("Embedding service returned invalid data: %s", exc)
        return _json(
            502, "AI embedding service returned an invalid response."
        )

    @app.exception_handler(ScreeningResponseError)
    def screening_response(request, exc: ScreeningResponseError):
        logger.error("Screening service returned invalid data: %s", exc)
        return _json(502, "AI screening service returned an invalid response.")

    # --- 503: AI service unavailable / misconfigured --------------------------
    # Responses use static, credential-free text; the real (already sanitized)
    # exception message is logged for operators.
    @app.exception_handler(EmbeddingConfigurationError)
    def embedding_config(request, exc: EmbeddingConfigurationError):
        logger.error("Embedding service misconfigured: %s", exc)
        return _json(
            503,
            "AI embedding service is not configured. Set GEMINI_API_KEY and "
            "GEMINI_EMBEDDING_MODEL in the project .env file and restart.",
        )

    @app.exception_handler(EmbeddingApiError)
    def embedding_api(request, exc: EmbeddingApiError):
        logger.error("Embedding API unavailable: %s", exc)
        return _json(
            503,
            "AI embedding service is unavailable (network, quota, auth, or "
            "rate-limit problem).",
        )

    @app.exception_handler(ScreeningConfigurationError)
    def screening_config(request, exc: ScreeningConfigurationError):
        logger.error("Screening service misconfigured: %s", exc)
        return _json(
            503,
            "AI screening service is not configured. Set GEMINI_API_KEY and "
            "GEMINI_LLM_MODEL in the project .env file and restart.",
        )

    @app.exception_handler(ScreeningApiError)
    def screening_api(request, exc: ScreeningApiError):
        logger.error("Screening API unavailable: %s", exc)
        return _json(
            503,
            "AI screening service is unavailable (network, quota, auth, or "
            "rate-limit problem).",
        )

    @app.exception_handler(VectorIndexError)
    def vector_index(request, exc: VectorIndexError):
        logger.error("Vector index unavailable: %s", exc)
        return _json(
            503,
            "AI retrieval service is unavailable. Run "
            "`python -m app.db.embed_candidates` to index candidate embeddings.",
        )

    # --- 500: unexpected -------------------------------------------------------
    @app.exception_handler(Exception)
    def unexpected(request, exc: Exception):
        logger.exception("Unhandled API error for %s", request.url.path)
        return _json(500, "Internal server error.")