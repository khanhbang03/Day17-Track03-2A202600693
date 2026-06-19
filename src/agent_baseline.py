from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config import LabConfig, load_config
from memory_store import estimate_tokens, extract_profile_updates
from model_provider import build_chat_model, provider_has_runtime_credentials


@dataclass
class SessionState:
    messages: list[dict[str, str]] = field(default_factory=list)
    token_usage: int = 0
    prompt_tokens_processed: int = 0


class BaselineAgent:
    """Within-thread memory only; intentionally no persistent profile."""

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.sessions: dict[str, SessionState] = {}
        self.langchain_agent = self._maybe_build_langchain_agent()

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        del user_id
        return self._reply_offline(thread_id, message) if self.langchain_agent is None else self._reply_live(thread_id, message)

    def token_usage(self, thread_id: str) -> int:
        return self.sessions.get(thread_id, SessionState()).token_usage

    def prompt_token_usage(self, thread_id: str) -> int:
        return self.sessions.get(thread_id, SessionState()).prompt_tokens_processed

    def compaction_count(self, thread_id: str) -> int:
        return 0

    def _reply_offline(self, thread_id: str, message: str) -> dict[str, Any]:
        state = self.sessions.setdefault(thread_id, SessionState())
        state.messages.append({"role": "user", "content": message})
        prompt_tokens = estimate_tokens("\n".join(item["content"] for item in state.messages))
        state.prompt_tokens_processed += prompt_tokens
        lower = message.lower()
        requested = []
        for key, signals in [
            ("name", ("tên", "là ai")),
            ("profession", ("nghề", "làm gì")),
            ("location", ("ở đâu", "nơi ở")),
            ("response_style", ("style", "kiểu trả lời")),
            ("favorite_drink", ("đồ uống",)),
            ("favorite_food", ("món ăn",)),
            ("pet", ("nuôi con gì", "corgi")),
            ("interests", ("mối quan tâm",)),
        ]:
            if any(signal in lower for signal in signals):
                requested.append(key)
        facts = self._thread_facts(state.messages)
        values = [facts[key] for key in requested if key in facts]
        answer = "; ".join(values) + "." if values else (
            "Mình chưa có thông tin đó trong thread này." if requested
            else "Mình đã ghi nhận trong thread hiện tại."
        )
        state.messages.append({"role": "assistant", "content": answer})
        output_tokens = estimate_tokens(answer)
        state.token_usage += output_tokens
        return {
            "answer": answer, "agent_tokens": output_tokens,
            "prompt_tokens": prompt_tokens, "thread_id": thread_id,
        }

    @staticmethod
    def _thread_facts(messages: list[dict[str, str]]) -> dict[str, str]:
        facts: dict[str, str] = {}
        for item in messages:
            if item["role"] == "user":
                facts.update(extract_profile_updates(item["content"]))
        return facts

    def _maybe_build_langchain_agent(self):
        if self.force_offline or not provider_has_runtime_credentials(self.config.model):
            return None
        try:
            return build_chat_model(self.config.model)
        except (RuntimeError, ValueError):
            return None

    def _reply_live(self, thread_id: str, message: str) -> dict[str, Any]:
        state = self.sessions.setdefault(thread_id, SessionState())
        state.messages.append({"role": "user", "content": message})
        prompt_tokens = estimate_tokens("\n".join(item["content"] for item in state.messages))
        state.prompt_tokens_processed += prompt_tokens
        response = self.langchain_agent.invoke(state.messages)
        answer = response.content if hasattr(response, "content") else str(response)
        state.messages.append({"role": "assistant", "content": answer})
        output_tokens = estimate_tokens(answer)
        state.token_usage += output_tokens
        return {"answer": answer, "agent_tokens": output_tokens, "prompt_tokens": prompt_tokens}
