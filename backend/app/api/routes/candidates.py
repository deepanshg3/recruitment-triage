"""Candidate listing, detail, and recruiter shortlist actions.

Thin routes: validate input, load a DB session, delegate to the candidate
service, transform the result into API schemas. No SQL, no LLM, no vectors.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.api import (
    CandidateListResponse,
    CandidateResponse,
    CandidateUpdate,
)
from app.services.candidates import get_candidate, list_candidates, update_shortlist

router = APIRouter(prefix="/candidates", tags=["Candidates"])


@router.get(
    "",
    response_model=CandidateListResponse,
    summary="List candidates",
    description=(
        "Deterministic recruiter listing. Filters combine with AND logic, text "
        "filters are case-insensitive and whitespace-normalized. target_role "
        "and source accept comma-separated lists where multiple values are "
        "OR-ed together (e.g. `target_role=Backend Engineer,Full-Stack "
        "Engineer`). Skills accepts a comma-separated list; a candidate must "
        "contain ALL requested skills. Sorting is restricted to a whitelist "
        "with stable id tie-breaking. This endpoint never calls the LLM."
    ),
)
def list_candidates_endpoint(
    db: Session = Depends(get_db),
    search: str | None = None,
    target_role: str | None = None,
    min_experience: int | None = None,
    max_experience: int | None = None,
    source: str | None = None,
    skills: str | None = None,
    is_shortlisted: str | None = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 20,
) -> CandidateListResponse:
    result = list_candidates(
        db,
        search=search,
        target_role=target_role,
        min_experience=min_experience,
        max_experience=max_experience,
        source=source,
        skills=skills,
        is_shortlisted=is_shortlisted,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    total_pages = 0 if result.total == 0 else -(-result.total // page_size)
    return CandidateListResponse(
        items=[CandidateResponse.model_validate(c) for c in result.items],
        page=page,
        page_size=page_size,
        total=result.total,
        total_pages=total_pages,
    )


@router.get(
    "/{candidate_id}",
    response_model=CandidateResponse,
    summary="Get a single candidate",
    description=(
        "Returns the full candidate record. Embedding vectors are never exposed."
    ),
)
def candidate_detail_endpoint(
    candidate_id: str,
    db: Session = Depends(get_db),
) -> CandidateResponse:
    return CandidateResponse.model_validate(get_candidate(db, candidate_id))


@router.patch(
    "/{candidate_id}",
    response_model=CandidateResponse,
    summary="Update recruiter flags (shortlist)",
    description=(
        "Recruiter action. Only `is_shortlisted` may be modified; arbitrary "
        "fields are rejected with 422. Persisted to SQLite. Never calls the LLM."
    ),
)
def candidate_update_endpoint(
    candidate_id: str,
    payload: CandidateUpdate,
    db: Session = Depends(get_db),
) -> CandidateResponse:
    candidate = update_shortlist(db, candidate_id, payload.is_shortlisted)
    return CandidateResponse.model_validate(candidate)