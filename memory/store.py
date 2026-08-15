"""
作用：
- 为短期记忆与长期记忆提供统一的 SQLite 持久化接口，避免各记忆模块各自实现存储细节。
- 数据库文件默认落在 `storage/db/agent.db`，可跨进程复用会话历史与历史经验。

调用关系：
- 被 `memory.short_term` 调用，读写会话级对话记录。
- 被 `memory.long_term` 调用，读写可复用的历史经验。
- 依赖 `config.settings` 提供的存储目录配置。
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "storage" / "db" / "agent.db"


def _connect() -> sqlite3.Connection:
    """建立数据库连接并确保数据表存在。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(DB_PATH))
    connection.row_factory = sqlite3.Row
    _ensure_schema(connection)
    return connection


def _ensure_schema(connection: sqlite3.Connection) -> None:
    """初始化短期记忆和长期记忆两张表。"""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS short_term_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS long_term_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT NOT NULL UNIQUE,
            skill_name TEXT,
            summary TEXT NOT NULL,
            metadata TEXT,
            created_at TEXT NOT NULL
        );
        """
    )
    connection.commit()


def insert_short_term(session_id: str, role: str, content: str) -> None:
    """写入一条会话级消息。"""
    connection = _connect()
    try:
        connection.execute(
            "INSERT INTO short_term_memory (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, datetime.now().isoformat()),
        )
        connection.commit()
    finally:
        connection.close()


def fetch_short_term(session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """按时间顺序读取指定会话的历史消息。"""
    connection = _connect()
    try:
        rows = connection.execute(
            "SELECT role, content, created_at FROM short_term_memory "
            "WHERE session_id = ? ORDER BY id ASC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def insert_long_term(record_id: str, summary: str, *, skill_name: str = "", metadata: Optional[Dict[str, Any]] = None) -> None:
    """写入一条可复用的历史经验，record_id 重复时覆盖。"""
    connection = _connect()
    try:
        connection.execute(
            "INSERT INTO long_term_memory (record_id, skill_name, summary, metadata, created_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(record_id) DO UPDATE SET summary=excluded.summary, "
            "skill_name=excluded.skill_name, metadata=excluded.metadata",
            (record_id, skill_name, summary, json.dumps(metadata or {}, ensure_ascii=False), datetime.now().isoformat()),
        )
        connection.commit()
    finally:
        connection.close()


def search_long_term(keyword: str = "", *, skill_name: str = "", limit: int = 10) -> List[Dict[str, Any]]:
    """按关键字或 skill 名称检索历史经验。"""
    connection = _connect()
    try:
        query = "SELECT record_id, skill_name, summary, metadata, created_at FROM long_term_memory WHERE 1=1"
        params: List[Any] = []
        if keyword:
            query += " AND summary LIKE ?"
            params.append(f"%{keyword}%")
        if skill_name:
            query += " AND skill_name = ?"
            params.append(skill_name)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = connection.execute(query, params).fetchall()
        results: List[Dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            try:
                item["metadata"] = json.loads(item.get("metadata") or "{}")
            except json.JSONDecodeError:
                item["metadata"] = {}
            results.append(item)
        return results
    finally:
        connection.close()


def get_store() -> Dict[str, Any]:
    """返回存储句柄信息，兼容旧调用方。"""
    return {"backend": "sqlite", "db_path": str(DB_PATH)}


if __name__ == "__main__":
    print("=== memory/store.py 本地测试 ===")
    insert_short_term("demo-session", "user", "请求解岛礁补给问题")
    insert_short_term("demo-session", "assistant", "已完成求解，目标值 360")
    print("短期记忆：", fetch_short_term("demo-session"))
    insert_long_term("demo-exp-1", "岛礁补给：小规模优先用精确 Gurobi 求解", skill_name="emergency_island_supply")
    print("长期记忆：", search_long_term("岛礁"))
    print("存储句柄：", get_store())
