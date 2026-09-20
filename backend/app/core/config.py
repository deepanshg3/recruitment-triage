from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # backend/
REPO_ROOT = BASE_DIR.parent
DATA_DIR = REPO_ROOT / "data"


class Settings(BaseSettings):
    """Application configuration loaded from .env / environment variables."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Candidate Triage API"
    database_url: str = f"sqlite:///{BASE_DIR / 'recruitment.db'}"

    # Allowed CORS origins for the future React (Vite) frontend. Set as a JSON
    # list in .env if the dev origin differs (e.g. CORS_ORIGINS=["http://localhost:5173"]).
    cors_origins: list[str] = ["http://localhost:5173"]

    # Gemini configuration. The API key is read from .env / environment;
    # it must never be hardcoded.
    gemini_api_key: str = ""
    gemini_llm_model: str = "gemini-3.1-flash-lite"
    gemini_embedding_model: str = "models/embedding-001"
    # Optional fixed embedding dimension. None (empty in .env) means
    # "auto-detect from the first real embedding response". The sqlite-vec
    # index is created with exactly this dimension.
    embedding_dimension: int | None = None

    @field_validator("embedding_dimension", mode="before")
    @classmethod
    def _blank_dimension_to_none(cls, value):
        """.env may set EMBEDDING_DIMENSION= (blank) — treat as auto-detect."""
        return None if isinstance(value, str) and not value.strip() else value

    @property
    def candidates_data_path(self) -> Path:
        return DATA_DIR / "candidates.json"


settings = Settings()