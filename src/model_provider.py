from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass
class ProviderConfig:
    """Provider-neutral model configuration shared by both agents."""

    provider: str
    model_name: str
    temperature: float
    api_key: str | None = None
    base_url: str | None = None


def normalize_provider(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    aliases = {
        "anthorpic": "anthropic",
        "google": "gemini",
        "google_genai": "gemini",
        "open_ai": "openai",
        "open_router": "openrouter",
        "openai_compatible": "custom",
    }
    normalized = aliases.get(normalized, normalized)
    supported = {"openai", "custom", "gemini", "anthropic", "ollama", "openrouter"}
    if normalized not in supported:
        raise ValueError(f"Unsupported provider {value!r}. Choose one of: {', '.join(sorted(supported))}")
    return normalized


def build_chat_model(config: ProviderConfig):
    """Instantiate the selected provider lazily so offline mode stays lightweight."""

    provider = normalize_provider(config.provider)
    common = {"model": config.model_name, "temperature": config.temperature}
    try:
        if provider in {"openai", "custom"}:
            from langchain_openai import ChatOpenAI
            if config.api_key:
                common["api_key"] = config.api_key
            if provider == "custom":
                if not config.base_url:
                    raise ValueError("CUSTOM_BASE_URL is required for the custom provider")
                common["base_url"] = config.base_url
            return ChatOpenAI(**common)
        if provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            if config.api_key:
                common["google_api_key"] = config.api_key
            return ChatGoogleGenerativeAI(**common)
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            if config.api_key:
                common["api_key"] = config.api_key
            return ChatAnthropic(**common)
        if provider == "ollama":
            from langchain_ollama import ChatOllama
            if config.base_url:
                common["base_url"] = config.base_url
            return ChatOllama(**common)
        from langchain_openrouter import ChatOpenRouter
        if config.api_key:
            common["api_key"] = config.api_key
        return ChatOpenRouter(**common)
    except ImportError as exc:
        package_hints = {
            "openai": "langchain-openai", "custom": "langchain-openai",
            "gemini": "langchain-google-genai", "anthropic": "langchain-anthropic",
            "ollama": "langchain-ollama", "openrouter": "langchain-openrouter",
        }
        raise RuntimeError(
            f"Provider {provider!r} requires optional package {package_hints[provider]!r}."
        ) from exc


def provider_has_runtime_credentials(config: ProviderConfig) -> bool:
    provider = normalize_provider(config.provider)
    if provider == "ollama":
        return bool(config.base_url or os.getenv("OLLAMA_HOST"))
    if provider == "custom":
        return bool(config.base_url)
    return bool(config.api_key)
