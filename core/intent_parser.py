"""
作用：
- 根据用户输入识别当前任务意图，并从 `skills/` 中选出最匹配的问题类型。
- 额外抽取求解策略偏好，例如偏向精确算法还是启发式算法。

调用关系：
- 被 `core.agent` 调用，作为进入 ReAct 之前的第一步语义解析。
- 调用 `skills.loader` 读取本地 skills 元数据并执行轻量匹配。
"""

from __future__ import annotations

from typing import Any, Dict, List

from skills.loader import load_all_skills


def _detect_intent(user_input: str) -> str:
    text = user_input.lower()
    if any(keyword in text for keyword in ["修复", "报错", "debug", "错误"]):
        return "repair_problem"
    if any(keyword in text for keyword in ["修改", "新增约束", "增加约束", "调整约束"]):
        return "modify_constraints"
    return "solve_problem"


def _detect_solver_preference(user_input: str) -> str:
    text = user_input.lower()
    if any(keyword in text for keyword in ["精确", "exact", "milp", "cp", "整数规划"]):
        return "exact"
    if any(keyword in text for keyword in ["启发式", "heuristic", "遗传算法", "禁忌搜索", "模拟退火"]):
        return "heuristic"
    return "auto"


def _score_skill(user_input: str, skill: Dict[str, Any]) -> int:
    text = user_input.lower()
    metadata = skill.get("metadata", {})
    score = 0
    for keyword in metadata.get("keywords", []):
        if keyword.lower() in text:
            score += 3
    skill_name = metadata.get("skill_name", skill.get("skill_name", ""))
    if skill_name and skill_name.lower() in text:
        score += 5
    description = metadata.get("description", "")
    for token in description.lower().split():
        if token and token in text:
            score += 1
    return score


def parse_intent(user_input: str) -> Dict[str, Any]:
    """识别问题意图、求解偏好和最匹配的 skill。"""
    skills = load_all_skills()
    ranked_skills: List[Dict[str, Any]] = []
    for skill in skills:
        ranked_skills.append(
            {
                "skill_name": skill["skill_name"],
                "score": _score_skill(user_input, skill),
                "metadata": skill.get("metadata", {}),
            }
        )

    ranked_skills.sort(key=lambda item: item["score"], reverse=True)
    matched_skill = ranked_skills[0]["skill_name"] if ranked_skills else "emergency_island_supply"
    return {
        "intent": _detect_intent(user_input),
        "matched_skill": matched_skill,
        "solver_preference": _detect_solver_preference(user_input),
        "skill_candidates": ranked_skills,
    }


if __name__ == "__main__":
    print("=== intent_parser.py 本地测试 ===")
    samples = [
        "请帮我求解一个岛礁应急物资补给问题，优先使用精确算法。",
        "请用启发式方法求解一个车辆路径问题。",
        "我新增了时窗约束，请帮我修改模型。",
        "代码报错了，请帮我修复。",
    ]
    for sample in samples:
        print(f"\n输入：{sample}")
        print(parse_intent(sample))
