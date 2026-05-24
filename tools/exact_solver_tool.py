"""
作用：
- 面向智能体暴露精确求解工具，负责接收结构化问题并返回最小可用求解结果。
- 当前版本先搭建完整调用闭环，便于后续接入 MILP、CP-SAT 或其他精确算法实现。

调用关系：
- 被 `tools.tool_registry` 通过 `@tool` 自动扫描注册。
- 被 `core.tool_calling` 和 `core.react_agent` 调用。
- 后续可继续调用 `solver.codegen.exact_generator`、`solver.sandbox.runner`、`solver.postprocess.parser`。
"""

from __future__ import annotations

from tools.tool_registry import tool


@tool(
    name="exact_solver",
    description="根据结构化问题生成并执行精确求解流程。",
    input_schema={
        "type": "object",
        "properties": {
            "problem_spec": {"type": "object", "description": "结构化后的优化问题定义。"}
        },
        "required": ["problem_spec"],
    },
    aliases=["@exact", "@es"],
    tags=["solver", "exact"],
)
def run_exact_solver(problem_spec: dict) -> dict:
    """返回精确求解的最小可运行结果。"""
    return {
        "mode": "exact",
        "status": "success",
        "selected_solver": "exact_solver",
        "message": "已完成精确求解占位执行，可在此替换为真实 MILP/CP 求解逻辑。",
        "problem_spec": problem_spec,
        "solution": {
            "objective_value": None,
            "feasible": True,
            "strategy": "exact",
        },
    }


if __name__ == "__main__":
    print("=== exact_solver_tool.py 本地测试 ===")
    sample_problem_spec = {
        "skill_name": "emergency_island_supply",
        "description": "岛礁应急物资补给测试问题",
        "user_input": "请执行精确求解工具测试",
        "objectives": ["最小化总配送时间"],
        "hard_constraints": ["必须满足所有岛礁需求"],
        "solver_preference": "exact",
    }
    print(run_exact_solver(sample_problem_spec))
