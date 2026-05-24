"""
作用：
- 作为当前项目的顶层智能体入口，串联意图识别、问题构建、用户确认与 ReAct 执行。
- 让 CLI、API 或测试都可以通过同一个入口驱动最小可运行智能体流程。

调用关系：
- 被 `app.cli`、`app.api` 以及未来测试脚本调用。
- 调用 `core.intent_parser`、`core.problem_builder`、`core.confirmation`、`core.react_agent`。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.confirmation import build_confirmation_message
from core.intent_parser import parse_intent
from core.problem_builder import build_problem_spec
from core.react_agent import run_react_loop


def run_agent(
    user_input: str,
    *,
    confirmed: bool = False,
    problem_spec: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """执行一轮顶层智能体流程。"""
    current_problem_spec = problem_spec
    if current_problem_spec is None:
        intent_result = parse_intent(user_input)
        current_problem_spec = build_problem_spec(user_input, intent_result)
    else:
        intent_result = {"intent": "solve_problem", "matched_skill": current_problem_spec.get("skill_name", "")}

    confirmation_message = build_confirmation_message(current_problem_spec)
    if not confirmed:
        return {
            "status": "awaiting_confirmation",
            "user_input": user_input,
            "intent_result": intent_result,
            "problem_spec": current_problem_spec,
            "confirmation_message": confirmation_message,
        }

    current_problem_spec["confirmed"] = True
    react_result = run_react_loop(
        {
            "user_input": user_input,
            "intent_result": intent_result,
            "problem_spec": current_problem_spec,
        }
    )
    react_result["confirmation_message"] = confirmation_message
    return react_result


if __name__ == "__main__":
    print("=== agent.py 本地测试 ===")
    sample_input = "请帮我求解一个岛礁应急物资补给问题，优先使用精确算法。"

    first_round = run_agent(sample_input)
    print("第一阶段：")
    print(first_round)

    second_round = run_agent(
        sample_input,
        confirmed=True,
        problem_spec=first_round["problem_spec"],
    )
    print("\n第二阶段：")
    print(second_round)
