"""
作用：
- 将 `tools.tool_registry` 暴露出的工具能力转换为 core 层可直接消费的接口。
- 负责导出 OpenAI tools schema、执行具体工具并统一工具调用结果。

调用关系：
- 被 `core.react_agent` 调用，用于执行模型选择的工具。
- 被 `core.agent` 间接依赖，作为 ReAct 环中的工具桥接层。
- 调用 `tools.tool_registry` 完成自动扫描、schema 导出和本地执行。
"""

from __future__ import annotations

from typing import Dict, List

from tools.tool_registry import get_tool_registry


def get_openai_tool_schemas() -> List[dict]:
    """获取当前全部已注册工具的 OpenAI schema。"""
    return get_tool_registry(auto_discover=True).export_openai_tools()


def get_available_tools_text() -> str:
    """获取供提示词使用的已注册工具文本描述。"""
    return get_tool_registry(auto_discover=True).get_available_tools()


def dispatch_tool_call(tool_name: str, payload: Dict[str, object]) -> Dict[str, object]:
    """执行指定工具，并将结果转换为普通字典。"""
    result = get_tool_registry(auto_discover=True).execute(tool_name, payload)
    return {
        "status": result.status,
        "tool_name": result.tool_name,
        "payload": result.payload,
        "error": result.error,
    }


if __name__ == "__main__":
    print("=== tool_calling.py 本地测试 ===")
    print("已导出的 OpenAI tools schema：")
    for schema in get_openai_tool_schemas():
        print(f"- {schema['function']['name']}")

    sample_problem_spec = {
        "skill_name": "emergency_island_supply",
        "description": "工具调度测试问题",
        "user_input": "请测试工具桥接层",
        "objectives": ["最小化总运输时间"],
        "hard_constraints": ["满足全部需求"],
        "solver_preference": "heuristic",
    }

    print("\n执行 validate_problem：")
    print(dispatch_tool_call("validate_problem", {"problem_spec": sample_problem_spec}))
    print("\n执行 @heuristic：")
    print(dispatch_tool_call("@heuristic", {"problem_spec": sample_problem_spec}))
