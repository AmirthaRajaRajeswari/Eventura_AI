"""
Observability integration for LLM calls.

Supports Langfuse and LangSmith through configuration.
Call `setup_observability()` at application startup.
"""

from __future__ import annotations

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


def setup_observability() -> None:
    provider = settings.observability_provider

    if provider == "langfuse":
        _setup_langfuse()
    elif provider == "langsmith":
        _setup_langsmith()
    else:
        logger.info("Observability disabled", provider=provider)


def _setup_langfuse() -> None:
    try:
        from langfuse.callback import CallbackHandler  # noqa: F401

        if not settings.langfuse_public_key or not settings.langfuse_secret_key:
            logger.warning(
                "Langfuse keys not set — observability will be disabled"
            )
            return

        logger.info(
            "Langfuse observability enabled",
            host=settings.langfuse_host,
        )
    except ImportError:
        logger.warning("langfuse package not installed — skipping")


def _setup_langsmith() -> None:
    import os

    if not settings.langsmith_api_key:
        logger.warning("LANGSMITH_API_KEY not set — observability will be disabled")
        return

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project

    logger.info(
        "LangSmith observability enabled",
        project=settings.langsmith_project,
    )


def get_langfuse_callback():
    """Return a Langfuse callback handler if configured, else None."""
    if settings.observability_provider != "langfuse":
        return None
    try:
        from langfuse.callback import CallbackHandler

        return CallbackHandler(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except Exception as e:
        logger.warning("Could not create Langfuse handler", error=str(e))
        return None
