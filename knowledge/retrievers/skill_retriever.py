"""
Role:
- Retrieve skill candidates and relevant fragments for a user request.

Called by:
- `Operational-Agent.intent_parser`

Calls:
- `skills.loader`
"""


def retrieve_skill_context(user_input: str) -> list:
    """Placeholder skill retrieval."""
    return [user_input]
