"""
作用：
- 在调用求解工具之前检查 `problem_spec` 的最小完整性，避免缺字段直接进入求解阶段。
- 该工具可被 ReAct 循环优先调用，作为求解前的守卫步骤。

调用关系：
- 被 `tools.tool_registry` 通过 `@tool` 自动扫描注册。
- 被 `core.react_agent` 或 `core.recovery` 调用。
- 校验对象来自 `schemas.problem` 的统一字段约定。
"""

from __future__ import annotations

from tools.tool_registry import tool


@tool(
    name="validate_problem",
    description="校验结构化问题是否具备进入求解阶段所需的关键字段。",
    input_schema={
        "type": "object",
        "properties": {
            "problem_spec": {"type": "object", "description": "待校验的问题定义。"}
        },
        "required": ["problem_spec"],
    },
    aliases=["@validate"],
    tags=["validator", "guardrail"],
)
def validate_problem_spec(problem_spec: dict) -> dict:
    """返回最小校验结果。"""
    missing_fields = []
    for field_name in ["skill_name", "description", "user_input"]:
        if not problem_spec.get(field_name):
            missing_fields.append(field_name)

    objectives = problem_spec.get("objectives", [])
    constraints = problem_spec.get("hard_constraints", [])
    valid = not missing_fields and bool(objectives) and bool(constraints)

    return {
        "valid": valid,
        "problem_spec": problem_spec,
        "missing_fields": missing_fields,
        "message": "校验通过。" if valid else "问题结构不完整，暂不建议进入求解阶段。",
    }


if __name__ == "__main__":
    print("=== validator_tool.py 本地测试 ===")
    valid_problem_spec = {
        "skill_name": "emergency_island_supply",
        "description": "测试问题",
        "user_input": "请测试校验工具",
        "objectives": ["最小化时间"],
        "hard_constraints": ["满足需求"],
    }
    invalid_problem_spec = {"skill_name": "", "description": "", "user_input": ""}

    print("有效问题：")
    print(validate_problem_spec(valid_problem_spec))
    print("无效问题：")
    print(validate_problem_spec(invalid_problem_spec))
