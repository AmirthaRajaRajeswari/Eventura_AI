"""
Eventura AI — centralised application configuration.

All secrets and tuneable parameters are read from environment variables.
Import `settings` from this module anywhere in the application.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://eventura:eventura@localhost:5432/eventura"
    )
    sync_database_url: str = (
        "postgresql+psycopg2://eventura:eventura@localhost:5432/eventura"
    )

    # ── LLM ───────────────────────────────────
    llm_provider: Literal["gemini", "groq", "ollama"] = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    groq_api_key: str = ""
    groq_model: str = "llama3-70b-8192"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # ── Embeddings ────────────────────────────
    embedding_model: str = "all-MiniLM-L6-v2"

    # ── Observability ─────────────────────────
    observability_provider: Literal["langfuse", "langsmith", "none"] = "none"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    langsmith_api_key: str = ""
    langsmith_project: str = "eventura-ai"

    # ── Mock vendor marketplace ───────────────
    mock_vendor_base_url: str = "http://localhost:8001"

    # ── WhatsApp ──────────────────────────────
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""

    # ── Weather ───────────────────────────────
    weather_api_key: str = ""

    # ── App ───────────────────────────────────
    app_env: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
