"""
Role:
- Summarize the full problem statement for user confirmation before solving.
- Make the final constraints, objectives, and assumptions explicit.

Called by:
- `Operational-Agent.agent`

Calls:
- `llm.responder`
- `schemas.problem`
"""


def build_confirmation_message(problem_spec: dict) -> str:
    """Create a human-readable confirmation message."""
    return f"Please confirm the problem specification: {problem_spec}"
