from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class CandidateBase(BaseModel):
    """Read/return shape of a candidate.

    Mirrors the structure in data/candidates.json plus the triage field
    that the model adds.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    target_role: str
    years_experience: int = Field(ge=0)
    source: str
    skills: list[str] = Field(default_factory=list)
    notes: str = ""
    applied_date: date
    is_shortlisted: bool = False


class CandidateCreate(CandidateBase):
    """Input shape used when seeding candidates from JSON."""