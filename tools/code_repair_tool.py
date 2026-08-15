"""
作用：
- 在生成代码执行失败或约束不满足时，提供统一的修复入口。
- 优先使用 LLM 根据错误报告与原始代码给出修复后的完整代码；无可用模型时回退到规则化的修复建议。

调用关系：
- 被 `tools.tool_registry` 通过 `@tool` 自动扫描注册。
- 被 `core.react_agent`、`core.recovery` 调用。
- 调用 `llm.client.LLM` 完成代码修复（可选），并读取 `error_report` 中的 stderr / 原始代码。
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from tools.tool_registry import tool

_REPAIR_SYSTEM_PROMPT = """你是资深运筹优化工程师，负责修复自动生成的求解代码。
输入包含：原始代码、报错信息（stderr/traceback）、问题结构。
要求：
1. 只输出修复后的完整 Python 代码，使用 ```python 代码块包裹。
2. 保持原有的 result.json 写出逻辑与字段结构不变。
3. 不要解释，不要寒暄。"""


def _extract_code_block(text: str) -> Optional[str]:
    """从 LLM 返回中提取 ```python``` 代码块。"""
    match = re.search(r"```(?:python)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _llm_repair(error_report: Dict[str, Any]) -> Dict[str, Any]:
    """使用 LLM 生成修复后的完整代码，失败时抛异常由上层兜底。"""
    from llm.client import LLM

    original_code = str(error_report.get("original_code", ""))
    stderr = str(error_report.get("stderr", error_report.get("execution_result", {}).get("error", "")))
    problem_spec = error_report.get("problem_spec", {})

    llm = LLM()
    response = llm.simple_chat(
        user_text=(
            "请修复以下求解代码。\n"
            f"【报错信息】\n{stderr}\n\n"
            f"【问题结构】\n{problem_spec}\n\n"
            f"【原始代码】\n{original_code}"
        ),
        system_prompt=_REPAIR_SYSTEM_PROMPT,
        temperature=0,
    )
    repaired_code = _extract_code_block(response.content)
    if not repaired_code:
        raise ValueError("LLM 未返回可用的修复代码。")
    return {
        "repair_status": "repaired",
        "message": "已由 LLM 生成修复后的代码，可重新执行验证。",
        "repaired_code": repaired_code,
        "error_report": error_report,
    }


@tool(
    name="repair_code",
    description="根据错误报告与原始代码，生成修复后的求解代码或修复建议。",
    input_schema={
        "type": "object",
        "properties": {
            "error_report": {
                "type": "object",
                "description": "执行期错误信息，建议包含 stderr、original_code、problem_spec。",
            }
        },
        "required": ["error_report"],
    },
    aliases=["@repair"],
    tags=["repair", "debug"],
)
def repair_code(error_report: dict) -> dict:
    """优先用 LLM 修复代码，失败时给出规则化修复建议。"""
    try:
        return _llm_repair(error_report)
    except Exception as exc:
        stderr = str(error_report.get("stderr", error_report.get("execution_result", {}).get("error", "")))
        suggestion = "请检查实例数据是否完整、约束是否互相矛盾、以及求解器依赖是否安装。"
        if "infeasible" in stderr.lower():
            suggestion = "模型不可行：请检查供给是否足以覆盖需求，或航线容量是否过紧。"
        elif "not_available" in stderr.lower() or "no module" in stderr.lower():
            suggestion = "求解器依赖缺失：请安装对应求解器（如 gurobipy）或切换到启发式求解。"
        return {
            "repair_status": "advice_only",
            "message": f"未启用 LLM 修复（{exc}），已给出规则化修复建议。",
            "suggestion": suggestion,
            "error_report": error_report,
        }


if __name__ == "__main__":
    print("=== code_repair_tool.py 本地测试 ===")
    sample_error_report = {
        "tool_name": "exact_solver",
        "exception_type": "RuntimeError",
        "stderr": "model infeasible",
        "problem_spec": {"skill_name": "emergency_island_supply"},
        "original_code": "print('placeholder')",
    }
    print(repair_code(sample_error_report))
