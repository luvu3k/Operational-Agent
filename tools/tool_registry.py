"""
Role:
- 维护全局工具注册表，提供注册函数.

Called by:
- `llm.tool_calling`
- `Operational-Agent.react_loop`

Calls:
- All tool modules in this folder.
"""
from typing import Dict, Any

TOOL_REGISTRY = {}

class ToolExecutor:
    """
    工具执行器，负责管理和执行工具。
    """
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}

    def registerTool(self, name: str, description: str, func: callable) -> None:
        """注册工具处理函数."""
        if name in self.tools:
            raise ValueError(f"警告:工具 '{name}' 已存在，将被覆盖。")
        self.tools[name] = {"description": description, "func": func}
        print(f"工具 '{name}' 已注册: {description}")

    def getTool(self, name: str) -> callable:
        """
        根据工具名称获取工具的执行函数.
        """
        tool = self.tools.get(name, False).get("func", False)
        if not tool:
            raise ValueError(f"错误:工具 '{name}' 未找到。")
        return tool

    def listTools(self) -> list:
        """列出所有已注册的工具."""
        return list(self.tools.keys())

    def getAvailableTools(self) -> str:
        """
        获取所有可用工具的格式化描述字符串。
        """
        return "\n".join([
            f"- {name}: {info['description']}" 
            for name, info in self.tools.items()
        ])

def search(query: str) -> str:
    """示例工具函数:模拟搜索."""
    return f"搜索结果: 模拟的搜索结果对于查询 '{query}'"

if __name__ == "__main__":
    # 创建工具执行器
    executor = ToolExecutor()

    search_description = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    # 注册工具
    executor.registerTool("Search", search_description, search)

    # 列出所有工具
    print(executor.listTools())

    # 获取工具描述
    print(executor.getAvailableTools())

    # 执行工具
    tool = executor.getTool("Search")
    result = tool("Python编程")
    print(result)

