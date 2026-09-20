"""GeminiLLMClient tests (Prompt 3, section C). All SDK calls are mocked."""

import httpx
import pytest

from app.schemas.screening import ScreeningReport
from app.services.errors import (
    ScreeningApiError,
    ScreeningConfigurationError,
    ScreeningResponseError,
)
from app.services.llm_client import GeminiLLMClient

SYSTEM = "You are a recruiting assistant."
PROMPT = "JOB DESCRIPTION:\nBackend Engineer\n\nCANDIDATE:\nname: Ada"


class FakeResponse:
    """Minimal stand-in for GenerateContentResponse (parsed/text only)."""

    def __init__(self, parsed=None, text=None):
        self.parsed = parsed
        self.text = text


def _report_json():
    return (
        '{"candidate_id": "cand_001", "candidate_name": "Ada Lovelace", '
        '"strengths": ["Python"], "gaps": ["Docker not specified"], '
        '"evidence": ["Skills list includes Python"], '
        '"interview_questions": ["Design a rate limiter."]}'
    )


class FakeGenAIClient:
    """Pretends to be google.genai.Client: exposes models.generate_content.

    `exc` is raised for the first `fail_count` calls, then `responses` are
    served in order.
    """

    def __init__(self, responses=None, exc=None, fail_count=0):
        self.responses = list(responses or [])
        self.exc = exc
        self.fail_count = fail_count
        self.calls = []
        self.models = self  # generate_content lives on the same fake object

    def generate_content(self, *, model, contents, config=None):
        self.calls.append((model, contents, config))
        if self.exc is not None and self.fail_count > 0:
            self.fail_count -= 1
            raise self.exc
        if self.responses:
            return self.responses.pop(0)
        raise AssertionError("No fake response for generate_content call")


def _client(fake, **kwargs):
    llm = GeminiLLMClient(api_key="test-key", model="test-model", **kwargs)
    llm._get_client = lambda: fake
    return llm


def test_success_returns_parsed_pydantic_instance():
    report = ScreeningReport.model_validate_json(_report_json())
    llm = _client(FakeGenAIClient(responses=[FakeResponse(parsed=report)]))

    result = llm.generate_structured(
        response_schema=ScreeningReport,
        system_instruction=SYSTEM,
        user_content=PROMPT,
    )

    assert isinstance(result, ScreeningReport)
    assert result.candidate_id == "cand_001"
    assert llm._get_client().calls[0][0] == "test-model"
    assert llm._get_client().calls[0][1] == PROMPT


def test_success_falls_back_when_parsed_is_none_but_text_is_valid():
    llm = _client(
        FakeGenAIClient(responses=[FakeResponse(parsed=None, text=_report_json())])
    )

    result = llm.generate_structured(
        response_schema=ScreeningReport,
        system_instruction=SYSTEM,
        user_content=PROMPT,
    )

    assert isinstance(result, ScreeningReport)
    assert result.candidate_name == "Ada Lovelace"


def test_api_failure_raises_screening_api_error():
    from google.genai import errors

    llm = _client(
        FakeGenAIClient(
            exc=errors.APIError(code=429, response_json={"message": "quota exceeded"}),
            fail_count=1,
        )
    )
    with pytest.raises(ScreeningApiError, match="request failed"):
        llm.generate_structured(
            response_schema=ScreeningReport,
            system_instruction=SYSTEM,
            user_content=PROMPT,
        )


def test_network_timeout_raises_screening_api_error():
    llm = _client(
        FakeGenAIClient(exc=httpx.TimeoutException("timed out"), fail_count=1)
    )
    with pytest.raises(ScreeningApiError, match="request failed"):
        llm.generate_structured(
            response_schema=ScreeningReport,
            system_instruction=SYSTEM,
            user_content=PROMPT,
        )


def test_malformed_json_raises_screening_response_error():
    llm = _client(
        FakeGenAIClient(
            responses=[FakeResponse(parsed=None, text="this is not json {")]
        )
    )
    with pytest.raises(ScreeningResponseError, match="json|structured"):
        llm.generate_structured(
            response_schema=ScreeningReport,
            system_instruction=SYSTEM,
            user_content=PROMPT,
        )


def test_validation_failure_raises_screening_response_error():
    bad = '{"candidate_id": "c1"}'  # missing required fields
    llm = _client(FakeGenAIClient(responses=[FakeResponse(parsed=None, text=bad)]))
    with pytest.raises(ScreeningResponseError, match="validation"):
        llm.generate_structured(
            response_schema=ScreeningReport,
            system_instruction=SYSTEM,
            user_content=PROMPT,
        )


def test_empty_text_raises_screening_response_error():
    llm = _client(FakeGenAIClient(responses=[FakeResponse(parsed=None, text="")]))
    with pytest.raises(ScreeningResponseError, match="empty"):
        llm.generate_structured(
            response_schema=ScreeningReport,
            system_instruction=SYSTEM,
            user_content=PROMPT,
        )


def test_missing_api_key_raises_screening_configuration_error():
    llm = GeminiLLMClient(api_key="   ", model="test-model")
    with pytest.raises(ScreeningConfigurationError, match="GEMINI_API_KEY"):
        llm.generate_structured(
            response_schema=ScreeningReport,
            system_instruction=SYSTEM,
            user_content=PROMPT,
        )


def test_missing_model_raises_screening_configuration_error():
    llm = GeminiLLMClient(api_key="test-key", model=" ")
    with pytest.raises(ScreeningConfigurationError, match="GEMINI_LLM_MODEL"):
        llm.generate_structured(
            response_schema=ScreeningReport,
            system_instruction=SYSTEM,
            user_content=PROMPT,
        )


def test_transient_failure_is_retried_then_succeeds():
    from google.genai import errors

    report = ScreeningReport.model_validate_json(_report_json())
    fake = FakeGenAIClient(
        exc=errors.APIError(code=503, response_json={"message": "unavailable"}),
        fail_count=1,
        responses=[FakeResponse(parsed=report)],
    )
    calls = []
    llm = GeminiLLMClient(
        api_key="k", model="m", max_retries=1, sleep_func=calls.append
    )
    llm._get_client = lambda: fake

    result = llm.generate_structured(
        response_schema=ScreeningReport,
        system_instruction=SYSTEM,
        user_content=PROMPT,
    )

    assert isinstance(result, ScreeningReport)
    assert len(fake.calls) == 2  # failed attempt + retry
    assert len(calls) == 1  # slept exactly once


def test_retry_exhausted_raises_screening_api_error():
    from google.genai import errors

    fake = FakeGenAIClient(
        exc=errors.APIError(code=500, response_json={"message": "boom"}),
        fail_count=2,
    )
    llm = GeminiLLMClient(api_key="k", model="m", max_retries=1, sleep_func=lambda _: None)
    llm._get_client = lambda: fake

    with pytest.raises(ScreeningApiError):
        llm.generate_structured(
            response_schema=ScreeningReport,
            system_instruction=SYSTEM,
            user_content=PROMPT,
        )
    assert len(fake.calls) == 2


def test_error_message_never_contains_api_key():
    fake = FakeGenAIClient(exc=RuntimeError("boom"), fail_count=1)
    llm = _client(fake)
    with pytest.raises(ScreeningApiError) as excinfo:
        llm.generate_structured(
            response_schema=ScreeningReport,
            system_instruction=SYSTEM,
            user_content=PROMPT,
        )
    assert "test-key" not in str(excinfo.value)
    assert "boom" not in str(excinfo.value)