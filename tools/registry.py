"""
Role:
- Register and expose all callable tools to the agent.

Called by:
- `llm.tool_calling`
- `Operational-Agent.react_loop`

Calls:
- All tool modules in this folder.
"""


TOOL_REGISTRY = {}


def register_tool(name: str, handler) -> None:
    """Register a tool handler."""
    TOOL_REGISTRY[name] = handler
