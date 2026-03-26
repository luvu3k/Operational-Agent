"""
Role:
- Store and retrieve session-scoped conversation memory.

Called by:
- `app.session`
- `Operational-Agent.agent`

Calls:
- `memory.store`
"""


def append_short_term_message(session_id: str, message: str) -> None:
    """Placeholder short-term memory write."""
    _ = (session_id, message)
