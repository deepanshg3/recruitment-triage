"""Application-level errors for the embedding / vector-search pipeline.

These are distinct from HTTP errors: this stage has no REST endpoints, so the
pipeline reports failures through these exceptions and the CLI/test layers.
"""


class EmbeddingError(Exception):
    """Base class for all embedding / vector pipeline errors."""


class EmbeddingConfigurationError(EmbeddingError):
    """The embedding service is misconfigured (e.g. missing API key)."""


class EmbeddingApiError(EmbeddingError):
    """The upstream Gemini API call failed (network, auth, rate limit, 5xx)."""


class EmbeddingResponseError(EmbeddingError):
    """Gemini returned a malformed, empty, or incompatible embedding."""


class VectorIndexError(EmbeddingError):
    """The sqlite-vec index is inconsistent with the requested operation
    (dimension mismatch, missing index, etc.)."""


class RetrievalInputError(EmbeddingError):
    """Invalid retrieval input (empty job description, bad top_k)."""


class VectorDimensionMismatchError(VectorIndexError):
    """Index dimension differs from the embedding dimension being stored."""


class ScreeningError(Exception):
    """Base class for all LLM screening pipeline errors."""


class ScreeningConfigurationError(ScreeningError):
    """The LLM service is misconfigured (e.g. missing/blank API key)."""


class ScreeningApiError(ScreeningError):
    """The Gemini LLM request failed (network, auth, rate limit, timeout, 5xx)."""


class ScreeningResponseError(ScreeningError):
    """The LLM response was malformed or failed Pydantic validation."""


class ScreeningInputError(ScreeningError):
    """Invalid screening input (empty JD, missing/invalid candidate)."""


class CandidateNotFoundError(Exception):
    """A candidate with the requested id does not exist."""


class InvalidQueryError(Exception):
    """A client-supplied filter/sort/pagination value is invalid (HTTP 400)."""