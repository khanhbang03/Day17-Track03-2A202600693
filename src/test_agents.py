from __future__ import annotations

from pathlib import Path

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config
from memory_store import UserProfileStore, extract_profile_updates


def make_config(tmp_path: Path):
    config = load_config(tmp_path)
    config.state_dir = tmp_path / "state"
    config.state_dir.mkdir(parents=True, exist_ok=True)
    config.compact_threshold_tokens = 80
    config.compact_keep_messages = 4
    return config


def test_user_markdown_read_write_edit(tmp_path: Path) -> None:
    store = UserProfileStore(tmp_path / "profiles")
    path = store.write_text("dung/../ct", "# User Profile\n\n## Facts\n- **name**: Dũng")
    assert path.exists()
    assert path.resolve().is_relative_to((tmp_path / "profiles").resolve())
    assert "Dũng" in store.read_text("dung/../ct")
    assert store.edit_text("dung/../ct", "Dũng", "DũngCT")
    assert "DũngCT" in store.read_text("dung/../ct")
    assert not store.edit_text("dung/../ct", "missing", "value")


def test_compact_trigger(tmp_path: Path) -> None:
    agent = AdvancedAgent(make_config(tmp_path), force_offline=True)
    for index in range(15):
        agent.reply("u1", "long", f"Lượt {index}: " + "ngữ cảnh dài " * 20)
    assert agent.compaction_count("long") > 0
    assert len(agent.compact_memory.context("long")["messages"]) <= 4


def test_cross_session_recall(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    advanced = AdvancedAgent(config, force_offline=True)
    baseline = BaselineAgent(config, force_offline=True)
    statement = "Mình tên là DũngCT và hiện tại mình làm MLOps engineer."
    advanced.reply("u1", "session-a", statement)
    baseline.reply("u1", "session-a", statement)
    advanced_answer = advanced.reply("u1", "session-b", "Mình tên gì và hiện tại làm nghề gì?")["answer"]
    baseline_answer = baseline.reply("u1", "session-b", "Mình tên gì và hiện tại làm nghề gì?")["answer"]
    assert "DũngCT" in advanced_answer and "MLOps engineer" in advanced_answer
    assert "DũngCT" not in baseline_answer and "MLOps engineer" not in baseline_answer


def test_compact_reduces_prompt_load_on_long_thread(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    baseline = BaselineAgent(config, force_offline=True)
    advanced = AdvancedAgent(config, force_offline=True)
    for index in range(30):
        message = f"Lượt {index}: " + "phân tích trade-off token và recall " * 16
        baseline.reply("u1", "thread", message)
        advanced.reply("u1", "thread", message)
    assert advanced.compaction_count("thread") > 0
    assert advanced.prompt_token_usage("thread") < baseline.prompt_token_usage("thread")


def test_correction_replaces_stale_fact(tmp_path: Path) -> None:
    agent = AdvancedAgent(make_config(tmp_path), force_offline=True)
    agent.reply("u1", "a", "Mình ở Đà Nẵng và đang làm backend engineer.")
    agent.reply("u1", "a", "Mình không còn làm backend engineer nữa, giờ chuyển sang MLOps engineer.")
    answer = agent.reply("u1", "b", "Hiện tại mình làm nghề gì?")["answer"]
    profile = agent.profile_store.read_text("u1")
    assert "MLOps engineer" in answer
    assert "**profession**: MLOps engineer" in profile
    assert "**profession**: backend engineer" not in profile


def test_questions_and_noise_are_not_persisted() -> None:
    assert extract_profile_updates("Mình tên gì và đang ở đâu?") == {}
    assert "profession" not in extract_profile_updates(
        "Mình đùa là chuyển sang product manager, nhưng đó chỉ là câu đùa."
    )
    assert "location" not in extract_profile_updates(
        "Hà Nội chỉ là nơi mình họp hai ngày, không phải nơi ở hiện tại."
    )
