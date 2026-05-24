"""
作用：
- 定义智能体内部统一使用的组合优化问题结构。
- 让 `skills`、`rag`、`core`、`tools` 在传递问题信息时使用同一份字段约定。

调用关系：
- 被 `core.problem_builder` 调用，用于构造结构化问题对象。
- 被 `core.confirmation` 调用，用于生成用户确认信息。
- 被 `tools.validator_tool`、`tools.heuristic_solver_tool`、`tools.exact_solver_tool` 调用。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class ProblemSpec:
    skill_name: str
    # 问题类型，是偏向精确求解还是启发式求解
    problem_type: str
    description: str
    user_input: str
    background: str = ""
    objectives: List[str] = field(default_factory=list)
    hard_constraints: List[str] = field(default_factory=list)
    soft_constraints: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    resources: Dict[str, Any] = field(default_factory=dict)
    experience_hints: List[str] = field(default_factory=list)
    extra_requirements: List[str] = field(default_factory=list)
    solver_preference: str = "auto"
    confirmed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """将 dataclass 转换为便于序列化和 tool 调用的字典。"""
        return asdict(self)
