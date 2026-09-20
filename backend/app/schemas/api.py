"""REST API request/response schemas.

Dedicated contracts for the HTTP layer — the ORM models are never used
directly as API payloads. ScreeningReport is reused as-is for the AI output.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.candidate import CandidateBase
from app.schemas.screening import ScreeningReport

# Upper bound for /match top_k. The index only holds ~50 candidates, matching
# this many costs one LLM call each, and every screen is one API call.
MAX_TOP_K = 50


class CandidateResponse(CandidateBase):
    """Full candidate payload shown to the frontend.

    Deliberately excludes embedding vectors, database internals, and any
    retrieved distance — those are /match concepts, not candidate properties.
    """


class CandidateListResponse(BaseModel):
    """Paginated candidate listing."""

    items: list[CandidateResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


class CandidateUpdate(BaseModel):
    """Recruiter actions allowed on a candidate.

    Only shortlisting is supported. `extra="forbid"` ensures arbitrary fields
    (name, skills, experience, ...) can never be modified through the API.
    """

    model_config = ConfigDict(extra="forbid")

    is_shortlisted: bool


class MatchRequest(BaseModel):
    """Payload for POST /match."""

    job_description: str = Field(
        min_length=1,
        description="Free-text job description to match and screen against.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=MAX_TOP_K,
        description=f"Number of top candidates to retrieve and screen (1..{MAX_TOP_K}).",
    )

    @field_validator("job_description")
    @classmethod
    def _job_description_not_blank(cls, v: str) -> str:
        v = v.strip() if isinstance(v, str) else v
        if not v:
            raise ValueError("job_description must not be empty.")
        return v


class MatchResultItem(BaseModel):
    """One retrieved candidate and its (optional) screening report.

    `retrieval_distance` is the raw sqlite-vec cosine distance (lower = more
    similar). It is NOT a match percentage, score, or confidence — the
    terminology intentionally says exactly what it is.
    """

    candidate: CandidateResponse
    retrieval_distance: float = Field(
        description="Raw cosine distance from the vec0 search (lower = more similar)."
    )
    screening: ScreeningReport | None = None
    screening_error: str | None = Field(
        default=None,
        description="Present instead of `screening` when the LLM step failed; "
        "contains a typed error message (never an API key or stack trace).",
    )


class MatchResponse(BaseModel):
    """Response of POST /match: retrieval info + per-candidate outcomes."""

    job_description: str
    top_k_requested: int
    results: list[MatchResultItem]