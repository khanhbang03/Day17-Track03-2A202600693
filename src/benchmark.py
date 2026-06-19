from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
from typing import Any

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config


@dataclass
class BenchmarkRow:
    agent_name: str
    agent_tokens_only: int
    prompt_tokens_processed: int
    recall_score: float
    response_quality: float
    memory_growth_bytes: int
    compactions: int


def load_conversations(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"Benchmark file must contain a JSON list: {path}")
    return data


def recall_points(answer: str, expected: list[str]) -> float:
    if not expected:
        return 1.0
    normalized = answer.casefold()
    hits = sum(item.casefold() in normalized for item in expected)
    if hits == 0:
        return 0.0
    return 1.0 if hits == len(expected) else 0.5


def heuristic_quality(answer: str, expected: list[str]) -> float:
    recall = recall_points(answer, expected)
    if not answer.strip():
        return 0.0
    clarity = 1.0 if len(answer) <= 600 else 0.5
    uncertainty = 0.5 if "chưa có thông tin" in answer.casefold() else 1.0
    return round((0.75 * recall + 0.25 * clarity) * uncertainty, 3)


def run_agent_benchmark(agent_name: str, agent, conversations: list[dict[str, Any]], config) -> BenchmarkRow:
    del config
    recall_scores: list[float] = []
    quality_scores: list[float] = []
    threads: set[str] = set()
    users: set[str] = set()
    initial_sizes: dict[str, int] = {}

    for conversation in conversations:
        user_id = conversation["user_id"]
        users.add(user_id)
        if hasattr(agent, "memory_file_size") and user_id not in initial_sizes:
            initial_sizes[user_id] = agent.memory_file_size(user_id)
        thread_id = f"{agent_name}-{conversation['id']}"
        threads.add(thread_id)
        for turn in conversation.get("turns", []):
            agent.reply(user_id, thread_id, turn)
        recall_thread = f"{thread_id}-recall"
        threads.add(recall_thread)
        for item in conversation.get("recall_questions", []):
            answer = agent.reply(user_id, recall_thread, item["question"])["answer"]
            expected = item.get("expected_contains", [])
            recall_scores.append(recall_points(answer, expected))
            quality_scores.append(heuristic_quality(answer, expected))

    growth = 0
    if hasattr(agent, "memory_file_size"):
        growth = sum(max(0, agent.memory_file_size(user) - initial_sizes.get(user, 0)) for user in users)
    return BenchmarkRow(
        agent_name=agent_name,
        agent_tokens_only=sum(agent.token_usage(thread) for thread in threads),
        prompt_tokens_processed=sum(agent.prompt_token_usage(thread) for thread in threads),
        recall_score=round(sum(recall_scores) / len(recall_scores), 3) if recall_scores else 0.0,
        response_quality=round(sum(quality_scores) / len(quality_scores), 3) if quality_scores else 0.0,
        memory_growth_bytes=growth,
        compactions=sum(agent.compaction_count(thread) for thread in threads),
    )


def format_rows(rows: list[BenchmarkRow]) -> str:
    headers = [
        "Agent", "Agent tokens only", "Prompt tokens processed",
        "Cross-session recall", "Response quality", "Memory growth (bytes)", "Compactions",
    ]
    values = [[
        row.agent_name, row.agent_tokens_only, row.prompt_tokens_processed,
        f"{row.recall_score:.3f}", f"{row.response_quality:.3f}",
        row.memory_growth_bytes, row.compactions,
    ] for row in rows]
    try:
        from tabulate import tabulate
        return tabulate(values, headers=headers, tablefmt="github")
    except ImportError:
        rows_text = [headers, *[[str(cell) for cell in row] for row in values]]
        widths = [max(len(row[index]) for row in rows_text) for index in range(len(headers))]
        lines = [
            "| " + " | ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)) + " |"
            for row in rows_text
        ]
        lines.insert(1, "| " + " | ".join("-" * width for width in widths) + " |")
        return "\n".join(lines)


def main() -> None:
    config = load_config(Path(__file__).resolve().parent.parent)
    suites = [
        ("Standard Benchmark", config.data_dir / "conversations.json"),
        ("Long-Context Stress Benchmark", config.data_dir / "advanced_long_context.json"),
    ]
    for suite_name, path in suites:
        suite_config = load_config(config.base_dir)
        suite_config.state_dir = config.state_dir / "benchmark" / suite_name.lower().replace(" ", "-")
        if suite_config.state_dir.exists():
            shutil.rmtree(suite_config.state_dir)
        suite_config.state_dir.mkdir(parents=True, exist_ok=True)
        conversations = load_conversations(path)
        rows = [
            run_agent_benchmark("Baseline", BaselineAgent(suite_config, True), conversations, suite_config),
            run_agent_benchmark("Advanced", AdvancedAgent(suite_config, True), conversations, suite_config),
        ]
        print(f"\n## {suite_name}\n")
        print(format_rows(rows))


if __name__ == "__main__":
    main()
