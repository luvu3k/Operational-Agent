"""
作用：
- 将用户输入、匹配到的 skill 基础知识以及当前求解偏好合并成统一的 `ProblemSpec`。
- 在进入 ReAct 循环前形成稳定的问题对象，供确认、校验和工具调用复用。

调用关系：
- 被 `core.agent` 调用，构造最小可执行问题状态。
- 调用 `skills.loader` 读取 skill 内容。
- 调用 `schemas.problem` 输出标准问题结构。
"""

from __future__ import annotations

from typing import Dict, List

from schemas.problem import ProblemSpec
from skills.loader import load_skill


def _extract_markdown_bullets(markdown_text: str) -> List[str]:
    bullets: List[str] = []
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
    return bullets


def build_problem_spec(user_input: str, intent_result: Dict[str, object]) -> Dict[str, object]:
    """构建结构化问题对象，并附带 skill 基础信息。"""
    matched_skill = str(intent_result.get("matched_skill", "emergency_island_supply"))
    skill = load_skill(matched_skill)

    skill_markdown = skill.get("skill_markdown", "")
    metadata = skill.get("metadata", {})
    bullets = _extract_markdown_bullets(skill_markdown)

    problem = ProblemSpec(
        skill_name=matched_skill,
        problem_type=str(metadata.get("description", matched_skill)),
        description=f"基于 skill `{matched_skill}` 构建的优化问题。",
        user_input=user_input,
        background=skill_markdown,
        objectives=bullets[:2] or ["以用户输入与基础 skill 为准构建目标函数。"],
        hard_constraints=bullets[2:] or ["需满足 skill 中基础约束以及用户新增约束。"],
        soft_constraints=[],
        assumptions=["默认以本地可用资源和 skill 基础设定构建模型。"],
        resources={},
        experience_hints=[],
        extra_requirements=[user_input],
        solver_preference=str(intent_result.get("solver_preference", "auto")),
        confirmed=False,
    )
    return problem.to_dict()


if __name__ == "__main__":
    print("=== problem_builder.py 本地测试 ===")
    sample_input = "请帮我求解一个岛礁应急物资补给问题，优先使用精确算法。"
    sample_intent = {
        "intent": "solve_problem",
        "matched_skill": "emergency_island_supply",
        "solver_preference": "exact",
    }
    print(build_problem_spec(sample_input, sample_intent))
