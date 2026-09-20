"""POST /match API tests. The AI pipeline is fully mocked — zero Gemini calls."""

import pytest

from app.schemas.screening import ScreeningReport
from app.services.errors import (
    ScreeningApiError,
    ScreeningConfigurationError,
    ScreeningResponseError,
    VectorIndexError,
)
from app.services.orchestration import MatchAndScreenResult
from app.services.retrieval import RankedCandidate
from app.services.screening_service import ScreeningFailure, ScreeningSuccess


def _report(candidate_id, name):
    return ScreeningReport(
        candidate_id=candidate_id,
        candidate_name=name,
        strengths=["Python expertise"],
        gaps=["Containerization not specified"],
        evidence=["Skills list includes Python"],
        interview_questions=["Describe a production API you shipped."],
    )


def _ranked(candidates):
    return [
        RankedCandidate(candidate=c, distance=i / 10.0)
        for i, c in enumerate(candidates)
    ]


def _make_result(candidates, job_description, top_k):
    outcomes = [
        ScreeningSuccess(candidate_id=c.id, report=_report(c.id, c.name))
        for c in candidates
    ]
    return MatchAndScreenResult(
        job_description=job_description,
        top_k_requested=top_k,
        retrieved=_ranked(candidates),
        outcomes=outcomes,
    )


def _patch_orchestrator(monkeypatch, result_factory, calls):
    def fake(db, *, engine, embed_service, llm_client, job_description, top_k=5):
        calls.append(top_k)
        return result_factory(job_description, top_k)

    monkeypatch.setattr(
        "app.api.routes.match.match_and_screen_candidates", fake
    )


JOB_DESCRIPTION = (
    "Backend Engineer - Build production REST APIs with Python and FastAPI, "
    "own PostgreSQL schema design, require 2+ years of experience, comfortable "
    "with Docker and working in a startup."
)


def test_valid_jd_default_top_k(api_client, monkeypatch, candidate_factory):
    cands = [
        candidate_factory(id="cand_a", name="Alice"),
        candidate_factory(id="cand_b", name="Bob"),
    ]
    calls = []
    _patch_orchestrator(monkeypatch, lambda jd, k: _make_result(cands, jd, k), calls)

    r = api_client.post("/match", json={"job_description": JOB_DESCRIPTION})

    assert r.status_code == 200
    body = r.json()
    assert body["job_description"] == JOB_DESCRIPTION
    assert body["top_k_requested"] == 5
    assert calls == [5]  # default top_k passed to the orchestrator
    assert len(body["results"]) == 2
    item = body["results"][0]
    assert item["candidate"]["id"] == "cand_a"
    assert item["retrieval_distance"] == 0.0
    assert item["screening"]["candidate_id"] == "cand_a"
    assert item["screening"]["strengths"] == ["Python expertise"]
    assert item["screening_error"] is None


def test_custom_top_k(api_client, monkeypatch, candidate_factory):
    cands = [candidate_factory(id="cand_a", name="Alice")]
    calls = []
    _patch_orchestrator(monkeypatch, lambda jd, k: _make_result(cands, jd, k), calls)

    r = api_client.post(
        "/match", json={"job_description": JOB_DESCRIPTION, "top_k": 3}
    )

    assert r.status_code == 200
    assert calls == [3]


@pytest.mark.parametrize(
    "payload",
    [
        {},  # missing job_description
        {"top_k": 5},  # missing job_description
        {"job_description": ""},  # empty
        {"job_description": "   \n  "},  # whitespace only
        {"job_description": "JD", "top_k": 0},
        {"job_description": "JD", "top_k": -1},
        {"job_description": "JD", "top_k": 51},  # exceeds MAX_TOP_K
        {"job_description": "JD", "top_k": "lots"},
    ],
)
def test_invalid_payload_returns_422(api_client, monkeypatch, payload):
    def boom(db, **kw):
        raise AssertionError("orchestrator must not be called for invalid payload")

    monkeypatch.setattr("app.api.routes.match.match_and_screen_candidates", boom)
    r = api_client.post("/match", json=payload)
    assert r.status_code == 422


def test_successful_structured_response_shape(api_client, monkeypatch, candidate_factory):
    cands = [candidate_factory(id="cand_a", name="Alice")]
    _patch_orchestrator(
        monkeypatch, lambda jd, k: _make_result(cands, jd, k), []
    )
    body = api_client.post(
        "/match", json={"job_description": JOB_DESCRIPTION}
    ).json()
    assert set(body.keys()) == {"job_description", "top_k_requested", "results"}
    assert set(body["results"][0].keys()) == {
        "candidate",
        "retrieval_distance",
        "screening",
        "screening_error",
    }


