"""ScreeningService single-candidate tests (Prompt 3, section D).

The LLM is always a stub — zero live Gemini calls.
"""

import pytest

from app.schemas.screening import ScreeningReport
from app.services.errors import (
    ScreeningApiError,
    ScreeningInputError,
)
from app.services.screening_service import ScreeningService


def _report(candidate_id="cand_001", name="Ada Lovelace"):
    return ScreeningReport(
        candidate_id=candidate_id,
        candidate_name=name,
        strengths=["Python expertise"],
        gaps=["Docker not specified"],
        evidence=["Skills list includes Python"],
        interview_questions=["Design a fault tolerant API."],
        overall_assessment="Evidence indicates strong backend depth.",
    )


class StubLLM:
    """Generates a fixed report (optionally raising for injected failures)."""

    def __init__(self, report=None, exc=None):
        self.report = report
        self.exc = exc
        self.calls = []

    def generate_structured(self, *, response_schema, system_instruction, user_content):
        self.calls.append(
            {"schema": response_schema, "system": system_instruction, "content": user_content}
        )
        if self.exc is not None:
            raise self.exc
        return self.report


def _service(**llm_kwargs):
    return ScreeningService(StubLLM(**llm_kwargs))


def test_screen_candidate_returns_screening_report(job_description, candidate_factory):
    candidate = candidate_factory(id="cand_001", name="Ada Lovelace")
    service = _service(report=_report())

    result = service.screen_candidate(
        job_description=job_description, candidate=candidate
    )

    assert isinstance(result, ScreeningReport)
    assert result.candidate_id == "cand_001"
    assert result.candidate_name == "Ada Lovelace"
    assert result.overall_assessment is not None


def test_screen_candidate_sends_only_canonical_candidate_data(
    job_description, candidate_factory
):
    candidate = candidate_factory(id="cand_001", name="Ada Lovelace")
    service = _service(report=_report())

    service.screen_candidate(job_description=job_description, candidate=candidate)

    content = service._llm_client.calls[0]["content"]
    assert "JOB DESCRIPTION:" in content
    assert "Backend Engineer" in content
    assert "Python, SQL, FastAPI" in content
    assert "is_shortlisted" not in content.lower()
    assert "vector" not in content.lower()


def test_stamp_report_forces_candidate_link(job_description, candidate_factory):
    candidate = candidate_factory(id="cand_042", name="Katherine Johnson")
    hallucinated = _report(candidate_id="WRONG_ID", name="Someone Else")
    service = _service(report=hallucinated)

    result = service.screen_candidate(job_description=job_description, candidate=candidate)

    assert result.candidate_id == "cand_042"
    assert result.candidate_name == "Katherine Johnson"


@pytest.mark.parametrize("jd", ["", "   \n\t  ", None, 123])
def test_empty_job_description_rejected(jd, candidate_factory):
    candidate = candidate_factory()
    service = _service(report=_report())
    with pytest.raises(ScreeningInputError, match="Job description"):
        service.screen_candidate(job_description=jd, candidate=candidate)


@pytest.mark.parametrize("bad", [None, object()])
def test_invalid_candidate_rejected(job_description, bad):
    service = _service(report=_report())
    with pytest.raises(ScreeningInputError, match="Candidate"):
        service.screen_candidate(job_description=job_description, candidate=bad)


def test_candidate_missing_name_rejected(job_description):
    from types import SimpleNamespace

    stub = SimpleNamespace(id="cand_x")
    service = _service(report=_report())
    with pytest.raises(ScreeningInputError, match="name"):
        service.screen_candidate(job_description=job_description, candidate=stub)


def test_llm_failure_propagates(job_description, candidate_factory):
    candidate = candidate_factory()
    service = _service(exc=ScreeningApiError("LLM boom"))
    with pytest.raises(ScreeningApiError, match="LLM boom"):
        service.screen_candidate(job_description=job_description, candidate=candidate)