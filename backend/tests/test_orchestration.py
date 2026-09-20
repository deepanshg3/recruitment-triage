"""Orchestration tests (Prompt 3, section F).

Both retrieval AND screening are mocked, so no embeddings API and no Gemini
calls are touched. Verifies the composition: JD -> retrieval(top_k) -> screen.
"""

import pytest

from app.schemas.screening import ScreeningReport
from app.services.errors import ScreeningInputError
from app.services.orchestration import (
    MatchAndScreenResult,
    match_and_screen_candidates,
)
from app.services.retrieval import RankedCandidate
from app.services.screening_service import (
    ScreeningSuccess,
)


def _report(candidate_id, name):
    return ScreeningReport(
        candidate_id=candidate_id,
        candidate_name=name,
        strengths=["strength"],
        gaps=["gap"],
        evidence=["evidence"],
        interview_questions=["question"],
    )


def _ranked(candidates):
    return [
        RankedCandidate(candidate=c, distance=i / 10.0)
        for i, c in enumerate(candidates)
    ]


def _fake_screen(retrieved):
    def fake(self, *, job_description, candidates):
        return [
            ScreeningSuccess(
                candidate_id=c.id,
                report=_report(c.id, c.name),
            )
            for c in candidates
        ]

    return fake


def test_match_and_screen_composes_retrieval_then_screening(
    monkeypatch, job_description, candidate_factory
):
    candidates = [
        candidate_factory(id="cand_a", name="Ann"),
        candidate_factory(id="cand_b", name="Bob"),
    ]
    ranked = _ranked(candidates)

    captured = {}
    monkeypatch.setattr(
        "app.services.orchestration.search_candidates",
        lambda db, **kw: captured.update(kw) or ranked,
    )
    monkeypatch.setattr(
        "app.services.screening_service.ScreeningService.screen_candidates",
        _fake_screen(ranked),
    )

    result = match_and_screen_candidates(
        None,  # db unused (retrieval mocked)
        engine=None,
        embed_service=None,
        llm_client=None,
        job_description=job_description,
        top_k=2,
    )

    assert isinstance(result, MatchAndScreenResult)
    assert captured["top_k"] == 2
    assert captured["job_description"] == job_description
    assert [r.candidate.id for r in result.retrieved] == ["cand_a", "cand_b"]
    assert result.top_k_requested == 2
    assert [o.candidate_id for o in result.outcomes] == ["cand_a", "cand_b"]
    for o in result.outcomes:
        assert isinstance(o.report, ScreeningReport)


def test_default_top_k_is_used_when_omitted(monkeypatch, job_description, candidate_factory):
    c = candidate_factory(id="cand_a", name="Ann")
    captured = {}
    monkeypatch.setattr(
        "app.services.orchestration.search_candidates",
        lambda db, **kw: captured.update(kw) or [RankedCandidate(candidate=c, distance=0.1)],
    )
    monkeypatch.setattr(
        "app.services.screening_service.ScreeningService.screen_candidates",
        _fake_screen([RankedCandidate(candidate=c, distance=0.1)]),
    )

    match_and_screen_candidates(
        None, engine=None, embed_service=None, llm_client=None,
        job_description=job_description,
    )

    assert captured["top_k"] == 5  # DEFAULT_TOP_K


def test_retrieval_errors_propagate(monkeypatch, job_description):
    from app.services.errors import VectorIndexError

    monkeypatch.setattr(
        "app.services.orchestration.search_candidates",
        lambda db, **kw: (_ for _ in ()).throw(
            VectorIndexError("No candidate embeddings are indexed.")
        ),
    )

    with pytest.raises(VectorIndexError, match="indexed"):
        match_and_screen_candidates(
            None, engine=None, embed_service=None, llm_client=None,
            job_description=job_description,
        )


@pytest.mark.parametrize("jd", ["", "   ", None])
def test_empty_jd_rejected_before_retrieval(monkeypatch, jd):
    called = []

    def fake_search(db, **kw):
        called.append(True)
        return []

    monkeypatch.setattr("app.services.orchestration.search_candidates", fake_search)

    with pytest.raises(ScreeningInputError, match="Job description"):
        match_and_screen_candidates(
            None, engine=None, embed_service=None, llm_client=None,
            job_description=jd,
        )
    assert called == []