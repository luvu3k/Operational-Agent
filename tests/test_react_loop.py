"""
作用：
- 端到端校验 ReAct 主循环：从 problem_spec 到工具选择、执行、结果返回。
- 使用本地规则规划（不依赖真实 LLM），验证启发式闭环稳定可用。

运行方式：
- pytest: `python3 -m pytest tests/test_react_loop.py`
- 直接运行: `python3 -m tests.test_react_loop`
"""

from __future__ import annotations

from core.react_agent import run_react_loop

SPEC = {
    "skill_name": "emergency_island_supply",
    "description": "岛礁应急物资补给测试问题",
    "user_input": "请求解岛礁补给问题",
    "objectives": ["最小化总运输成本"],
    "hard_constraints": ["满足全部岛礁需求"],
    "solver_preference": "heuristic",
    "solver_backend": "auto",
    "resources": {
        "instance_data": {
            "depots": [{"name": "w1", "supply": 70}, {"name": "w2", "supply": 50}],
            "islands": [{"name": "a", "demand": 30}, {"name": "b", "demand": 40}, {"name": "c", "demand": 20}],
            "routes": [
                {"from": "w1", "to": "a", "cost": 4, "capacity": 40},
                {"from": "w1", "to": "b", "cost": 6, "capacity": 40},
                {"from": "w1", "to": "c", "cost": 9, "capacity": 30},
                {"from": "w2", "to": "a", "cost": 5, "capacity": 40},
                {"from": "w2", "to": "b", "cost": 4, "capacity": 40},
                {"from": "w2", "to": "c", "cost": 3, "capacity": 30},
            ],
        }
    },
}


def test_react_loop_completes() -> None:
    result = run_react_loop({"problem_spec": SPEC})
    assert result["status"] == "completed"
    assert result["selected_tool"] in {"heuristic_solver", "exact_solver"}
    assert result["final_answer"]


def test_react_loop_solution_feasible() -> None:
    result = run_react_loop({"problem_spec": SPEC})
    solution = result["tool_result"]["payload"]["solution"]
    assert solution["feasible"] is True
    assert solution["objective_value"] is not None


def test_validation_failure_short_circuits() -> None:
    bad_spec = {"skill_name": "", "description": "", "user_input": ""}
    result = run_react_loop({"problem_spec": bad_spec})
    assert result["status"] == "validation_failed"


if __name__ == "__main__":
    test_react_loop_completes()
    test_react_loop_solution_feasible()
    test_validation_failure_short_circuits()
    print("test_react_loop.py 全部通过")
