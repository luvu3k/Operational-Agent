"""
作用：
- 校验短期记忆与长期记忆的 SQLite 持久化读写。

运行方式：
- pytest: `python3 -m pytest tests/test_memory.py`
- 直接运行: `python3 -m tests.test_memory`
"""

from __future__ import annotations

from uuid import uuid4

from memory.long_term import retrieve_experiences, save_experience
from memory.short_term import append_short_term_message, get_short_term_history


def test_short_term_roundtrip() -> None:
    session_id = f"test_{uuid4().hex[:8]}"
    append_short_term_message(session_id, "求解岛礁补给问题", role="user")
    append_short_term_message(session_id, "已完成求解", role="assistant")
    history = get_short_term_history(session_id)
    assert len(history) == 2
    assert history[0]["role"] == "user"


def test_long_term_roundtrip() -> None:
    keyword = f"关键词{uuid4().hex[:6]}"
    save_experience(f"这是一条包含 {keyword} 的历史经验。", skill_name="emergency_island_supply")
    results = retrieve_experiences(keyword)
    assert any(keyword in record["summary"] for record in results)


if __name__ == "__main__":
    test_short_term_roundtrip()
    test_long_term_roundtrip()
    print("test_memory.py 全部通过")
