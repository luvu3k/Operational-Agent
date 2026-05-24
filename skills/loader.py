"""
作用：
- 加载 `skills/` 目录下的 `metadata.json`、`skill.md`、`examples.md`。
- 为意图识别、问题构建和后续提示词拼接提供基础技能知识。

调用关系：
- 被 `core.intent_parser` 调用，用于技能匹配。
- 被 `core.problem_builder` 调用，用于读取匹配 skill 的基础背景、目标和约束说明。
- 可被未来的 `rag.retrievers.skill_retriever` 复用。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


SKILLS_DIR = Path(__file__).resolve().parent


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_skill(skill_name: str) -> Dict[str, Any]:
    """按技能名称加载一套完整的技能材料。"""
    skill_dir = SKILLS_DIR / skill_name
    if not skill_dir.exists() or not skill_dir.is_dir():
        raise FileNotFoundError(f"未找到 skill 目录: {skill_name}")

    metadata = _read_json(skill_dir / "metadata.json")
    return {
        "skill_name": skill_name,
        "metadata": metadata,
        "skill_markdown": _read_text(skill_dir / "skill.md"),
        "examples_markdown": _read_text(skill_dir / "examples.md"),
        "readme_markdown": _read_text(skill_dir / "README.md"),
        "path": str(skill_dir),
    }


def load_all_skills() -> List[Dict[str, Any]]:
    """扫描并加载当前项目内的全部技能目录。"""
    skills: List[Dict[str, Any]] = []
    for child in sorted(SKILLS_DIR.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if child.name == "__pycache__":
            continue
        if not (child / "metadata.json").exists():
            continue
        skills.append(load_skill(child.name))
    return skills
