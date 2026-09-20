"""ScreeningService batch tests (Prompt 3, section E).

Contract: one LLM call per candidate, input order preserved, failures are
explicit (ScreeningFailure) and never fabricate a report.
"""

import pytest

from app.schemas.screening import ScreeningReport
from app.services.errors import ScreeningApiError
from app.services.screening_service import (
    ScreeningFailure,
    ScreeningService,
    ScreeningSuccess,
)


def _report(candidate_id, name, i=0):
    return ScreeningReport(
        candidate_id=candidate_id,
        candidate_name=name,
        strengths=[f"strength {i}"],
        gaps=[f"gap {i}"],
        evidence=[f"evidence {i}"],
        interview_questions=[f"question {i}"],
    )


class StubLLM:
    """Tracks call order; can fail specific candidate ids."""

    def __init__(self, fail_ids=()):
        self.fail_ids = set(fail_ids)
        self.calls = []  # candidate ids in call order

    def generate_structured(self, *, response_schema, system_instruction, user_content):
        cid = None
        for line in user_content.splitlines():
            if line.startswith("Candidate ID:"):
                cid = line.split(":", 1)[1].strip()
        self.calls.append(cid)
        if cid in self.fail_ids:
            raise ScreeningApiError(f"simulated LLM failure for {cid}")
        return _report(cid, "Anonymous")


def _candidates(candidate_factory, count):
    return [
        candidate_factory(id=f"cand_{i}", name=f"Name {i}") for i in range(count)
    ]


def test_batch_makes_one_llm_call_per_candidate(job_description, candidate_factory):
    candidates = _candidates(candidate_factory, 5)
    llm = StubLLM()
    outcomes = ScreeningService(llm).screen_candidates(
        job_description=job_description, candidates=candidates
    )
    assert len(llm.calls) == 5
    assert len(outcomes) == 5


def test_batch_preserves_input_order(job_description, candidate_factory):
    candidates = _candidates(candidate_factory, 5)
    services = ScreeningService(StubLLM())
    outcomes = services.screen_candidates(
        job_description=job_description, candidates=candidates
    )
    assert [o.candidate_id for o in outcomes] == [f"cand_{i}" for i in range(5)]
    assert all(hasattr(o, "report") for o in outcomes)


def test_batch_returns_valid_screeningreports(job_description, candidate_factory):
    candidates = _candidates(candidate_factory, 2)
    outcomes = ScreeningService(StubLLM()).screen_candidates(
        job_description=job_description, candidates=candidates
    )
    for o in outcomes:
        assert isinstance(o, ScreeningSuccess)
        assert isinstance(o.report, ScreeningReport)


def test_one_failure_does_not_destroy_the_batch(job_description, candidate_factory):
    candidates = _candidates(candidate_factory, 5)
    llm = StubLLM(fail_ids={"cand_2"})
    outcomes = ScreeningService(llm).screen_candidates(
        job_description=job_description, candidates=candidates
    )

    assert len(outcomes) == 5
    assert outcomes[2].candidate_id == "cand_2"
    assert isinstance(outcomes[2], ScreeningFailure)
    assert outcomes[2].error_type == "ScreeningApiError"
    assert "cand_2" in outcomes[2].message

    for idx in (0, 1, 3, 4):
        assert isinstance(outcomes[idx], ScreeningSuccess)
        assert isinstance(outcomes[idx].report, ScreeningReport)


def test_no_fake_report_for_failed_candidate(job_description, candidate_factory):
    candidates = [candidate_factory(id="cand_0"), candidate_factory(id="cand_1")]
    outcomes = ScreeningService(StubLLM(fail_ids={"cand_0"})).screen_candidates(
        job_description=job_description, candidates=candidates
    )

    failed = outcomes[0]
    assert isinstance(failed, ScreeningFailure)
    assert not hasattr(failed, "report")
    assert failed.message  # explicit, not silent

    success = outcomes[1]
    assert isinstance(success, ScreeningSuccess)
    assert isinstance(success.report, ScreeningReport)


@pytest.mark.parametrize("jd", ["", "   "])
def test_batch_rejects_empty_jd_without_calling_llm(jd, candidate_factory):
    candidates = _candidates(candidate_factory, 2)
    llm = StubLLM()
    with pytest.raises(Exception, match="Job description"):
        ScreeningService(llm).screen_candidates(
            job_description=jd, candidates=candidates
        )
    assert llm.calls == []