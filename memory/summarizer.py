"""
作用：
- 把一次求解会话压缩成可复用的经验摘要，并写入长期记忆。
- 优先使用 LLM 生成高质量摘要，无可用模型时回退到规则拼接摘要。

调用关系：
- 被 `core.recovery`、会话收尾流程或 `core.agent` 调用。
- 调用 `llm.client.LLM` 生成摘要，调用 `memory.long_term` 落库。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from memory.long_term import save_experience


def _rule_summary(session_messages: List[Dict[str, Any]], solve_result: Optional[Dict[str, Any]]) -> str:
    """无 LLM 时的规则摘要：拼接关键结论。"""
    parts: List[str] = []
    if solve_result:
        skill = solve_result.get("problem_spec", {}).get("skill_name", "unknown")
        tool = solve_result.get("selected_tool", "unknown")
        solution = solve_result.get("tool_result", {}).get("payload", {}).get("solution", {})
        objective = solution.get("objective_value")
        status = solution.get("status_text", solution.get("status", "unknown"))
        parts.append(
            f"问题族={skill}，选用工具={tool}，求解状态={status}，目标值={objective}。"
        )
    if session_messages:
        parts.append(f"共记录 {len(session_messages)} 条会话消息。")
    return " ".join(parts) or "SESSION_SUMMARY_EMPTY"


def _llm_summary(session_messages: List[Dict[str, Any]], solve_result: Optional[Dict[str, Any]]) -> str:
    """使用 LLM 生成经验摘要，失败时抛异常由上层兜底。"""
    from llm.client import LLM

    llm = LLM()
    context = {
        "messages": session_messages[-20:],
        "solve_result": {
            "selected_tool": (solve_result or {}).get("selected_tool"),
            "solution": (solve_result or {}).get("tool_result", {}).get("payload", {}).get("solution"),
        },
    }
    response = llm.simple_chat(
        user_text=(
            "请把以下求解会话压缩成一条不超过 3 句话的可复用经验，"
            "重点说明问题类型、采用的求解策略、效果，以及下次遇到类似问题的建议。\n"
            f"{json.dumps(context, ensure_ascii=False)}"
        ),
        system_prompt="你是负责提炼运筹优化历史经验的助手，只输出精炼中文经验，不要寒暄。",
        temperature=0,
    )
    summary = response.content.strip()
    if not summary:
        raise ValueError("LLM 返回空摘要。")
    return summary


def summarize_session(
    session_messages: List[Dict[str, Any]],
    *,
    solve_result: Optional[Dict[str, Any]] = None,
    persist: bool = False,
    skill_name: str = "",
    use_llm: bool = True,
) -> str:
    """把会话摘要成经验，可选择直接写入长期记忆。"""
    summary = ""
    if use_llm:
        try:
            summary = _llm_summary(session_messages, solve_result)
        except Exception:
            summary = ""
    if not summary:
        summary = _rule_summary(session_messages, solve_result)

    if persist:
        resolved_skill = skill_name or (solve_result or {}).get("problem_spec", {}).get("skill_name", "")
        save_experience(summary, skill_name=resolved_skill, metadata={"source": "session_summary"})
    return summary


if __name__ == "__main__":
    print("=== memory/summarizer.py 本地测试 ===")
    demo_messages = [
        {"role": "user", "content": "求解岛礁补给问题"},
        {"role": "assistant", "content": "已完成 Gurobi 精确求解"},
    ]
    demo_result = {
        "problem_spec": {"skill_name": "emergency_island_supply"},
        "selected_tool": "exact_solver",
        "tool_result": {"payload": {"solution": {"objective_value": 360.0, "status_text": "OPTIMAL"}}},
    }
    print(summarize_session(demo_messages, solve_result=demo_result, use_llm=False))
