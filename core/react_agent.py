"""
作用：
- 实现项目当前版本的最小 ReAct 闭环：校验问题 -> 规划工具 -> 执行工具 -> 观察结果 -> 输出总结。
- 同时支持两种模式：优先使用 LLM 的 tool calling；若环境未配置可用模型，则自动回退到本地规则规划。

调用关系：
- 被 `core.agent` 调用，作为确认后的执行主循环。
- 调用 `core.tool_calling` 完成工具 schema 导出与本地工具执行。
- 调用 `llm.client` 发起规划与总结请求。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from core.tool_calling import dispatch_tool_call, get_available_tools_text, get_openai_tool_schemas
from llm.client import LLM


def _build_planner_system_prompt() -> str:
    return "\n".join(
        [
            "你是一个组合优化智能体，采用 ReAct 思维模式。",
            "你需要根据问题描述和当前可用工具，选择最合适的一个工具执行。",
            "优先通过工具调用而不是直接空谈。",
            "如果用户明显偏向精确算法，调用 exact_solver；如果偏向启发式，调用 heuristic_solver。",
            "若问题结构缺失或不完整，应优先调用 validate_problem 或 repair_code。",
            "当前可用工具如下：",
            get_available_tools_text(),
        ]
    )


def _maybe_build_llm() -> Optional[LLM]:
    try:
        return LLM.from_env()
    except Exception:
        return None


def _choose_tool_without_llm(problem_spec: Dict[str, Any]) -> Dict[str, Any]:
    solver_preference = str(problem_spec.get("solver_preference", "auto")).lower()
    if solver_preference == "exact":
        return {"tool_name": "exact_solver", "arguments": {"problem_spec": problem_spec}}
    return {"tool_name": "heuristic_solver", "arguments": {"problem_spec": problem_spec}}


def _parse_tool_calls(tool_calls: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not tool_calls:
        return None
    tool_call = tool_calls[0]
    function_payload = tool_call.get("function", {})
    raw_arguments = function_payload.get("arguments") or "{}"
    try:
        arguments = json.loads(raw_arguments)
    except json.JSONDecodeError:
        arguments = {}
    return {
        "tool_name": function_payload.get("name"),
        "arguments": arguments,
    }


def run_react_loop(problem_state: Dict[str, Any]) -> Dict[str, Any]:
    """运行一轮最小可用 ReAct 闭环。"""
    trace: List[Dict[str, Any]] = []
    problem_spec = dict(problem_state.get("problem_spec", {}))

    validation_result = dispatch_tool_call("validate_problem", {"problem_spec": problem_spec})
    trace.append({"phase": "validate", "result": validation_result})
    validation_payload = validation_result.get("payload", {})
    if not validation_payload.get("valid", False):
        return {
            "status": "validation_failed",
            "trace": trace,
            "problem_spec": problem_spec,
            "final_answer": validation_payload.get("message", "问题校验失败。"),
        }

    llm = _maybe_build_llm()
    selected_call = None
    llm_plan = None

    if llm is not None:
        plan_response = llm.chat(
            [
                {"role": "system", "content": _build_planner_system_prompt()},
                {
                    "role": "user",
                    "content": (
                        "请基于以下问题选择最合适的一个工具，并尽量使用 tool calling。\n"
                        f"{json.dumps(problem_spec, ensure_ascii=False)}"
                    ),
                },
            ],
            tools=get_openai_tool_schemas(),
            tool_choice="auto",
            temperature=0,
        )
        llm_plan = {
            "provider": llm.provider,
            "model": llm.model,
            "content": plan_response.content,
            "tool_calls": plan_response.tool_calls,
        }
        trace.append({"phase": "plan", "result": llm_plan})
        selected_call = _parse_tool_calls(plan_response.tool_calls)

    if selected_call is None:
        selected_call = _choose_tool_without_llm(problem_spec)
        trace.append({"phase": "fallback_plan", "result": selected_call})

    tool_name = selected_call["tool_name"]
    arguments = selected_call.get("arguments", {})
    if not arguments and tool_name in {"heuristic_solver", "exact_solver"}:
        arguments = {"problem_spec": problem_spec}

    action_result = dispatch_tool_call(tool_name, arguments)
    trace.append({"phase": "act", "result": action_result})

    if action_result.get("status") != "success":
        repair_result = dispatch_tool_call(
            "repair_code",
            {
                "error_report": {
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "execution_result": action_result,
                }
            },
        )
        trace.append({"phase": "repair", "result": repair_result})

    final_answer = ""
    if llm is not None:
        summary_response = llm.simple_chat(
            user_text=(
                "请根据以下 ReAct 执行记录，给出中文总结，说明最终调用了什么工具、得到什么结果。\n"
                f"{json.dumps(trace, ensure_ascii=False)}"
            ),
            system_prompt="你是一个负责总结求解过程的优化智能体。",
            temperature=0,
        )
        final_answer = summary_response.content
        trace.append({"phase": "summary", "result": {"content": final_answer}})
    else:
        action_payload = action_result.get("payload", {})
        final_answer = (
            f"已完成最小 ReAct 闭环，调用工具 `{tool_name}`，"
            f"结果状态为 `{action_result.get('status')}`，"
            f"工具返回信息：{action_payload.get('message', '无补充说明。')}"
        )

    return {
        "status": "completed",
        "problem_spec": problem_spec,
        "selected_tool": tool_name,
        "trace": trace,
        "final_answer": final_answer,
        "llm_enabled": llm is not None,
    }
