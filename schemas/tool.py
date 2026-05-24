"""
作用：
- 定义工具注册、工具调用、工具执行结果所使用的统一数据结构。
- 为 `tools.tool_registry`、`core.tool_calling` 和 `llm.client1` 提供共享契约。

调用关系：
- 被 `tools.tool_registry` 调用，用于保存工具元数据并导出 OpenAI tools schema。
- 被 `core.tool_calling` 调用，用于组织工具调用结果。
- 可被其他 tool 模块复用，避免重复定义输入输出结构。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


JsonDict = Dict[str, Any]


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: JsonDict
    handler: Optional[Callable[..., Any]] = None
    aliases: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    timeout_sec: int = 300
    module: str = ""
    qualname: str = ""
    enabled: bool = True

    def to_openai_tool(self) -> JsonDict:
        """导出为 OpenAI Chat Completions 可直接使用的 tool schema。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }


@dataclass
class ToolCallRequest:
    tool_name: str
    arguments: JsonDict = field(default_factory=dict)


@dataclass
class ToolExecutionResult:
    status: str
    tool_name: str
    payload: JsonDict = field(default_factory=dict)
    error: Optional[str] = None
