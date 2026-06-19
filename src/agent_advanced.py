from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import LabConfig, load_config
from memory_store import CompactMemoryManager, UserProfileStore, estimate_tokens, extract_profile_updates
from model_provider import build_chat_model, provider_has_runtime_credentials


@dataclass
class AgentContext:
    user_id: str
    memory_path: str


class AdvancedAgent:
    """Short-term, persistent structured User.md, and bounded compact memory."""

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.profile_store = UserProfileStore(self.config.state_dir / "profiles")
        self.compact_memory = CompactMemoryManager(
            self.config.compact_threshold_tokens, self.config.compact_keep_messages
        )
        self.thread_tokens: dict[str, int] = {}
        self.thread_prompt_tokens: dict[str, int] = {}
        self.langchain_agent = self._maybe_build_langchain_agent()

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        return self._reply_offline(user_id, thread_id, message) if self.langchain_agent is None else self._reply_live(user_id, thread_id, message)

    def token_usage(self, thread_id: str) -> int:
        return self.thread_tokens.get(thread_id, 0)

    def prompt_token_usage(self, thread_id: str) -> int:
        return self.thread_prompt_tokens.get(thread_id, 0)

    def memory_file_size(self, user_id: str) -> int:
        return self.profile_store.file_size(user_id)

    def compaction_count(self, thread_id: str) -> int:
        return self.compact_memory.compaction_count(thread_id)

    def _reply_offline(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        for key, value in extract_profile_updates(message).items():
            self.profile_store.upsert_fact(user_id, key, value)
        self.compact_memory.append(thread_id, "user", message)
        prompt_tokens = self._estimate_prompt_context_tokens(user_id, thread_id)
        self.thread_prompt_tokens[thread_id] = self.thread_prompt_tokens.get(thread_id, 0) + prompt_tokens
        answer = self._offline_response(user_id, thread_id, message)
        self.compact_memory.append(thread_id, "assistant", answer)
        output_tokens = estimate_tokens(answer)
        self.thread_tokens[thread_id] = self.thread_tokens.get(thread_id, 0) + output_tokens
        return {
            "answer": answer, "agent_tokens": output_tokens, "prompt_tokens": prompt_tokens,
            "memory_file": str(self.profile_store.path_for(user_id)),
            "compactions": self.compaction_count(thread_id),
        }

    def _estimate_prompt_context_tokens(self, user_id: str, thread_id: str) -> int:
        context = self.compact_memory.context(thread_id)
        pieces = [self.profile_store.read_text(user_id), str(context["summary"])]
        pieces.extend(str(item["content"]) for item in context["messages"])
        return estimate_tokens("\n".join(pieces))

    def _offline_response(self, user_id: str, thread_id: str, message: str) -> str:
        del thread_id
        facts = self.profile_store.facts(user_id)
        lower = message.lower()
        requested: list[str] = []
        for key, signals in [
            ("name", ("tên", "là ai", "dũngct")),
            ("profession", ("nghề", "làm gì", "backend", "mlops", "product manager")),
            ("location", ("ở đâu", "nơi ở", "huế", "đà nẵng", "hà nội")),
            ("response_style", ("style", "kiểu trả lời", "trả lời mình thích")),
            ("favorite_drink", ("đồ uống", "uống gì")),
            ("favorite_food", ("món ăn", "món ruột")),
            ("pet", ("nuôi con gì", "corgi", "con bơ")),
            ("interests", ("mối quan tâm", "quan tâm kỹ thuật", "tóm tắt")),
        ]:
            if key in facts and any(signal in lower for signal in signals):
                requested.append(key)
        if requested:
            labels = {
                "name": "Tên", "profession": "Nghề nghiệp hiện tại",
                "location": "Nơi ở hiện tại", "response_style": "Style trả lời",
                "favorite_drink": "Đồ uống yêu thích", "favorite_food": "Món ăn yêu thích",
                "pet": "Thú cưng", "interests": "Mối quan tâm",
            }
            return "; ".join(f"{labels[key]}: {facts[key]}" for key in requested) + "."
        return "Mình đã cập nhật thông tin ổn định và giữ ngữ cảnh gần nhất trong compact memory."

    def _maybe_build_langchain_agent(self):
        if self.force_offline or not provider_has_runtime_credentials(self.config.model):
            return None
        try:
            return build_chat_model(self.config.model)
        except (RuntimeError, ValueError):
            return None

    def _reply_live(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        for key, value in extract_profile_updates(message).items():
            self.profile_store.upsert_fact(user_id, key, value)
        self.compact_memory.append(thread_id, "user", message)
        prompt_tokens = self._estimate_prompt_context_tokens(user_id, thread_id)
        context = self.compact_memory.context(thread_id)
        system = (
            "Use the persistent profile and compact context; prefer corrected facts.\n\n"
            f"{self.profile_store.read_text(user_id)}\n\nSummary: {context['summary']}"
        )
        response = self.langchain_agent.invoke([
            {"role": "system", "content": system}, *context["messages"]
        ])
        answer = response.content if hasattr(response, "content") else str(response)
        self.compact_memory.append(thread_id, "assistant", answer)
        output_tokens = estimate_tokens(answer)
        self.thread_tokens[thread_id] = self.thread_tokens.get(thread_id, 0) + output_tokens
        self.thread_prompt_tokens[thread_id] = self.thread_prompt_tokens.get(thread_id, 0) + prompt_tokens
        return {"answer": answer, "agent_tokens": output_tokens, "prompt_tokens": prompt_tokens}
