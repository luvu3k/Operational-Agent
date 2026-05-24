"""
作用：
- 在代码执行失败或约束不满足时，提供统一的修复入口。
- 当前版本先输出修复建议占位结果，后续可接入真实的 LLM 修复与重试链路。

调用关系：
- 被 `tools.tool_registry` 通过 `@tool` 自动扫描注册。
- 被 `core.react_agent`、`core.recovery` 调用。
- 后续可继续接入 `solver.sandbox.capture` 与 `llm.client1`。
"""

from __future__ import annotations

from tools.tool_registry import tool


@tool(
    name="repair_code",
    description="根据错误报告生成下一步修复建议。",
    input_schema={
        "type": "object",
        "properties": {
            "error_report": {"type": "object", "description": "执行期错误信息或约束失败信息。"}
        },
        "required": ["error_report"],
    },
    aliases=["@repair"],
    tags=["repair", "debug"],
)
def repair_code(error_report: dict) -> dict:
    """返回修复建议占位结果。"""
    return {
        "repair_status": "pending",
        "message": "已记录错误信息，后续可在此接入 LLM 驱动的代码修复逻辑。",
        "error_report": error_report,
    }


if __name__ == "__main__":
    print("=== code_repair_tool.py 本地测试 ===")
    sample_error_report = {
        "tool_name": "exact_solver",
        "exception_type": "RuntimeError",
        "message": "求解器返回 infeasible",
        "stderr": "model infeasible",
    }
    print(repair_code(sample_error_report))
