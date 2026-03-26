"""
Role:
- Define shared input and output structures for tool calls.

Called by:
- `llm.tool_calling`
- `tools.registry`
- All tool modules
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class ToolResult:
    status: str
    payload: Dict[str, Any] = field(default_factory=dict)
