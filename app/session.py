"""
Role:
- Manage session identifiers and session-scoped runtime context.
- Provide a stable place to bind short-term memory to a user session.

Called by:
- `app.cli`
- `app.api`
- `Operational-Agent.agent`

Calls:
- `memory.short_term`
"""

from dataclasses import dataclass
from uuid import uuid4


@dataclass
class SessionContext:
    session_id: str


def create_session() -> SessionContext:
    """Create a new lightweight session context."""
    return SessionContext(session_id=str(uuid4()))
