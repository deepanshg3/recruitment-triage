from types import SimpleNamespace

import pytest

from app.services.embedding_service import GeminiEmbeddingService
from app.services.errors import (
    EmbeddingApiError,
    EmbeddingConfigurationError,
    EmbeddingResponseError,
)


class FakeModels:
    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error

    def embed_content(self, model=None, contents=None):
        if self._error is not None:
            raise self._error
        return self._response


class FakeClient:
    def __init__(self, response=None, error=None):
        self.models = FakeModels(response=response, error=error)


def sdk_response(values):
    embedding = SimpleNamespace(values=values, statistics=None)
    return SimpleNamespace(embeddings=[embedding])


def sdk_response_with(values_list):
    return SimpleNamespace(
        embeddings=[SimpleNamespace(values=v, statistics=None) for v in values_list]
    )


def service_with(response=None, error=None, **kwargs):
    service = GeminiEmbeddingService(api_key="test-key", **kwargs)
    service._client = FakeClient(response=response, error=error)
    return service


def test_valid_embedding():
    service = service_with(response=sdk_response([0.1, 0.2, 0.3]))
    assert service.embed("backend engineer") == [0.1, 0.2, 0.3]


def test_missing_api_key_raises():
    service = GeminiEmbeddingService(api_key="")
    with pytest.raises(EmbeddingConfigurationError, match="GEMINI_API_KEY"):
        service.embed("text")

    whitespace = GeminiEmbeddingService(api_key="   ")
    with pytest.raises(EmbeddingConfigurationError, match="GEMINI_API_KEY"):
        whitespace.embed("text")


def test_api_request_failure_is_wrapped():
    service = service_with(error=RuntimeError("network down"))
    with pytest.raises(EmbeddingApiError, match="RuntimeError"):
        service.embed("text")


def test_api_key_never_leaks_into_error():
    service = GeminiEmbeddingService(api_key="super-secret-key-123")
    service._client = FakeClient(error=RuntimeError("boom"))
    with pytest.raises(EmbeddingApiError) as excinfo:
        service.embed("text")
    assert "super-secret-key-123" not in str(excinfo.value)


def test_missing_embeddings_field():
    service = service_with(response=SimpleNamespace(embeddings=None))
    with pytest.raises(EmbeddingResponseError, match="no embeddings"):
        service.embed("text")


def test_empty_embeddings_list():
    service = service_with(response=SimpleNamespace(embeddings=[]))
    with pytest.raises(EmbeddingResponseError):
        service.embed("text")


def test_multiple_embeddings_returned():
    service = service_with(response=sdk_response_with([[0.1], [0.2]]))
    with pytest.raises(EmbeddingResponseError, match="exactly 1"):
        service.embed("text")


def test_malformed_embedding_missing_values():
    service = service_with(
        response=SimpleNamespace(embeddings=[SimpleNamespace(values=None)])
    )
    with pytest.raises(EmbeddingResponseError):
        service.embed("text")


def test_non_numeric_values():
    service = service_with(response=sdk_response(["a", "b"]))
    with pytest.raises(EmbeddingResponseError, match="not numeric"):
        service.embed("text")


def test_empty_vector_rejected():
    service = service_with(response=sdk_response([]))
    with pytest.raises(EmbeddingResponseError, match="empty"):
        service.embed("text")


def test_unexpected_dimension_rejected():
    service = service_with(response=sdk_response([0.1, 0.2, 0.3]), expected_dimension=5)
    with pytest.raises(EmbeddingResponseError, match="dimension 3"):
        service.embed("text")


def test_empty_and_whitespace_text_rejected():
    service = service_with(response=sdk_response([0.1]))
    with pytest.raises(EmbeddingResponseError, match="empty"):
        service.embed("")
    with pytest.raises(EmbeddingResponseError, match="empty"):
        service.embed("   \n\t  ")