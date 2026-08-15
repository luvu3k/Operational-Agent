"""
作用：
- 校验问题构建阶段能从自然语言 + JSON 数据块生成正确的 `ProblemSpec`（使用规则抽取，避免依赖真实 LLM）。

运行方式：
- pytest: `python3 -m pytest tests/test_problem_builder.py`
- 直接运行: `python3 -m tests.test_problem_builder`
"""

from __future__ import annotations

from core.problem_builder import build_problem_spec

USER_INPUT = """请用精确算法和 gurobi 求解岛礁应急补给问题。
背景：2个仓库为3个岛礁补给。
目标：最小化总运输成本。
约束：每个仓库发出量不超过库存；每个岛礁收到量满足需求；每条航线不超过容量。
```json
{
  "depots": [{"name": "w1", "supply": 70}, {"name": "w2", "supply": 50}],
  "islands": [{"name": "a", "demand": 30}, {"name": "b", "demand": 40}, {"name": "c", "demand": 20}],
  "routes": [
    {"from": "w1", "to": "a", "cost": 4, "capacity": 40},
    {"from": "w2", "to": "c", "cost": 3, "capacity": 30}
  ]
}
```
"""

INTENT = {"intent": "solve_problem", "matched_skill": "emergency_island_supply", "solver_preference": "exact"}


def test_build_spec_fields() -> None:
    spec = build_problem_spec(USER_INPUT, INTENT, use_llm=False)
    assert spec["skill_name"] == "emergency_island_supply"
    assert spec["solver_backend"] == "gurobi"
    assert spec["solver_preference"] == "exact"


def test_instance_data_extracted() -> None:
    spec = build_problem_spec(USER_INPUT, INTENT, use_llm=False)
    instance = spec["resources"]["instance_data"]
    assert len(instance["depots"]) == 2
    assert len(instance["islands"]) == 3


def test_resource_fallback_when_no_json() -> None:
    # 无 JSON 数据块时应从 RAG 资源索引回退取到实例数据
    spec = build_problem_spec("请用精确算法求解岛礁应急补给问题", INTENT, use_llm=False)
    instance = spec.get("resources", {}).get("instance_data", {})
    assert instance.get("depots"), "应从资源索引回退取到 depots"


if __name__ == "__main__":
    test_build_spec_fields()
    test_instance_data_extracted()
    test_resource_fallback_when_no_json()
    print("test_problem_builder.py 全部通过")
