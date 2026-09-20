"""Deterministic candidate querying/filtering/sorting/pagination.

No LLM, no vectors — plain SQLAlchemy reads plus predictable in-memory
filtering. The dataset is ~50 candidates, so in-Python filtering keeps the
LIKE/JSON semantics trivial and fully deterministic; pagination slices with a
stable (tie-broken) order.

Terminology: `retrieval_distance` is a /match concept and never appears here.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.services.errors import (
    CandidateNotFoundError,
    InvalidQueryError,
)

# Explicit sort whitelist — arbitrary SQL column names are rejected.
SORT_FIELDS = ("name", "target_role", "years_experience", "applied_date")
SORT_ORDERS = ("asc", "desc")
MAX_PAGE_SIZE = 100
MIN_DATE = date.min
# Sorting with a stable tie-break on candidate id.
_TIE_KEY = "id"


@dataclass
class CandidatePage:
    items: list[Candidate]
    total: int


def _normalize(value: str | None) -> str | None:
    """Strip and collapse internal whitespace for predictable comparisons."""
    if value is None:
        return None
    return " ".join(value.split())


def _parse_bool(value: str | None, *, name: str) -> bool | None:
    if value is None:
        return None
    v = value.strip().lower()
    if v in ("true", "1", "yes"):
        return True
    if v in ("false", "0", "no"):
        return False
    raise InvalidQueryError(
        f"Invalid value for '{name}': expected true/false, got {value!r}."
    )


def _parse_skills(value: str | None) -> list[str]:
    if value is None:
        return []
    parts = [p.strip() for p in value.split(",") if p.strip()]
    if not parts:
        raise InvalidQueryError(
            f"Invalid value for 'skills': got {value!r}. Provide at least one skill."
        )
    return parts


def _validate_pagination(page: int, page_size: int) -> None:
    if page < 1:
        raise InvalidQueryError(
            f"Invalid page {page!r}: page must be >= 1."
        )
    if page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise InvalidQueryError(
            f"Invalid page_size {page_size!r}: expected a value between "
            f"1 and {MAX_PAGE_SIZE}."
        )


def _validate_experience(min_experience: int | None, max_experience: int | None) -> None:
    if min_experience is not None and min_experience < 0:
        raise InvalidQueryError(
            f"Invalid min_experience {min_experience!r}: must be >= 0."
        )
    if max_experience is not None and max_experience < 0:
        raise InvalidQueryError(
            f"Invalid max_experience {max_experience!r}: must be >= 0."
        )
    if (
        min_experience is not None
        and max_experience is not None
        and min_experience > max_experience
    ):
        raise InvalidQueryError(
            f"min_experience ({min_experience}) cannot exceed "
            f"max_experience ({max_experience})."
        )


def _validate_sort(sort_by: str, sort_order: str) -> None:
    if sort_by not in SORT_FIELDS:
        raise InvalidQueryError(
            f"Invalid sort_by {sort_by!r}: allowed values are "
            f"{', '.join(SORT_FIELDS)}."
        )
    if sort_order not in SORT_ORDERS:
        raise InvalidQueryError(
            f"Invalid sort_order {sort_order!r}: allowed values are "
            f"{', '.join(SORT_ORDERS)}."
        )


def _matches(candidate: Candidate, filters: dict) -> bool:
    if filters["search"] is not None:
        q = filters["search"].lower()
        haystacks = [
            candidate.name,
            candidate.target_role,
            candidate.notes,
            *candidate.skills,
        ]
        if not any(q in (h or "").lower() for h in haystacks):
            return False

    if filters["target_role"] is not None and (_normalize(candidate.target_role) or "").lower() != filters["target_role"].lower():
        return False

    if filters["source"] is not None and (_normalize(candidate.source) or "").lower() != (
        filters["source"].lower()
    ):
        return False

    if filters["min_experience"] is not None and (
        candidate.years_experience < filters["min_experience"]
    ):
        return False
    if filters["max_experience"] is not None and (
        candidate.years_experience > filters["max_experience"]
    ):
        return False

    if filters["skills"]:
        candidate_skills = {s.lower() for s in candidate.skills}
        if not all(s.lower() in candidate_skills for s in filters["skills"]):
            return False

    if filters["is_shortlisted"] is not None and (
        candidate.is_shortlisted != filters["is_shortlisted"]
    ):
        return False

    return True


def _primary_key(sort_by: str):
    """Sort key for the primary field (id is used as the stable tie-break)."""

    def key(c: Candidate):
        if sort_by == "name":
            return (_normalize(c.name) or "").lower()
        if sort_by == "target_role":
            return (_normalize(c.target_role) or "").lower()
        if sort_by == "years_experience":
            return c.years_experience
        if sort_by == "applied_date":
            return c.applied_date or MIN_DATE
        return c.id

    return key


def list_candidates(
    db: Session,
    *,
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
) -> CandidatePage:
    """Return one page of candidates satisfying ALL supplied filters.

    Raises InvalidQueryError for invalid filter/sort/pagination values.
    """
    _validate_sort(sort_by, sort_order)
    _validate_pagination(page, page_size)
    _validate_experience(min_experience, max_experience)

    parsed_shortlist = _parse_bool(is_shortlisted, name="is_shortlisted")
    parsed_skills = _parse_skills(skills)

    filters = {
        "search": _normalize(search),
        "target_role": _normalize(target_role),
        "min_experience": min_experience,
        "max_experience": max_experience,
        "source": _normalize(source),
        "skills": parsed_skills,
        "is_shortlisted": parsed_shortlist,
    }

    candidates = db.execute(select(Candidate)).scalars().all()
    # Normalized filter is always lowercase; matching lowercases candidate data.
    if filters["target_role"] is not None:
        filters["target_role"] = filters["target_role"].lower()
    if filters["source"] is not None:
        filters["source"] = filters["source"].lower()

    filtered = [c for c in candidates if _matches(c, filters)]
    # Two-pass stable sort: base order by id, then by the primary sort field.
    # Id remains the tie-break in ASCENDING order even when direction is desc.
    filtered.sort(key=lambda c: c.id)
    filtered.sort(key=_primary_key(sort_by), reverse=(sort_order == "desc"))

    total = len(filtered)
    start = (page - 1) * page_size
    items = filtered[start : start + page_size]
    return CandidatePage(items=items, total=total)


def get_candidate(db: Session, candidate_id: str) -> Candidate:
    """Return the candidate or raise CandidateNotFoundError."""
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise CandidateNotFoundError(f"Candidate {candidate_id!r} does not exist.")
    return candidate


def update_shortlist(
    db: Session, candidate_id: str, is_shortlisted: bool
) -> Candidate:
    """Persist a recruiter shortlist change. Never touches the LLM."""
    candidate = get_candidate(db, candidate_id)
    candidate.is_shortlisted = is_shortlisted
    db.commit()
    db.refresh(candidate)
    return candidate