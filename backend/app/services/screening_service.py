"""Screening service: JD + candidate(s) -> structured ScreeningReport(s).

Responsibilities:
- validate inputs
- build prompt (prompts.py)
- call the LLM through the GeminiLLMClient abstraction (no direct SDK use here)
- validate/stamp the returned report

Design decision: ONE LLM call per candidate (not one big multi-candidate prompt).
Rationale: per-candidate error isolation, simpler validation, simpler retry
behavior, and easier per-candidate presentation later. Cost is K LLM calls for
K candidates, which for the existing top_k=5 default is 5 calls per search.

Partial failure contract: `screen_candidates` preserves input order and returns
one explicit outcome per candidate. A failed candidate yields a
ScreeningFailure (no fake report); the candidates around it are still screened.
Success/failure states are data, not exceptions, at the batch boundary.
"""

import logging

from pydantic import BaseModel

from app.schemas.screening import ScreeningReport
from app.services.errors import (
    ScreeningError,
    ScreeningInputError,
)
from app.services.llm_client import GeminiLLMClient
from app.services.prompts import SYSTEM_INSTRUCTION, build_screening_prompt
from app.services.screening_input import build_screening_input

logger = logging.getLogger(__name__)


class ScreeningSuccess(BaseModel):
    candidate_id: str
    report: ScreeningReport


class ScreeningFailure(BaseModel):
    candidate_id: str | None
    error_type: str
    message: str


ScreeningOutcome = ScreeningSuccess | ScreeningFailure


def _validate_job_description(job_description: object) -> str:
    if not isinstance(job_description, str) or not job_description.strip():
        raise ScreeningInputError("Job description must not be empty.")
    return job_description.strip()


class ScreeningService:
    def __init__(self, llm_client: GeminiLLMClient) -> None:
        self._llm_client = llm_client

    def screen_candidate(
        self, *, job_description: str, candidate
    ) -> ScreeningReport:
        """Screen ONE candidate. Raises ScreeningError on any failure."""
        jd = _validate_job_description(job_description)
        candidate_input = build_screening_input(candidate)
        prompt = build_screening_prompt(jd, candidate_input.to_prompt_text())

        report = self._llm_client.generate_structured(
            response_schema=ScreeningReport,
            system_instruction=SYSTEM_INSTRUCTION,
            user_content=prompt,
        )
        return self._stamp_report(report, candidate)

    def screen_candidates(
        self, *, job_description: str, candidates
    ) -> list[ScreeningOutcome]:
        """Screen a sequence of candidates, preserving order.

        Returns one ScreeningOutcome per candidate. Failures are represented as
        ScreeningFailure objects (never fake reports) and do not stop the batch.
        """
        jd = _validate_job_description(job_description)

        outcomes: list[ScreeningOutcome] = []
        for candidate in candidates:
            candidate_id = getattr(candidate, "id", None)
            try:
                report = self.screen_candidate(job_description=jd, candidate=candidate)
            except ScreeningError as exc:
                logger.warning("Screening failed for %r: %s", candidate_id, exc)
                outcomes.append(
                    ScreeningFailure(
                        candidate_id=candidate_id,
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                )
            except Exception as exc:  # unexpected; isolate but do not hide
                logger.exception(
                    "Unexpected screening error for %r", candidate_id
                )
                outcomes.append(
                    ScreeningFailure(
                        candidate_id=candidate_id,
                        error_type=type(exc).__name__,
                        message=f"Unexpected screening error: {exc}",
                    )
                )
            else:
                outcomes.append(
                    ScreeningSuccess(candidate_id=candidate_id, report=report)
                )
        return outcomes

    @staticmethod
    def _stamp_report(report: ScreeningReport, candidate) -> ScreeningReport:
        """Guarantee the report links to the real candidate.

        candidate_id/name are authoritative from the candidate record, so a
        hallucinated id/name from the LLM can never misroute a report.
        """
        report.candidate_id = str(getattr(candidate, "id", ""))
        report.candidate_name = str(getattr(candidate, "name", ""))
        return report