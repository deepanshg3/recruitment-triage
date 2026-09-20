"""Isolated Gemini LLM client for structured output.

Responsibilities (and only these):
- read API key + model from settings
- call Gemini `generate_content` with a Pydantic response schema
- return a validated Pydantic instance

No screening/prompt logic lives here; that is in prompts.py and
screening_service.py.

Structured-output mechanism (verified against the installed SDK,
google-genai 2.24.0):
  config = GenerateContentConfig(
      response_mime_type="application/json",
      response_schema=SomePydanticModel,   # direct Pydantic structured output
      system_instruction=...,
  )
  response = client.models.generate_content(model, contents, config)
  response.parsed                       # SomePydanticModel instance

The SDK's own `parsed` population silently swallows JSONDecodeError /
ValidationError and leaves `parsed=None`, so this client treats a missing
`parsed` as a malformed result and re-validates the raw text itself (strict).
Parsing/validation is isolated to `_parse_structured` below.
"""

import logging
import time
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.services.errors import (
    ScreeningApiError,
    ScreeningConfigurationError,
    ScreeningResponseError,
)

logger = logging.getLogger(__name__)

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


class GeminiLLMClient:
    """Adapter around the Google GenAI SDK for producing structured output.

    Errors are typed (ScreeningConfigurationError / ScreeningApiError /
    ScreeningResponseError) and never contain secrets.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        max_retries: int = 1,
        sleep_func=time.sleep,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.gemini_api_key
        self._model = model if model is not None else settings.gemini_llm_model
        # Very small bounded retry for transient API failures (configurable).
        self._max_retries = max(int(max_retries) if max_retries > 0 else 0, 0)
        self._sleep = sleep_func
        self._client = None

    @property
    def model(self) -> str:
        return self._model

    def check_configured(self) -> None:
        """Raise ScreeningConfigurationError if the service cannot be used."""
        self._ensure_configured()

    def _ensure_configured(self) -> None:
        if not self._api_key or not self._api_key.strip():
            raise ScreeningConfigurationError(
                "Gemini LLM API key is not configured. Set GEMINI_API_KEY in "
                "the project .env file (or environment) and re-run."
            )
        if not self._model or not self._model.strip():
            raise ScreeningConfigurationError(
                "Gemini LLM model is not configured. Set GEMINI_LLM_MODEL."
            )

    def _get_client(self):
        if self._client is None:
            from google import genai

            logger.info("Initializing Gemini LLM client (model=%s)", self._model)
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def generate_structured(
        self,
        *,
        response_schema: type[ResponseModel],
        system_instruction: str,
        user_content: str,
    ) -> ResponseModel:
        """Call Gemini and return a validated `response_schema` instance.

        Raises ScreeningConfigurationError / ScreeningApiError /
        ScreeningResponseError with application-level messages.
        """
        self._ensure_configured()
        if not user_content or not user_content.strip():
            raise ScreeningResponseError("Cannot screen without user content.")

        from google.genai import types

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
            system_instruction=system_instruction,
            temperature=0.0,
        )

        attempts = 0
        while True:
            attempts += 1
            try:
                logger.debug(
                    "generate_content(model=%s, user_content=%d chars)",
                    self._model,
                    len(user_content),
                )
                response = self._get_client().models.generate_content(
                    model=self._model,
                    contents=user_content,
                    config=config,
                )
            except Exception as exc:
                if attempts <= self._max_retries:
                    logger.warning(
                        "LLM request transient failure (attempt %d, %s); retrying",
                        attempts,
                        type(exc).__name__,
                    )
                    self._sleep(1.0 * attempts)
                    continue
                logger.error(
                    "LLM generate_content failed for model %s: %s",
                    self._model,
                    type(exc).__name__,
                )
                raise ScreeningApiError(
                    "Gemini LLM request failed "
                    f"({type(exc).__name__}). Check the API key, network, "
                    "quota and rate limits before retrying."
                ) from exc

            return self._parse_structured(response, response_schema)

    def _parse_structured(
        self, response, response_schema: type[ResponseModel]
    ) -> ResponseModel:
        """Single place where the SDK response is turned into a validated model."""
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, response_schema):
            return parsed

        # SDK left parsed=None (silent JSON/validation swallow) or returned a
        # non-model — re-parse the raw text strictly so we never return None.
        text = getattr(response, "text", None)
        if not text or not text.strip():
            raise ScreeningResponseError(
                "Gemini LLM returned an empty or unparseable response "
                "(model produced no text)."
            )
        try:
            return response_schema.model_validate_json(text)
        except ValidationError as exc:
            raise ScreeningResponseError(
                "Gemini LLM returned structured output that failed validation: "
                f"{exc}".replace("\n", " ")
            ) from exc
        except ValueError as exc:
            raise ScreeningResponseError(
                "Gemini LLM did not return valid JSON structured output."
            ) from exc