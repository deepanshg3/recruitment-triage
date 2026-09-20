"""Pydantic schema for the LLM's structured screening output.

The LLM is asked to reason about a candidate against a job description and
produce a screening report. It must NOT make hiring decisions or produce
scores/percentages — the recruiter remains the decision maker.

Field descriptions below double as instructions: the description text is sent
to the model as part of the structured-output schema.
"""

from typing import Annotated

from pydantic import BaseModel, Field


class ScreeningReport(BaseModel):
    """Evidence-based screening report for ONE candidate vs a JD.

    All lists must be based on facts present in the JD and candidate record
    only. Missing information must be described as "not specified", never as
    proof that the candidate lacks something.
    """

    candidate_id: Annotated[
        str,
        Field(
            description=(
                "The candidate's stable identifier as supplied in the input. "
                "Copy it exactly."
            )
        ),
    ]
    candidate_name: Annotated[
        str,
        Field(
            description=(
                "The candidate's name as supplied in the input. Copy it exactly."
            )
        ),
    ]
    strengths: Annotated[
        list[str],
        Field(
            description=(
                "Capabilities the candidate demonstrably has, referencing "
                "specific skills/experience/notes from the candidate data. "
                "No invented facts."
            )
        ),
    ]
    gaps: Annotated[
        list[str],
        Field(
            description=(
                "Areas where the JD requires something the candidate data does "
                "not demonstrate. If a requirement is not mentioned in the "
                "candidate data, phrase it as 'not specified' — do not claim "
                "the candidate lacks it."
            )
        ),
    ]
    evidence: Annotated[
        list[str],
        Field(
            description=(
                "Short factual citations from the candidate record (e.g. "
                "'Skills list includes Python', 'Notes mention production "
                "APIs'). Explicit evidence only, no assumptions."
            )
        ),
    ]
    interview_questions: Annotated[
        list[str],
        Field(
            description=(
                "Questions that target genuine uncertainty or important JD "
                "requirements — e.g. probing production API design or a "
                "required skill that is not specified in the candidate data."
            )
        ),
    ]
    overall_assessment: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Optional neutral summary of the evidence, in 1-3 sentences. "
                "Factual only. This is NOT a hiring recommendation and must "
                "never contain a score, percentage or decision."
            ),
        ),
    ]