def test_partial_screening_failure_is_explicit(api_client, monkeypatch, candidate_factory):
    cands = [
        candidate_factory(id="cand_a", name="Alice"),
        candidate_factory(id="cand_b", name="Bob"),
    ]
    outcomes = [
        ScreeningFailure(
            candidate_id="cand_a",
            error_type="ScreeningApiError",
            message="simulated LLM failure",
        ),
        ScreeningSuccess(candidate_id="cand_b", report=_report("cand_b", "Bob")),
    ]
    result = MatchAndScreenResult(
        job_description=JOB_DESCRIPTION,
        top_k_requested=2,
        retrieved=_ranked(cands),
        outcomes=outcomes,
    )

    def fake(db, **kw):
        return result

    monkeypatch.setattr("app.api.routes.match.match_and_screen_candidates", fake)

    body = api_client.post(
        "/match", json={"job_description": JOB_DESCRIPTION, "top_k": 2}
    ).json()

    failed, ok = body["results"]
    assert failed["candidate"]["id"] == "cand_a"
    assert failed["screening"] is None
    assert "ScreeningApiError" in failed["screening_error"]
    assert ok["candidate"]["id"] == "cand_b"
    assert isinstance(ok["screening"], dict)
    assert ok["screening_error"] is None


def test_screening_configuration_error_maps_to_503(api_client, monkeypatch):
    def raise_config(db, **kw):
        raise ScreeningConfigurationError(
            "Gemini LLM API key is not configured. Set GEMINI_API_KEY."
        )

    monkeypatch.setattr("app.api.routes.match.match_and_screen_candidates", raise_config)
    r = api_client.post("/match", json={"job_description": JOB_DESCRIPTION})
    assert r.status_code == 503
    assert "GEMINI_API_KEY" in r.json()["detail"]


def test_screening_api_error_maps_to_503(api_client, monkeypatch):
    def raise_api(db, **kw):
        raise ScreeningApiError("Gemini LLM request failed (APIError).")

    monkeypatch.setattr("app.api.routes.match.match_and_screen_candidates", raise_api)
    r = api_client.post("/match", json={"job_description": JOB_DESCRIPTION})
    assert r.status_code == 503
    assert "unavailable" in r.json()["detail"]


def test_malformed_ai_response_maps_to_502(api_client, monkeypatch):
    def raise_malformed(db, **kw):
        raise ScreeningResponseError("Gemini LLM returned invalid structured output.")

    monkeypatch.setattr("app.api.routes.match.match_and_screen_candidates", raise_malformed)
    r = api_client.post("/match", json={"job_description": JOB_DESCRIPTION})
    assert r.status_code == 502


def test_missing_embeddings_index_maps_to_503(api_client, monkeypatch):
    def raise_index(db, **kw):
        raise VectorIndexError(
            "No candidate embeddings are indexed. Run `python -m app.db.embed_candidates` first."
        )

    monkeypatch.setattr("app.api.routes.match.match_and_screen_candidates", raise_index)
    r = api_client.post("/match", json={"job_description": JOB_DESCRIPTION})
    assert r.status_code == 503
    assert "embed_candidates" in r.json()["detail"]


def test_no_real_gemini_call_occurs(
    api_client, monkeypatch, candidate_factory
):
    cands = [candidate_factory(id="cand_a", name="Alice")]
    calls = []
    _patch_orchestrator(monkeypatch, lambda jd, k: _make_result(cands, jd, k), calls)

    # If any real AI service method were reached, fail loudly.
    monkeypatch.setattr(
        "app.services.embedding_service.GeminiEmbeddingService.embed",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("real embedding call attempted")
        ),
    )
    monkeypatch.setattr(
        "app.services.llm_client.GeminiLLMClient.generate_structured",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("real LLM call attempted")
        ),
    )

    api_client.post("/match", json={"job_description": JOB_DESCRIPTION})

    assert calls == [5]  # orchestrator invoked exactly once, fully mocked


def test_error_response_never_leaks_credentials(api_client, monkeypatch):
    def raise_config(db, **kw):
        raise ScreeningConfigurationError(
            "Gemini LLM API key 'AIza_Fake_Secret' is invalid."
        )

    monkeypatch.setattr("app.api.routes.match.match_and_screen_candidates", raise_config)
    r = api_client.post("/match", json={"job_description": JOB_DESCRIPTION})
    body = r.json()["detail"]
    assert "AIza_Fake_Secret" not in body  # key never echoed back