from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from model_provider import ProviderConfig, normalize_provider


@dataclass
class LabConfig:
    """Shared paths, compact-memory limits, and model provider settings."""

    base_dir: Path
    data_dir: Path
    state_dir: Path
    compact_threshold_tokens: int
    compact_keep_messages: int
    model: ProviderConfig
    judge_model: ProviderConfig


def load_config(base_dir: Path | None = None) -> LabConfig:
    """Load .env/environment settings and create writable state storage."""

    root = (base_dir or Path(__file__).resolve().parent.parent).resolve()
    try:
        from dotenv import load_dotenv
        load_dotenv(root / ".env", override=False)
    except ImportError:
        pass

    state_dir = Path(os.getenv("LAB_STATE_DIR", str(root / "state"))).resolve()
    state_dir.mkdir(parents=True, exist_ok=True)
    provider = normalize_provider(os.getenv("LLM_PROVIDER", "openai"))
    default_models = {
        "openai": "gpt-4o-mini", "custom": "local-model",
        "gemini": "gemini-2.0-flash", "anthropic": "claude-3-5-haiku-latest",
        "ollama": "llama3.2", "openrouter": "openai/gpt-4o-mini",
    }
    key_vars = {
        "openai": "OPENAI_API_KEY", "custom": "CUSTOM_API_KEY",
        "gemini": "GEMINI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
        "ollama": "", "openrouter": "OPENROUTER_API_KEY",
    }
    base_urls = {
        "custom": os.getenv("CUSTOM_BASE_URL"),
        "ollama": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "openrouter": os.getenv("OPENROUTER_BASE_URL"),
    }

    def make_provider(prefix: str) -> ProviderConfig:
        selected = normalize_provider(os.getenv(f"{prefix}_PROVIDER", provider))
        key_var = key_vars[selected]
        return ProviderConfig(
            provider=selected,
            model_name=os.getenv(f"{prefix}_MODEL", default_models[selected]),
            temperature=float(os.getenv(f"{prefix}_TEMPERATURE", "0")),
            api_key=os.getenv(key_var) if key_var else None,
            base_url=base_urls.get(selected),
        )

    return LabConfig(
        base_dir=root,
        data_dir=root / "data",
        state_dir=state_dir,
        compact_threshold_tokens=max(32, int(os.getenv("COMPACT_THRESHOLD_TOKENS", "1200"))),
        compact_keep_messages=max(2, int(os.getenv("COMPACT_KEEP_MESSAGES", "6"))),
        model=make_provider("LLM"),
        judge_model=make_provider("JUDGE"),
    )
