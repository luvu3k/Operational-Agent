"""
作用：
- 面向智能体暴露启发式求解工具，负责接收结构化问题并返回最小可用求解结果。
- 当前版本先提供可运行闭环所需的占位实现，后续可替换为真实代码生成与执行逻辑。

调用关系：
- 被 `tools.tool_registry` 通过 `@tool` 自动扫描注册。
- 被 `core.tool_calling` 和 `core.react_agent` 调用。
- 后续可继续调用 `solver.codegen.heuristic_generator`、`solver.sandbox.runner`、`solver.postprocess.parser`。
"""

from __future__ import annotations

from tools.tool_registry import tool


@tool(
    name="heuristic_solver",
    description="根据结构化问题生成并执行启发式求解流程。",
    input_schema={
        "type": "object",
        "properties": {
            "problem_spec": {"type": "object", "description": "结构化后的优化问题定义。"}
        },
        "required": ["problem_spec"],
    },
    aliases=["@heuristic", "@hs"],
    tags=["solver", "heuristic"],
)
def run_heuristic_solver(problem_spec: dict) -> dict:
    """返回启发式求解的最小可运行结果。"""
    return {
        "mode": "heuristic",
        "status": "success",
        "selected_solver": "heuristic_solver",
        "message": "已完成启发式求解占位执行，可在此替换为真实算法生成与运行逻辑。",
        "problem_spec": problem_spec,
        "solution": {
            "objective_value": None,
            "feasible": True,
            "strategy": "heuristic",
        },
    }


if __name__ == "__main__":
    print("=== heuristic_solver_tool.py 本地测试 ===")
    sample_problem_spec = {
        "skill_name": "vehicle_routing",
        "description": "车辆路径问题测试",
        "user_input": "请执行启发式求解工具测试",
        "objectives": ["最小化总行驶距离"],
        "hard_constraints": ["每个客户点必须被服务一次"],
        "solver_preference": "heuristic",
    }
    print(run_heuristic_solver(sample_problem_spec))
