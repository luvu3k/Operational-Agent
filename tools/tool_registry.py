"""
作用：
- 维护智能体运行时可见的工具注册中心，支持 `@tool` 装饰器、自动扫描与执行分发。
- 向 LLM 导出 OpenAI 兼容的 tool schema，并为本地 ReAct 循环提供统一执行入口。

调用关系：
- 被 `core.tool_calling` 调用，用于导出 tools schema 与执行具体工具。
- 被 `tools` 目录下各工具模块调用，通过 `@tool(...)` 注册元数据。
- 自动扫描 `tools/` 下的模块，发现并装载带装饰器的工具函数。
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from schemas.tool import ToolExecutionResult, ToolSpec


TOOLS_PACKAGE = "tools"
TOOLS_DIR = Path(__file__).resolve().parent


def tool(
    *,
    name: str,
    description: str,
    input_schema: dict,
    aliases: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    timeout_sec: int = 300,
):
    """为工具函数附加元数据，供自动扫描阶段读取。"""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        func.__tool_spec__ = ToolSpec(
            name=name,
            description=description,
            input_schema=input_schema,
            aliases=aliases or [],
            tags=tags or [],
            timeout_sec=timeout_sec,
            module=func.__module__,
            qualname=func.__qualname__,
            handler=func,
        )
        return func

    return decorator


class ToolRegistry:
    """维护工具元数据、别名映射、自动扫描和执行分发。"""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}
        self._aliases: Dict[str, str] = {}
        self._discovered = False

    def register(self, spec: ToolSpec) -> ToolSpec:
        """注册一项工具定义。"""
        if not spec.handler:
            raise ValueError(f"工具 `{spec.name}` 缺少可执行 handler。")
        self._tools[spec.name] = spec
        for alias in spec.aliases:
            self._aliases[alias] = spec.name
        return spec

    def register_function(self, func: Callable[..., Any]) -> ToolSpec:
        """从装饰器附加信息中读取工具规格并注册。"""
        spec = getattr(func, "__tool_spec__", None)
        if spec is None:
            raise ValueError(f"函数 `{func.__name__}` 未使用 @tool 装饰器。")
        if not spec.module:
            spec.module = func.__module__
        if not spec.qualname:
            spec.qualname = func.__qualname__
        spec.handler = func
        return self.register(spec)

    def discover(self, package_name: str = TOOLS_PACKAGE, directory: Path = TOOLS_DIR) -> None:
        """自动扫描 tools 包，将所有被 @tool 标注的函数注册到运行时。"""
        if self._discovered:
            return

        for module_info in pkgutil.iter_modules([str(directory)]):
            module_name = module_info.name
            if module_name.startswith("_") or module_name == "tool_registry":
                continue

            module = importlib.import_module(f"{package_name}.{module_name}")
            for _, func in inspect.getmembers(module, inspect.isfunction):
                if getattr(func, "__tool_spec__", None) is not None:
                    self.register_function(func)

        self._discovered = True

    def get(self, name_or_alias: str) -> ToolSpec:
        """按正式名称或别名获取工具规格。"""
        resolved_name = self._aliases.get(name_or_alias, name_or_alias)
        spec = self._tools.get(resolved_name)
        if spec is None:
            raise ValueError(f"未找到工具: {name_or_alias}")
        return spec

    def list_tools(self) -> List[ToolSpec]:
        """列出全部已注册工具。"""
        return [self._tools[name] for name in sorted(self._tools)]

    def get_available_tools(self) -> str:
        """生成面向提示词的工具说明列表。"""
        if not self._tools:
            return "当前没有已注册工具。"
        lines = []
        for spec in self.list_tools():
            alias_text = f"（别名: {', '.join(spec.aliases)}）" if spec.aliases else ""
            lines.append(f"- {spec.name}{alias_text}: {spec.description}")
        return "\n".join(lines)

    def export_openai_tools(self) -> List[dict]:
        """导出 OpenAI Chat Completions 可使用的 tools schema。"""
        return [spec.to_openai_tool() for spec in self.list_tools() if spec.enabled]

    def execute(self, name_or_alias: str, arguments: Optional[dict] = None) -> ToolExecutionResult:
        """执行指定工具，并统一封装返回结构。"""
        spec = self.get(name_or_alias)
        handler = spec.handler
        if handler is None:
            raise ValueError(f"工具 `{spec.name}` 缺少 handler。")

        arguments = arguments or {}
        try:
            if arguments:
                result = handler(**arguments)
            else:
                result = handler()
            payload = result if isinstance(result, dict) else {"result": result}
            return ToolExecutionResult(
                status="success",
                tool_name=spec.name,
                payload=payload,
                error=None,
            )
        except Exception as exc:  # pragma: no cover - 运行期保护分支
            return ToolExecutionResult(
                status="error",
                tool_name=spec.name,
                payload={},
                error=str(exc),
            )


_GLOBAL_TOOL_REGISTRY = ToolRegistry()


def get_tool_registry(auto_discover: bool = True) -> ToolRegistry:
    """返回全局单例工具注册表。"""
    if auto_discover:
        _GLOBAL_TOOL_REGISTRY.discover()
    return _GLOBAL_TOOL_REGISTRY


if __name__ == "__main__":
    print("=== tool_registry.py 本地测试 ===")
    registry = get_tool_registry(auto_discover=True)

    print("已发现工具：")
    for spec in registry.list_tools():
        print(f"- {spec.name} | aliases={spec.aliases} | tags={spec.tags}")

    print("\nOpenAI tools schema：")
    for schema in registry.export_openai_tools():
        print(f"- {schema['function']['name']}")

    sample_problem_spec = {
        "skill_name": "emergency_island_supply",
        "description": "岛礁应急物资补给测试问题",
        "user_input": "请测试工具注册与调用",
        "objectives": ["最小化总运输时间"],
        "hard_constraints": ["满足全部岛礁需求"],
        "solver_preference": "exact",
    }

    print("\n执行校验工具：")
    validate_result = registry.execute("validate_problem", {"problem_spec": sample_problem_spec})
    print(validate_result)

    print("\n通过别名执行精确求解工具：")
    exact_result = registry.execute("@exact", {"problem_spec": sample_problem_spec})
    print(exact_result)
