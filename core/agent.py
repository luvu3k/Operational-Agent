"""
作用：
- 作为当前项目的顶层智能体入口，串联意图识别、问题构建、用户确认与 ReAct 执行。
- 让 CLI、API 或测试都可以通过同一个入口驱动最小可运行智能体流程。
- 可选地将本轮对话写入短期记忆，并在求解完成后把经验沉淀进长期记忆。

调用关系：
- 被 `app.cli`、`app.api` 以及未来测试脚本调用。
- 调用 `core.intent_parser`、`core.problem_builder`、`core.confirmation`、`core.react_agent`。
- 可选调用 `memory.short_term`、`memory.summarizer` 完成记忆读写。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.confirmation import build_confirmation_message
from core.intent_parser import parse_intent
from core.problem_builder import build_problem_spec
from core.react_agent import run_react_loop


def _record_memory(session_id: Optional[str], role: str, content: str) -> None:
    """尽力写入短期记忆，失败不影响主流程。"""
    if not session_id:
        return
    try:
        from memory.short_term import append_short_term_message

        append_short_term_message(session_id, content, role=role)
    except Exception:
        pass


def _persist_experience(react_result: Dict[str, Any]) -> None:
    """求解完成后尽力沉淀经验到长期记忆，失败不影响主流程。"""
    try:
        from memory.summarizer import summarize_session

        summarize_session(
            [],
            solve_result=react_result,
            persist=True,
            skill_name=react_result.get("problem_spec", {}).get("skill_name", ""),
            use_llm=False,
        )
    except Exception:
        pass


def run_agent(
    user_input: str,
    *,
    confirmed: bool = False,
    problem_spec: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """执行一轮顶层智能体流程。"""
    current_problem_spec = problem_spec
    if current_problem_spec is None:
        # 当用户输入新问题时，需要解析意图并构建问题规格
        intent_result = parse_intent(user_input)
        # 解析意图后，根据意图构建问题规格
        current_problem_spec = build_problem_spec(user_input, intent_result)
    else:
        intent_result = {"intent": "solve_problem", "matched_skill": current_problem_spec.get("skill_name", "")}

    confirmation_message = build_confirmation_message(current_problem_spec)
    if not confirmed:
        _record_memory(session_id, "user", user_input)
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
    _record_memory(session_id, "assistant", react_result.get("final_answer", ""))
    _persist_experience(react_result)
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
