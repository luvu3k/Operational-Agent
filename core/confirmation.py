"""
作用：
- 将结构化后的问题说明整理成面向用户的中文确认文本。
- 在真正调用求解工具之前，把目标函数、约束、假设和求解偏好显式列给用户确认。

调用关系：
- 被 `core.agent` 调用，在进入 `core.react_agent` 前进行确认。
- 读取 `schemas.problem` 输出的问题字段，但不直接依赖具体求解工具。
"""

from __future__ import annotations

from typing import Dict, List


def _format_list(title: str, values: List[str]) -> str:
    if not values:
        return f"{title}：暂无"
    body = "\n".join(f"- {item}" for item in values)
    return f"{title}：\n{body}"


def build_confirmation_message(problem_spec: Dict[str, object]) -> str:
    """生成用户确认所需的问题说明。"""
    return "\n".join(
        [
            "请确认以下问题定义是否正确：",
            f"问题类型：{problem_spec.get('skill_name', 'unknown')}",
            f"问题说明：{problem_spec.get('description', '')}",
            f"求解偏好：{problem_spec.get('solver_preference', 'auto')}",
            _format_list("目标函数", list(problem_spec.get("objectives", []))),
            _format_list("硬约束", list(problem_spec.get("hard_constraints", []))),
            _format_list("软约束", list(problem_spec.get("soft_constraints", []))),
            _format_list("建模假设", list(problem_spec.get("assumptions", []))),
            _format_list("用户附加需求", list(problem_spec.get("extra_requirements", []))),
        ]
    )


if __name__ == "__main__":
    print("=== confirmation.py 本地测试 ===")
    sample_problem_spec = {
        "skill_name": "emergency_island_supply",
        "description": "岛礁应急物资补给测试问题",
        "solver_preference": "exact",
        "objectives": ["最小化总配送时间"],
        "hard_constraints": ["满足所有岛礁需求"],
        "soft_constraints": ["尽量均衡船只负载"],
        "assumptions": ["当前资源数据完整可用"],
        "extra_requirements": ["优先保障重伤员医疗物资"],
    }
    print(build_confirmation_message(sample_problem_spec))
