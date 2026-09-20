"""Isolated Gemini embedding client.

Responsibilities (and only these):
- read API key + model from settings
- accept text, call Gemini, return a numeric vector (list[float])

This module performs NO database work. Storage/search live in
`vector_repository.py`.

The `google-genai` SDK response structure used here (verified against the
installed SDK, google-genai 2.x):

    response = client.models.embed_content(model=..., contents=text)
    response.embeddings            # list[ContentEmbedding], one per input
    response.embeddings[0].values  # list[float]  <- the vector

Do not depend on any undocumented attribute; `_parse_embedding` is the single
place that reads the SDK response shape.
"""

import logging

from app.core.config import settings
from app.services.errors import (
    EmbeddingApiError,
    EmbeddingConfigurationError,
    EmbeddingResponseError,
)

logger = logging.getLogger(__name__)


class GeminiEmbeddingService:
    """Client for the Gemini embeddings API. Predictable errors, no secrets logged."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        expected_dimension: int | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.gemini_api_key
        self._model = model if model is not None else settings.gemini_embedding_model
        # If set, every returned vector length is validated against it.
        self.expected_dimension = expected_dimension
        self._client = None

    @property
    def model(self) -> str:
        return self._model

    def check_configured(self) -> None:
        """Raise EmbeddingConfigurationError if the service cannot be used."""
        self._ensure_api_key()

    def _ensure_api_key(self) -> None:
        if not self._api_key or not self._api_key.strip():
            raise EmbeddingConfigurationError(
                "Gemini API key is not configured. Set GEMINI_API_KEY in the "
                "project .env file (or environment) and re-run."
            )
        if self._model is None or not self._model.strip():
            raise EmbeddingConfigurationError(
                "Gemini embedding model is not configured. Set GEMINI_EMBEDDING_MODEL."
            )

    def _get_client(self):
        if self._client is None:
            from google import genai

            logger.info("Initializing Gemini client (model=%s)", self._model)
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def embed(self, text: str) -> list[float]:
        """Embed `text` and return a flat list[float] vector.

        Raises EmbeddingConfigurationError / EmbeddingApiError /
        EmbeddingResponseError with application-level messages.
        """
        self._ensure_api_key()
        if not text or not text.strip():
            raise EmbeddingResponseError("Cannot embed empty text.")

        logger.debug("Embedding %d characters with model %s", len(text), self._model)
        try:
            response = self._get_client().models.embed_content(
                model=self._model, contents=text
            )
        except Exception as exc:  # SDK/network/HTTP/rate-limit failures
            logger.error(
                "Gemini embed_content failed for model %s: %s",
                self._model,
                type(exc).__name__,
            )
            raise EmbeddingApiError(
                f"Gemini embedding API request failed ({type(exc).__name__}). "
                "Check the API key, network connection and quota/rate limits "
                "before retrying."
            ) from exc

        vector = self._parse_embedding(response)
        self._validate_vector(vector)
        return vector

    def _parse_embedding(self, response) -> list[float]:
        """Extract the single embedding vector from an SDK response."""
        embeddings = getattr(response, "embeddings", None)
        if not embeddings:
            raise EmbeddingResponseError(
                "Gemini embedding response contained no embeddings."
            )
        if len(embeddings) != 1:
            raise EmbeddingResponseError(
                "Gemini embedding response contained "
                f"{len(embeddings)} embeddings; expected exactly 1."
            )

        values = getattr(embeddings[0], "values", None)
        if values is None:
            raise EmbeddingResponseError(
                "Gemini embedding response was malformed (missing values)."
            )

        statistics = getattr(embeddings[0], "statistics", None)
        if statistics is not None and getattr(statistics, "truncated", False):
            raise EmbeddingResponseError(
                "Gemini truncated the input before embedding. Shorten the text "
                "or increase the model token limit."
            )

        try:
            return [float(v) for v in values]
        except (TypeError, ValueError) as exc:
            raise EmbeddingResponseError(
                "Gemini embedding values were not numeric floats."
            ) from exc

    def _validate_vector(self, vector: list[float]) -> None:
        if not vector:
            raise EmbeddingResponseError("Gemini returned an empty embedding vector.")
        if self.expected_dimension is not None and len(vector) != self.expected_dimension:
            raise EmbeddingResponseError(
                f"Gemini embedding dimension {len(vector)} does not match the "
                f"index dimension {self.expected_dimension}. The embedding "
                "model/configuration changed and the vector index must be rebuilt."
            )