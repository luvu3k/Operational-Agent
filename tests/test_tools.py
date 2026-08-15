"""
作用：
- 校验工具注册中心与各求解工具的真实行为（不依赖真实 LLM）。
- 覆盖：工具自动发现、别名调用、OpenAI schema 导出、启发式求解真实执行。

运行方式：
- pytest: `python3 -m pytest tests/test_tools.py`
- 直接运行: `python3 -m tests.test_tools`
"""

from __future__ import annotations

from tools.tool_registry import get_tool_registry


SAMPLE_SPEC = {
    "skill_name": "emergency_island_supply",
    "description": "岛礁应急物资补给测试问题",
    "user_input": "请测试工具注册与调用",
    "objectives": ["最小化总运输成本"],
    "hard_constraints": ["满足全部岛礁需求"],
    "solver_preference": "heuristic",
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


def test_tools_discovered() -> None:
    registry = get_tool_registry(auto_discover=True)
    names = {spec.name for spec in registry.list_tools()}
    for expected in {"validate_problem", "exact_solver", "heuristic_solver", "repair_code"}:
        assert expected in names, f"缺少工具: {expected}"


def test_openai_schema_export() -> None:
    schemas = get_tool_registry().export_openai_tools()
    assert schemas, "OpenAI tools schema 不应为空"
    for schema in schemas:
        assert schema["type"] == "function"
        assert "name" in schema["function"]
        assert "parameters" in schema["function"]


def test_alias_dispatch_validate() -> None:
    registry = get_tool_registry()
    result = registry.execute("@validate", {"problem_spec": SAMPLE_SPEC})
    assert result.status == "success"
    assert result.payload.get("valid") is True


def test_heuristic_solver_real_execution() -> None:
    registry = get_tool_registry()
    result = registry.execute("heuristic_solver", {"problem_spec": SAMPLE_SPEC})
    assert result.status == "success"
    solution = result.payload["solution"]
    assert solution["feasible"] is True
    assert solution["objective_value"] is not None
    assert result.payload.get("code_path")


if __name__ == "__main__":
    test_tools_discovered()
    test_openai_schema_export()
    test_alias_dispatch_validate()
    test_heuristic_solver_real_execution()
    print("test_tools.py 全部通过")
