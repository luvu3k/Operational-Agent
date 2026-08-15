"""
作用：
- 存取长期记忆，即被摘要后的可复用历史经验（例如某类约束组合下优先用哪种求解策略）。
- 基于 `memory.store` 的 SQLite 后端实现，供 RAG 经验检索与 ReAct 决策参考。

调用关系：
- 被 `memory.summarizer` 调用，写入会话提炼后的经验。
- 被 `rag.retrievers.experience_retriever` 调用，检索历史经验。
- 调用 `memory.store` 完成实际读写。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import uuid4

from memory.store import insert_long_term, search_long_term


def save_experience(summary: str, *, skill_name: str = "", metadata: Optional[Dict[str, Any]] = None, record_id: Optional[str] = None) -> str:
    """保存一条历史经验，返回记录 ID。"""
    resolved_id = record_id or f"exp_{uuid4().hex[:12]}"
    insert_long_term(resolved_id, summary, skill_name=skill_name, metadata=metadata)
    return resolved_id


def retrieve_experiences(keyword: str = "", *, skill_name: str = "", limit: int = 10) -> List[Dict[str, Any]]:
    """按关键字或 skill 检索历史经验。"""
    return search_long_term(keyword, skill_name=skill_name, limit=limit)


if __name__ == "__main__":
    print("=== memory/long_term.py 本地测试 ===")
    exp_id = save_experience(
        "岛礁补给小规模问题优先使用精确 Gurobi，可在数秒内取得最优解。",
        skill_name="emergency_island_supply",
        metadata={"scale": "small", "solver": "gurobi"},
    )
    print("写入经验：", exp_id)
    print("检索经验：", retrieve_experiences("岛礁"))
