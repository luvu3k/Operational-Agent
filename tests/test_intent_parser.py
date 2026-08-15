"""
作用：
- 校验意图识别的规则行为（不依赖真实 LLM）。

运行方式：
- pytest: `python3 -m pytest tests/test_intent_parser.py`
- 直接运行: `python3 -m tests.test_intent_parser`
"""

from __future__ import annotations

from core.intent_parser import parse_intent


def test_detect_exact_preference() -> None:
    result = parse_intent("请用精确算法求解岛礁应急物资补给问题")
    assert result["solver_preference"] == "exact"
    assert result["intent"] == "solve_problem"


def test_detect_heuristic_preference() -> None:
    result = parse_intent("请用启发式方法求解一个车辆路径问题")
    assert result["solver_preference"] == "heuristic"


def test_skill_matching() -> None:
    result = parse_intent("island emergency supply routing")
    assert result["matched_skill"] == "emergency_island_supply"
    assert result["skill_candidates"], "应返回候选 skill 列表"


if __name__ == "__main__":
    test_detect_exact_preference()
    test_detect_heuristic_preference()
    test_skill_matching()
    print("test_intent_parser.py 全部通过")
