"""
Role:
- Retrieve relevant long-term historical experiences and debugging lessons.
- Backed by the SQLite long-term memory store so retrieval reflects真实历史经验。

Called by:
- `core.problem_builder`
- `core.recovery`

Calls:
- `memory.long_term`
"""

from __future__ import annotations

from typing import Any, Dict, List


def retrieve_experience_context(query: str, *, skill_name: str = "", limit: int = 5) -> List[Dict[str, Any]]:
    """从长期记忆中检索与查询相关的历史经验。"""
    try:
        from memory.long_term import retrieve_experiences
    except Exception:
        return []
    try:
        return retrieve_experiences(query, skill_name=skill_name, limit=limit)
    except Exception:
        return []


if __name__ == "__main__":
    print("=== experience_retriever.py 本地测试 ===")
    print(retrieve_experience_context("岛礁", skill_name="emergency_island_supply"))
