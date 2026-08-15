"""
Role:
- Retrieve structured resource information such as vehicles, warehouses, and inventory.
- Backed by JSON resource files under `rag/indexes/resources/` so problem_builder可自动拼接资源。

Called by:
- `core.problem_builder`

Calls:
- 本地 `rag/indexes/resources/*.json` 资源索引文件。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

RESOURCE_INDEX_DIR = Path(__file__).resolve().parents[1] / "indexes" / "resources"


def _load_resource_files() -> List[Dict[str, Any]]:
    """加载资源索引目录下的全部 JSON 文件。"""
    if not RESOURCE_INDEX_DIR.exists():
        return []
    records: List[Dict[str, Any]] = []
    for path in sorted(RESOURCE_INDEX_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        records.append({"source": path.name, "data": payload})
    return records


def retrieve_resource_context(query: str, *, skill_name: str = "") -> Dict[str, Any]:
    """
    检索与查询相关的资源信息。
    当前实现按 skill_name / 关键字做轻量匹配，返回最匹配的一份资源数据。
    """
    records = _load_resource_files()
    if not records:
        return {"query": query, "skill_name": skill_name, "resources": {}}

    lowered_query = query.lower()
    best_match: Dict[str, Any] = {}
    for record in records:
        data = record.get("data", {})
        record_skill = str(data.get("skill_name", "")).lower()
        if skill_name and record_skill == skill_name.lower():
            best_match = data
            break
        keywords = [str(item).lower() for item in data.get("keywords", [])]
        if any(keyword in lowered_query for keyword in keywords):
            best_match = data

    resources = best_match.get("instance_data", best_match.get("resources", {})) if best_match else {}
    return {"query": query, "skill_name": skill_name, "resources": resources}


if __name__ == "__main__":
    print("=== resource_retriever.py 本地测试 ===")
    print(retrieve_resource_context("岛礁补给", skill_name="emergency_island_supply"))
