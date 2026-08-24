from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Google AI API key — maps to GOOGLE_API_KEY in .env
    # Get a free key at https://aistudio.google.com
    google_api_key: str

    # Model used for structured extraction via response_schema.
    # Default: gemini-3.5-flash — GA as of mid-2026, optimised for structured output.
    # Override to gemini-3.5-pro for highest accuracy at higher cost.
    llm_model: str = "gemini-3.5-flash"

    # PostgreSQL connection string
    database_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # Allow extra fields so the file can carry other vars (e.g. future keys)
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.
    Using a factory (rather than a module-level singleton) keeps imports
    side-effect-free and makes settings trivially overridable in tests via
    `patch("src.config.get_settings", return_value=Settings(...))`.
    """
    return Settings()
