"""
作用：
- 存取会话级（短期）对话记忆，用于在一次会话内保留上下文。
- 基于 `memory.store` 的 SQLite 后端实现，跨进程可复现。

调用关系：
- 被 `app.session`、`core.agent` 调用，记录用户输入与智能体输出。
- 调用 `memory.store` 完成实际读写。
"""

from __future__ import annotations

from typing import Any, Dict, List

from memory.store import fetch_short_term, insert_short_term


def append_short_term_message(session_id: str, message: str, *, role: str = "user") -> None:
    """写入一条短期记忆消息。"""
    insert_short_term(session_id, role, message)


def get_short_term_history(session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """读取指定会话的历史消息。"""
    return fetch_short_term(session_id, limit=limit)


if __name__ == "__main__":
    print("=== memory/short_term.py 本地测试 ===")
    append_short_term_message("st-demo", "帮我求解岛礁补给问题", role="user")
    append_short_term_message("st-demo", "已生成求解代码并得到目标值", role="assistant")
    print(get_short_term_history("st-demo"))
