"""
Role:
- Agent-facing tool for direct sandbox execution requests.

Called by:
- `Operational-Agent.react_loop`

Calls:
- `solver.sandbox.executor`
"""


def run_in_sandbox(code_path: str) -> dict:
    """Placeholder sandbox execution tool."""
    return {"code_path": code_path, "execution_status": "pending"}
