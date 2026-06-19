from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import unicodedata


def estimate_tokens(text: str) -> int:
    """Stable offline approximation suitable for relative benchmark costs."""

    cleaned = " ".join(text.split())
    return max(1, (len(cleaned) + 3) // 4) if cleaned else 0


@dataclass
class UserProfileStore:
    """Persistent, structured storage for one User.md per user."""

    root_dir: Path

    def path_for(self, user_id: str) -> Path:
        normalized = unicodedata.normalize("NFKC", user_id).strip()
        slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", normalized).strip(".-") or "anonymous"
        return self.root_dir / slug[:100] / "User.md"

    def read_text(self, user_id: str) -> str:
        path = self.path_for(user_id)
        return path.read_text(encoding="utf-8") if path.exists() else "# User Profile\n\n## Facts\n"

    def write_text(self, user_id: str, content: str) -> Path:
        path = self.path_for(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.rstrip() + "\n", encoding="utf-8")
        return path

    def edit_text(self, user_id: str, search_text: str, replacement: str) -> bool:
        content = self.read_text(user_id)
        if search_text not in content:
            return False
        self.write_text(user_id, content.replace(search_text, replacement, 1))
        return True

    def file_size(self, user_id: str) -> int:
        path = self.path_for(user_id)
        return path.stat().st_size if path.exists() else 0

    def facts(self, user_id: str) -> dict[str, str]:
        facts: dict[str, str] = {}
        for line in self.read_text(user_id).splitlines():
            match = re.match(r"^-\s+\*\*([a-z_]+)\*\*:\s*(.+?)\s*$", line)
            if match:
                facts[match.group(1)] = match.group(2)
        return facts

    def upsert_fact(self, user_id: str, key: str, value: str) -> Path:
        """Replace a field in place, so corrected facts do not coexist."""

        facts = self.facts(user_id)
        new_value = value.strip().rstrip(" .")
        if key in {"interests", "response_style"} and key in facts:
            old_items = [item.strip() for item in facts[key].split(",")]
            new_items = [item.strip() for item in new_value.split(",")]
            new_value = ", ".join(dict.fromkeys([*old_items, *new_items]))
        facts[key] = new_value
        lines = ["# User Profile", "", "## Facts"]
        lines.extend(f"- **{name}**: {facts[name]}" for name in sorted(facts))
        return self.write_text(user_id, "\n".join(lines))


def extract_profile_updates(message: str) -> dict[str, str]:
    """Extract only explicit, durable profile assertions.

    The conservative patterns act as a confidence threshold: questions,
    examples, travel mentions and jokes are not persisted as current facts.
    """

    text = " ".join(message.strip().split())
    lower = text.lower()
    if not text:
        return {}
    question_markers = (
        "tên gì", "tên mình là gì", "tên mình không", "ở đâu", "nghề gì",
        "làm nghề gì", "làm gì?", "nuôi con gì", "món ăn yêu thích của mình là gì",
        "đồ uống yêu thích của mình là gì", "thử nhớ", "thử ghi nhớ",
    )
    if any(marker in lower for marker in question_markers):
        return {}
    updates: dict[str, str] = {}

    def capture(key: str, patterns: list[str]) -> None:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                value = match.group(1).strip(" ,.;:!?")
                if value:
                    updates[key] = value
                return

    capture("name", [
        r"(?:mình|tôi)\s+tên\s+(?:là\s+)?([A-Za-zÀ-ỹ0-9_. -]{2,40}?)(?=,|\.| và | hiện |$)",
        r"tên\s+mình\s+là\s+([A-Za-zÀ-ỹ0-9_. -]{2,40}?)(?=,|\.| và |$)",
        r"nhắc lại lần cuối[^:]*:\s*tên\s+([A-Za-zÀ-ỹ0-9_. -]{2,40}?)(?=,|\.|$)",
    ])
    if "không phải nơi ở hiện tại" not in lower:
        capture("location", [
            r"(?:hiện tại|hiện|giờ|thực ra từ tuần này)\s+(?:mình\s+)?(?:đang\s+)?(?:làm việc\s+)?ở\s+([A-Za-zÀ-ỹ ]{2,35}?)(?=,|\.| chứ | để | vài |$)",
            r"(?:mình|tôi)\s+(?:vẫn\s+)?(?:đang\s+)?ở\s+([A-Za-zÀ-ỹ ]{2,35}?)(?=,|\.| chứ | để | chưa |$)",
            r"nơi ở (?:hiện tại )?(?:là|đã cập nhật từ [^ ]+ sang)\s+([A-Za-zÀ-ỹ ]{2,35}?)(?=,|\.|$)",
        ])
    capture("profession", [
        r"(?:giờ|hiện tại)\s+(?:mình\s+)?(?:đang\s+)?(?:chuyển sang|làm)\s+([A-Za-z][A-Za-z0-9 +#.-]* engineer)(?=,|\.| cho |$)",
        r"(?:mình|tôi)\s+(?:vẫn\s+)?(?:đang\s+)?làm\s+([A-Za-z][A-Za-z0-9 +#.-]* engineer)(?=,|\.| cho |$)",
        r"nghề nghiệp (?:thì )?(?:vẫn là|hiện tại là)\s+([A-Za-z][A-Za-z0-9 +#.-]* engineer)(?=,|\.|$)",
        r"nghề\s+([A-Za-z][A-Za-z0-9 +#.-]* engineer)(?=,|\.|$)",
    ])
    capture("favorite_drink", [
        r"(?:đồ uống yêu thích (?:của mình )?là|mình vẫn uống)\s+(.{2,45}?)(?=,|\.| nhưng | như |$)",
        r"(?:mình|tôi)\s+thích\s+([^,.!?]*(?:cà phê|trà)[^,.!?]*)",
    ])
    capture("favorite_food", [
        r"(?:món ăn yêu thích (?:của mình )?là|món ruột(?: của mình)?(?: là)?)\s+([^,.!?]{2,45})",
    ])
    capture("pet", [
        r"(?:mình|tôi)\s+nuôi\s+(?:một\s+)?([^,.!?]{2,60}?)(?=\.|,|$)",
        r"con\s+(corgi(?:\s+(?:tên\s+)?[A-Za-zÀ-ỹ]+)?)",
    ])

    style: list[str] = []
    if any(term in lower for term in ("ngắn gọn", "câu trả lời ngắn", "bullet ngắn", "3 bullet")):
        style.append("3 bullet ngắn" if "3 bullet" in lower else "ngắn gọn")
    if "bullet" in lower and not any("bullet" in item for item in style):
        style.append("có bullet")
    if any(term in lower for term in ("ví dụ thực tế", "ví dụ thực chiến")):
        style.append("có ví dụ thực chiến")
    if "trade-off" in lower:
        style.append("nhấn mạnh trade-off")
    if style and any(term in lower for term in ("mình muốn", "mình thích", "style", "hãy trả lời")):
        updates["response_style"] = ", ".join(dict.fromkeys(style))

    interests: list[str] = []
    for canonical, pattern in [
        ("Python", r"\bpython\b"), ("AI", r"\bai\b|ai ứng dụng|ai agent"),
        ("MLOps", r"\bmlops\b"), ("RAG", r"\brag\b"),
    ]:
        if re.search(pattern, lower) and any(
            signal in lower for signal in ("mình thích", "quan tâm", "đang học", "dài hạn")
        ):
            interests.append(canonical)
    if interests:
        updates["interests"] = ", ".join(interests)

    for key, value in list(updates.items()):
        value_lower = value.lower()
        if key == "profession" and (
            f"không còn làm {value_lower}" in lower
            or f"{value_lower} cho đỡ" in lower
            or ("chỉ là câu đùa" in lower and value_lower in lower.split("chỉ là câu đùa")[0][-80:])
        ):
            del updates[key]
        elif key == "location" and f"{value_lower} chỉ là nơi" in lower:
            del updates[key]
    return updates


def summarize_messages(messages: list[dict[str, str]], max_items: int = 6) -> str:
    if not messages:
        return ""
    snippets: list[str] = []
    for message in messages[-max_items:]:
        role = "U" if message.get("role") == "user" else "A"
        content = " ".join(message.get("content", "").split())
        if len(content) > 180:
            content = content[:177].rstrip() + "..."
        snippets.append(f"{role}: {content}")
    return " | ".join(snippets)


@dataclass
class CompactMemoryManager:
    threshold_tokens: int
    keep_messages: int
    state: dict[str, dict[str, object]] = field(default_factory=dict)

    def append(self, thread_id: str, role: str, content: str) -> None:
        thread = self.state.setdefault(
            thread_id, {"messages": [], "summary": "", "compactions": 0}
        )
        messages = thread["messages"]
        assert isinstance(messages, list)
        messages.append({"role": role, "content": content})
        context_text = str(thread["summary"]) + " " + " ".join(
            str(item.get("content", "")) for item in messages
        )
        if estimate_tokens(context_text) <= self.threshold_tokens or len(messages) <= self.keep_messages:
            return

        old_messages = messages[:-self.keep_messages]
        combined = " | ".join(
            part for part in (str(thread["summary"]), summarize_messages(old_messages, 10)) if part
        )
        max_summary_chars = max(240, self.threshold_tokens * 2)
        if len(combined) > max_summary_chars:
            combined = combined[-max_summary_chars:]
            separator = combined.find(" | ")
            if separator >= 0:
                combined = combined[separator + 3:]
        thread["summary"] = combined
        thread["messages"] = messages[-self.keep_messages:]
        thread["compactions"] = int(thread["compactions"]) + 1

    def context(self, thread_id: str) -> dict[str, object]:
        thread = self.state.setdefault(
            thread_id, {"messages": [], "summary": "", "compactions": 0}
        )
        return {
            "messages": [dict(item) for item in thread["messages"]],
            "summary": str(thread["summary"]),
            "compactions": int(thread["compactions"]),
        }

    def compaction_count(self, thread_id: str) -> int:
        return int(self.context(thread_id)["compactions"])
