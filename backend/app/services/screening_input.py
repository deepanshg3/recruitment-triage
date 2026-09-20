"""Build the canonical, LLM-safe representation of a candidate for screening.

Separate from the embedding document (`candidate_document.py`): screening
prioritizes recruiter-relevant recruiting information (source, notes) that is
irrelevant for vector search.

What is sent to the LLM:
- candidate_id, name, target_role, years_experience, source, skills, notes

What is deliberately NOT sent:
- is_shortlisted / any internal triage state
- applied_date (administrative, not a fit signal)
- embedding / vector / sqlite-vec data
- ORM internals
"""

from pydantic import BaseModel, Field

from app.services.errors import ScreeningInputError

# Fields the LLM can reason about. Constructor does NOT include applied_date.
_SCREENING_FIELDS = (
    "candidate_id",
    "name",
    "target_role",
    "years_experience",
    "source",
    "skills",
    "notes",
)


class ScreeningCandidate(BaseModel):
    """Structured candidate information sent to the LLM."""

    candidate_id: str
    name: str
    target_role: str
    years_experience: int = Field(ge=0)
    source: str = ""
    skills: list[str] = Field(default_factory=list)
    notes: str = ""

    def to_prompt_text(self) -> str:
        """Deterministic text block for the screening prompt."""
        skills = ", ".join(self.skills or [])
        return "\n".join(
            [
                f"Candidate ID: {self.candidate_id}",
                f"Name: {self.name}",
                f"Target Role: {self.target_role}",
                f"Years of Experience: {self.years_experience}",
                f"Source: {self.source}",
                f"Skills: {skills}",
                f"Notes: {self.notes}",
            ]
        )


def build_screening_input(candidate) -> ScreeningCandidate:
    """Convert any candidate-like object into a validated ScreeningCandidate.

    Rejects candidates missing required identifying fields so corrupt data is
    never sent to the LLM.
    """
    if candidate is None:
        raise ScreeningInputError("Candidate is missing.")

    candidate_id = getattr(candidate, "id", None)
    name = getattr(candidate, "name", None)
    if not candidate_id or not name or not name.strip():
        raise ScreeningInputError(
            "Candidate is invalid: id and name are required."
        )

    try:
        return ScreeningCandidate(
            candidate_id=str(candidate_id),
            name=name,
            target_role=getattr(candidate, "target_role", "") or "",
            years_experience=getattr(candidate, "years_experience", 0) or 0,
            source=getattr(candidate, "source", "") or "",
            skills=list(getattr(candidate, "skills", None) or []),
            notes=getattr(candidate, "notes", "") or "",
        )
    except Exception as exc:  # pydantic validation failure
        raise ScreeningInputError(
            f"Candidate {candidate_id!r} has invalid screening data: {exc}"
        ) from exc