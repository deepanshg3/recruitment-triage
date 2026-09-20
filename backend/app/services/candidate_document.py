"""Build the canonical document text that gets embedded for each candidate.

The SAME function must be used everywhere embeddings are generated so a given
candidate always maps to identical text. The text is the semantic 'suitability'
signal for vector search: role, experience, skills and notes only. Recruiter /
administrative fields (is_shortlisted, applied_date, source) are deliberately
excluded because they are not part of fit.
"""

from app.models.candidate import Candidate


def build_candidate_document(candidate: Candidate) -> str:
    """Return a deterministic text representation of a candidate.

    Works with any object exposing the documented attributes, so tests can use
    lightweight stubs instead of ORM Candidate instances.
    """
    skills = ", ".join(candidate.skills or [])
    return "\n".join(
        [
            f"Name: {candidate.name}",
            f"Target Role: {candidate.target_role}",
            f"Years of Experience: {candidate.years_experience}",
            f"Skills: {skills}",
            f"Notes: {candidate.notes}",
        ]
    )