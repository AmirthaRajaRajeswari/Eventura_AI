"""
LLM provider abstraction for Eventura AI.

Switching providers requires only changing the LLM_PROVIDER environment variable.
All agent code should call `get_llm()` rather than importing a provider directly.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from langchain_core.language_models import BaseChatModel

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)

LLMProvider = Literal["gemini", "groq", "ollama"]


def get_llm(
    provider: LLMProvider | None = None,
    temperature: float = 0.1,
    max_tokens: int | None = None,
) -> BaseChatModel:
    """
    Return a LangChain BaseChatModel for the configured provider.

    Parameters
    ----------
    provider:
        Override the provider from settings. Used for evaluation runs.
    temperature:
        Sampling temperature. Default 0.1 for consistency.
    max_tokens:
        Optional token limit.
    """
    provider = provider or settings.llm_provider
    logger.debug("Creating LLM", provider=provider)

    if provider == "gemini":
        return _make_gemini(temperature, max_tokens)
    elif provider == "groq":
        return _make_groq(temperature, max_tokens)
    elif provider == "ollama":
        return _make_ollama(temperature, max_tokens)
    else:
        raise ValueError(f"Unknown LLM provider: {provider!r}")


def _make_gemini(temperature: float, max_tokens: int | None) -> BaseChatModel:
    from langchain_google_genai import ChatGoogleGenerativeAI

    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. "
            "Add it to your .env file or set LLM_PROVIDER=groq."
        )

    kwargs: dict = {
        "model": settings.gemini_model,
        "google_api_key": settings.gemini_api_key,
        "temperature": temperature,
        "convert_system_message_to_human": True,
    }
    if max_tokens:
        kwargs["max_output_tokens"] = max_tokens

    return ChatGoogleGenerativeAI(**kwargs)


def _make_groq(temperature: float, max_tokens: int | None) -> BaseChatModel:
    from langchain_groq import ChatGroq

    if not settings.groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. "
            "Add it to your .env file or set LLM_PROVIDER=gemini."
        )

    kwargs: dict = {
        "model_name": settings.groq_model,
        "groq_api_key": settings.groq_api_key,
        "temperature": temperature,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens

    return ChatGroq(**kwargs)


def _make_ollama(temperature: float, max_tokens: int | None) -> BaseChatModel:
    from langchain_community.chat_models import ChatOllama

    kwargs: dict = {
        "model": settings.ollama_model,
        "base_url": settings.ollama_base_url,
        "temperature": temperature,
    }
    if max_tokens:
        kwargs["num_predict"] = max_tokens

    return ChatOllama(**kwargs)


def get_llm_info() -> dict:
    """Return human-readable info about the active LLM provider."""
    provider = settings.llm_provider
    if provider == "gemini":
        return {"provider": "gemini", "model": settings.gemini_model}
    elif provider == "groq":
        return {"provider": "groq", "model": settings.groq_model}
    elif provider == "ollama":
        return {"provider": "ollama", "model": settings.ollama_model}
    return {"provider": provider, "model": "unknown"}
